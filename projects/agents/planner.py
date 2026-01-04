import json
from .openrouter_client import call_openrouter


PLANNER_SYSTEM_PROMPT = """
You are an autonomous project planning agent.

Break down the project goal into an ordered list of tasks.

Rules:
- Return ONLY valid JSON
- No explanations
- Tasks must be actionable
- estimated_days must be an integer

Output format:
{
  "tasks": [
    {
      "title": "...",
      "description": "...",
      "estimated_days": 3
    }
  ]
}
"""


def generate_task_plan(goal: str):
    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": f"Project goal:\n{goal}"},
    ]

    response = call_openrouter(messages)

    content = response["choices"][0]["message"]["content"]

    try:
        parsed = json.loads(content)
        return parsed["tasks"]
    except (json.JSONDecodeError, KeyError):
        raise ValueError("Planner agent returned invalid JSON")
