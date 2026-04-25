# Skill: Scaffold a new ADK Agent

## When to use
When I need to create a new agent or add tools to an existing agent.

## Agent template (Google ADK Python)

```python
from google.adk.agents import Agent


def my_tool(param: str) -> dict:
    """Description of what this tool does.
    
    Args:
        param: Description of the parameter.
    
    Returns:
        dict with status and result.
    """
    return {"status": "success", "result": "..."}


user_agent = Agent(
    model="gemini-2.5-flash",
    name="user_agent",
    description="Personal agent for a Catch-Up user",
    instruction="""You are the personal AI agent for {user_name}.
    Your job is to negotiate meetup plans with other agents
    while defending {user_name}'s preferences and schedule.
    
    Preferences: {preferences_json}
    Recent history: {history_json}
    """,
    tools=[my_tool],
)
```

## Key rules
- Tool functions MUST have docstrings with Args and Returns — ADK parses them for the LLM
- Tool functions return dicts, not strings
- Agent instruction supports {} template vars injected at runtime
- Use `gemini-2.5-flash` as model (fast, cheap, good enough)
- Agent name must be unique per session

## Testing an agent locally
```bash
# Quick test with ADK CLI
uv run adk run src/agents/

# Or programmatically
uv run python -c "
from google.adk.agents import Agent
from src.agents.user_agent import create_agent
agent = create_agent('test_user', {...})
print(agent.name)
"
```
