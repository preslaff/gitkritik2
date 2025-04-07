import google.generativeai as genai
from gitkritik2.core.models import ReviewState
from typing import Dict, Any

def call_gemini(
    system_prompt: str,
    user_prompt: str,
    state: ReviewState,
    common: Dict[str, Any],
    debug_models: bool = False
) -> str:
    if not state.gemini_api_key:
        raise ValueError("Gemini API key is not configured.")

    genai.configure(api_key=state.gemini_api_key)

    if debug_models:
        try:
            models = genai.list_models()
            print("\n[GEMINI] Available Models:")
            for model in models:
                print(f"  • ID: {model.name}")
                print(f"    Description: {getattr(model, 'description', 'N/A')}")
                print(f"    Supported: {getattr(model, 'supported_generation_methods', [])}")
                print("  --------------------------------------------------")
        except Exception as e:
            print(f"Failed to list Gemini models: {e}")
        return "[DEBUG] Model list complete."

    model_name = state.model or "gemini-pro"
    prompt = f"{system_prompt}\n\n{user_prompt}"

    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return getattr(response, "text", "[ERROR] Gemini returned no text.")
    except Exception as e:
        return f"[ERROR] Gemini LLM call failed: {e}"
