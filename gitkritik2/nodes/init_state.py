# nodes/init_state.py

import os
from gitkritik2.core.models import ReviewState
from gitkritik2.core.config import load_config_file
from gitkritik2.core.utils import ensure_review_state

def init_state(state: dict) -> dict:
    print("[init_state] Initializing ReviewState")
    state = ensure_review_state(state)
    config_data = load_config_file()

    state.platform = os.getenv("GITKRITIK_PLATFORM", config_data.get("platform", "github"))
    state.strategy = os.getenv("GITKRITIK_STRATEGY", config_data.get("strategy", "hybrid"))
    state.model = os.getenv("GITKRITIK_MODEL", config_data.get("model", "gpt-4"))
    state.llm_provider = os.getenv("GITKRITIK_LLM_PROVIDER", config_data.get("llm_provider", "openai"))
    state.openai_api_key = os.getenv("OPENAI_API_KEY")
    state.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    state.gemini_api_key = os.getenv("GEMINI_API_KEY")
    state.repo = os.getenv("GITHUB_REPOSITORY") or config_data.get("repo")
    state.pr_number = os.getenv("GITHUB_PR_NUMBER") or config_data.get("pr_number")

    #Debbuging the dict error
    
    return state.model_dump()
