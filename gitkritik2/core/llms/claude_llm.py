from anthropic import Anthropic
from gitkritik2.core.models import ReviewState
from typing import Dict, Any

def call_claude(system_prompt: str, user_prompt: str, state: ReviewState, common: Dict[str, Any]) -> str:
    if not state.anthropic_api_key:
        raise ValueError("Anthropic API key is not configured.")

    client = Anthropic(api_key=state.anthropic_api_key)

    response = client.messages.create(
        model=state.model,
        max_tokens=getattr(state, "max_tokens", 2048),
        temperature=getattr(state, "temperature", 0.3),
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text if response.content else "[ERROR] Claude returned no content."
