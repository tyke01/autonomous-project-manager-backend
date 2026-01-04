import requests
import json
from django.conf import settings
from decouple import config


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def call_openrouter(messages, model=settings.PLANNER_AI_MODEL):
    headers = {
        "Authorization": f"Bearer {config('OPENROUTER_API_KEY')}",
        # "HTTP-Referer": settings.OPENROUTER_SITE_URL,
        # "X-Title": settings.OPENROUTER_SITE_NAME,
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,  # Lower = more deterministic
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        data=json.dumps(payload),
        timeout=60,
    )

    response.raise_for_status()
    return response.json()
