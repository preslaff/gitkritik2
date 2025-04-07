from openai import OpenAI, AuthenticationError, APIConnectionError, RateLimitError, APIError
from gitkritik2.core.models import ReviewState
from typing import Dict, Any
import datetime

def call_openai(system_prompt: str, user_prompt: str, state: ReviewState, common: Dict[str, Any], debug_quota=False) -> str:
    
    if not state.openai_api_key:
        raise ValueError("OpenAI API key is not configured.")

    client = OpenAI(api_key=state.openai_api_key)

    if debug_quota:
        try:
            now = datetime.datetime.utcnow()
            usage = client.beta.usage.retrieve(
                start_date=now.replace(day=1).date().isoformat(),
                end_date=now.date().isoformat()
            )
            used = usage["total_usage"] / 100.0
            print(f"OpenAI usage: ${used:.2f}")
        except Exception as e:
            print(f"Could not fetch usage info: {e}")

    try:
        response = client.chat.completions.create(
            model=state.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=state.temperature,
            max_tokens=state.max_tokens,
        )
        return response.choices[0].message.content.strip()

    except (AuthenticationError, APIConnectionError, RateLimitError, APIError) as e:
        print(f"[ERROR] OpenAI API call failed: {e}")
        raise
    except Exception as e:
        print(f"[ERROR] Unexpected error during OpenAI call: {e}")
        raise
