"""VoiceService — unified Gradbot WebSocket handler."""

import json
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
                "Save the extracted information. Call when you have gathered enough data from the conversation.",
                task.output_schema,  # already a JSON string from tasks.py
            ),
        ]

        def on_start(msg: dict) -> gradbot.SessionConfig:
            return gradbot.SessionConfig(
                voice_id=task.voice_id,
                instructions=task.system_prompt,
                language=gradbot.LANGUAGES.get(task.language, gradbot.Lang.Fr),
                tools=tools,
                assistant_speaks_first=True,
                silence_timeout_s=0.0,  # CRITICAL: avoid agent re-prompting itself
                rewrite_rules=task.language,  # language code string for TTS
                **cfg.session_kwargs,  # merge YAML settings (they take priority)
            )

        async def on_tool_call(handle, input_handle, ws):
            if handle.name == "save_result":
                # handle.args is ALREADY a dict — do NOT json.loads() it
                result_data.update(handle.args)
                await handle.send_json({"status": "saved"})
                logger.info(
                    f"Voice data extracted: task={task.task_type} user={task.user_id}"
                )

                # Switch to a goodbye prompt — no more tools needed
                goodbye_config = gradbot.SessionConfig(
                    voice_id=task.voice_id,
                    instructions="L'utilisateur a terminé. Remercie-le chaleureusement et dis au revoir.",
                    language=gradbot.LANGUAGES.get(task.language, gradbot.Lang.Fr),
                    tools=[],
                    assistant_speaks_first=False,
                    silence_timeout_s=0.0,
                    **cfg.session_kwargs,
                )
                await input_handle.send_config(goodbye_config)
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
            logger.error(f"Gradbot session error: {e}")

        duration = time.time() - start_time
        logger.info(
            f"Voice session ended: task={task.task_type} user={task.user_id} "
            f"duration={duration:.1f}s success={bool(result_data)}"
        )

        return VoiceTaskResult(
            task_type=task.task_type,
            user_id=task.user_id,
            extracted_data=result_data,
            success=bool(result_data),
        )


# Singleton
voice_service = VoiceService()
