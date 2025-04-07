# nodes/init_state.py

import os
from gitkritik2.core.models import ReviewState
from gitkritik2.core.config import load_config_file
from gitkritik2.core.utils import ensure_review_state

def init_state(state: dict) -> dict:
    print("[init_state] Initializing ReviewState")
    from gitkritik2.core.utils import ensure_review_state
    state = ensure_review_state(state)

    from gitkritik2.core.config import load_config_file
    config_data = load_config_file()

    # Safe fallback: env > yaml > default
    state.platform = os.getenv("GITKRITIK_PLATFORM") or config_data.get("platform", "github")
    state.strategy = os.getenv("GITKRITIK_STRATEGY") or config_data.get("strategy", "hybrid")
    state.model = os.getenv("GITKRITIK_MODEL") or config_data.get("model", "gpt-4")
    state.llm_provider = os.getenv("GITKRITIK_LLM_PROVIDER") or config_data.get("llm_provider")
    state.openai_api_key = os.getenv("OPENAI_API_KEY")
    state.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    state.gemini_api_key = os.getenv("GEMINI_API_KEY")
    state.repo = os.getenv("GITHUB_REPOSITORY") or config_data.get("repo")
    state.pr_number = os.getenv("GITHUB_PR_NUMBER") or config_data.get("pr_number")

    return state.model_dump()

