# core/llm_interface.py
import os
from gitkritik2.core.models import ReviewState
from typing import Dict, Any, Optional

# LangChain imports
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama

# Simple cache for initialized models within a single run
_llm_cache: Dict[str, BaseChatModel] = {}

def get_llm(state: ReviewState) -> Optional[BaseChatModel]:
    """Gets an initialized LangChain ChatModel based on ReviewState."""
    provider = state.llm_provider
    model_name = state.model
    cache_key = f"{provider}_{model_name}"

    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    if not provider:
        print("[ERROR] LLM provider not configured in state.")
        return None
    if not model_name:
        print("[ERROR] LLM model not configured in state.")
        return None

    llm: BaseChatModel | None = None
    try:
        if provider == "openai":
            api_key = state.openai_api_key # Loaded during init_state
            if not api_key: raise ValueError("OPENAI_API_KEY is missing.")
            llm = ChatOpenAI(
                model=model_name, api_key=api_key,
                temperature=state.temperature, max_tokens=state.max_tokens,
            )
        elif provider == "anthropic": # Changed from 'claude' to match langchain pkg
            api_key = state.anthropic_api_key
            if not api_key: raise ValueError("ANTHROPIC_API_KEY is missing.")
            llm = ChatAnthropic(
                model=model_name, api_key=api_key,
                temperature=state.temperature, max_tokens=state.max_tokens,
            )
        elif provider == "gemini":
            api_key = state.gemini_api_key
            if not api_key: raise ValueError("GEMINI_API_KEY is missing.")
            llm = ChatGoogleGenerativeAI(
                model=model_name, google_api_key=api_key,
                temperature=state.temperature, max_output_tokens=state.max_tokens,
                # safety_settings=... # Adjust safety settings if needed
                # convert_system_message_to_human=True # May be needed
            )
        elif provider == "local":
            backend = os.getenv("GITKRITIK_LOCAL_BACKEND", "ollama").lower()
            local_model_name = os.getenv("GITKRITIK_LOCAL_MODEL", model_name)
            if backend == "ollama":
                base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                print(f"[LLM] Using Ollama backend: model={local_model_name}, base_url={base_url}")
                llm = ChatOllama(
                    base_url=base_url, model=local_model_name,
                    temperature=state.temperature,
                    # Consider adding num_ctx, top_k, top_p if needed
                )
            else:
                 raise ValueError(f"Unsupported local backend '{backend}'. Use 'ollama'.")
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        if llm:
            _llm_cache[cache_key] = llm
        return llm

    except Exception as e:
        print(f"[ERROR] Failed to initialize LLM ({provider}/{model_name}): {e}")
        return None