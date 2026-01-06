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


def generate_task_guidance(task_title: str, task_description: str, project_goal: str, conversation_history: list = None) -> dict:
    """
    Generate guidance with optional conversation history for follow-up questions.
    
    Args:
        task_title: The task title
        task_description: The task description
        project_goal: The overall project goal
        conversation_history: List of previous messages [{"role": "user", "content": "..."}, ...]
    
    Returns:
        dict with 'content' and 'metadata' (tokens used, model, etc.)
    """
    
    system_prompt = """
        You are an expert project management assistant helping developers complete their tasks successfully.

        Your role is to provide:
        1. Step-by-step instructions to complete the task
        2. Best practices and tips
        3. Common pitfalls to avoid
        4. Resource recommendations (tools, libraries, documentation)
        5. pseudocode examples where relevant
        6. Estimated time breakdown for sub-steps

        Be specific, actionable, and encouraging. Format your response in clear markdown.
        Keep your guidance concise but comprehensive (aim for 300-500 words).
        """
    
    # Build message history
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history if exists
    if conversation_history:
        messages.extend(conversation_history)
    else:
        # Initial guidance request
        user_prompt = f"""
        Task: {task_title}
        Description: {task_description}
        Project Context: {project_goal}

        Please provide detailed guidance on how to complete this task successfully.
        """
        messages.append({"role": "user", "content": user_prompt})
    
    try:
        response = call_openrouter(messages)
        
        guidance_content = response["choices"][0]["message"]["content"]
        
        # Extract metadata
        metadata = {
            "model": response.get("model", "unknown"),
            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
        }
        
        
        return {
            "content": guidance_content,
            "metadata": metadata
        }
    except Exception as e:
        raise ValueError(f"Failed to generate task guidance: {str(e)}")