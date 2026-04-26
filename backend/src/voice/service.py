"""VoiceService — unified Gradbot WebSocket handler."""

import logging
import time

from fastapi import WebSocket

from src.voice.tasks import VoiceTask, VoiceTaskResult

logger = logging.getLogger(__name__)


class VoiceService:
    """Handles Gradbot voice sessions for any task type.

    The same class handles onboarding, feedback, and any future voice task.
    Only the VoiceTask config changes (prompt, schema, context).

    Future: add handle_twilio_session() for phone calls — same logic,
    different audio format (ulaw 8kHz instead of OggOpus).
    """

    async def handle_session(
        self,
        websocket: WebSocket,
        task: VoiceTask,
    ) -> VoiceTaskResult:
        """Run a complete Gradbot voice session and return extracted data."""
        import gradbot

        cfg = gradbot.config.from_env()
        start_time = time.time()
        result_data: dict = {}

        tools = [
            gradbot.ToolDef(
                "save_result",
                (
                    "Save the extracted information from the user. "
                    "Call this tool ONLY when you have gathered enough data "
                    "(at minimum the required fields)."
                ),
                task.output_schema,  # already a JSON string from tasks.py
            ),
        ]

        def _session_kwargs(extra: dict) -> dict:
            """Merge YAML session_kwargs with explicit overrides — explicit wins."""
            merged = {**cfg.session_kwargs, **extra}
            # CRITICAL: silence_timeout_s must always be 0.0 — never let YAML override.
            merged["silence_timeout_s"] = 0.0
            return merged

        def on_start(msg: dict) -> gradbot.SessionConfig:
            session_kwargs = _session_kwargs({
                "rewrite_rules": task.language,  # language code string for TTS
                "assistant_speaks_first": True,
            })
            logger.info(
                "Voice on_start: task=%s user=%s start_msg=%s session_kwargs=%s",
                task.task_type, task.user_id, msg, session_kwargs,
            )
            cfg_obj = gradbot.SessionConfig(
                voice_id=task.voice_id,
                instructions=task.system_prompt,
                language=gradbot.LANGUAGES.get(task.language, gradbot.Lang.En),
                tools=tools,
                **session_kwargs,
            )
            logger.info(
                "Voice SessionConfig built: voice_id=%s lang=%s speaks_first=%s "
                "silence=%s tools=%d",
                cfg_obj.voice_id, cfg_obj.language, cfg_obj.assistant_speaks_first,
                cfg_obj.silence_timeout_s, len(cfg_obj.tools or []),
            )
            return cfg_obj

        async def on_tool_call(handle, input_handle, ws):
            if handle.name == "save_result":
                # handle.args is ALREADY a dict — do NOT json.loads() it
                result_data.update(handle.args)
                logger.info(
                    "Voice data extracted: task=%s user=%s",
                    task.task_type,
                    task.user_id,
                )
                # Tell the LLM the save worked so it can naturally wrap up
                # (the prompt instructs it to say a short closing line).
                await handle.send_json({"status": "saved"})

                # Notify the FRONTEND directly via the WebSocket. The browser
                # uses this to show a "Information saved ✓" transition while
                # the agent's closing line plays out, then auto-navigates to
                # the permissions screen.
                try:
                    await ws.send_json({
                        "type": "event",
                        "event": f"{task.task_type}_saved",
                    })
                except Exception:
                    logger.warning("Failed to send saved event to client")
            else:
                await handle.send_error(f"Unknown tool: {handle.name}")

        try:
            await gradbot.websocket.handle_session(
                websocket,
                config=cfg,  # auto-sets run_kwargs, output_format, debug
                on_start=on_start,
                on_tool_call=on_tool_call,
            )
        except Exception as e:
            logger.exception("Gradbot session error: %s", e)

        duration = time.time() - start_time
        logger.info(
            "Voice session ended: task=%s user=%s duration=%.1fs success=%s",
            task.task_type,
            task.user_id,
            duration,
            bool(result_data),
        )

        return VoiceTaskResult(
            task_type=task.task_type,
            user_id=task.user_id,
            extracted_data=result_data,
            success=bool(result_data),
        )


# Singleton
voice_service = VoiceService()
