import os
from gitkritik2.core.models import ReviewState
from gitkritik2.core.llms.openai_llm import call_openai
from gitkritik2.core.llms.claude_llm import call_claude
from gitkritik2.core.llms.gemini_llm import call_gemini
from gitkritik2.core.llms.local_llm import call_local

def call_llm(system_prompt: str, user_prompt: str, state: ReviewState, common: dict) -> str:
    
    provider = state.llm_provider
    if not provider:
        raise ValueError("No LLM provider configured. Please set 'llm_provider' in .kritikrc.yaml or env.")

    model = state.model
    if not model:
        raise ValueError("No LLM model configured. Please set 'model' in .kritikrc.yaml or env.")
    
    if provider == "openai":
        api_key = state.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing.")
        return call_openai(system_prompt, user_prompt, state, common)

    elif provider == "claude":
        api_key = state.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is missing.")
        return call_claude(system_prompt, user_prompt, state, common)

    elif provider == "gemini":
        api_key = state.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing.")
        return call_gemini(system_prompt, user_prompt, state, common)

    elif provider == "local":
        return call_local(system_prompt, user_prompt, state, common)

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
