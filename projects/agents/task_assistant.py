import logging
from .openrouter_client import call_openrouter

# logger = logging.getLogger('agents.task_assistant')


TASK_ASSISTANT_SYSTEM_PROMPT = """
You are an expert project management assistant helping developers complete their tasks successfully.

Your role is to provide:
1. Step-by-step instructions to complete the task
2. Best practices and tips
3. Common pitfalls to avoid
4. Resource recommendations (tools, libraries, documentation)
5. Estimated time breakdown for sub-steps

Be specific, actionable, and encouraging. Format your response in clear markdown with:
- Numbered steps
- pseudocode examples where relevant
- Links to documentation when helpful
- Tips highlighted with 💡
- Warnings highlighted with ⚠️

Keep your guidance concise but comprehensive (aim for 300-500 words).
"""


def generate_task_guidance(task_title: str, task_description: str, project_goal: str) -> str:
    """
    Generate detailed guidance for completing a specific task.
    """
    # logger.info(f"Generating guidance for task: {task_title}")
    
    user_prompt = f"""
    Task: {task_title}
    Description: {task_description}
    Project Context: {project_goal}

    Please provide detailed guidance on how to complete this task successfully.
    """
    
    messages = [
        {"role": "system", "content": TASK_ASSISTANT_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    
    try:
        response = call_openrouter(messages)
        guidance = response["choices"][0]["message"]["content"]
        # logger.info(f"Successfully generated guidance for: {task_title}")
        return guidance
    except Exception as e:
        # logger.error(f"Failed to generate guidance: {e}")
        raise ValueError(f"Failed to generate task guidance: {str(e)}")