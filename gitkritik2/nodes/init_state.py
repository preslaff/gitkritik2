# nodes/init_state.py
import os
from gitkritik2.core.models import ReviewState # Keep for reference/casting if needed internally
from gitkritik2.core.config import load_config_file
from gitkritik2.core.utils import ensure_review_state # Keep if casting internally

# Default values
DEFAULT_PLATFORM = "github"
DEFAULT_STRATEGY = "hybrid"
DEFAULT_MODEL = "gpt-4-turbo-preview" # Example default
DEFAULT_LLM_PROVIDER = "openai" # Example default

def init_state(state: dict) -> dict:
    """
    Initializes the review state by loading configuration from environment
    variables and a configuration file (.kritikrc.yaml).

    Accepts and returns a dictionary compatible with LangGraph StateGraph(dict).
    """
    print("[init_state] Initializing ReviewState from env and config")

    # Load config from file if specified/present
    config_path = state.get("config_file_path") # Get path from initial state if provided via CLI
    yaml_config = load_config_file(config_path) # Pass path to loader

    # --- Populate State Dictionary ---
    # Order of precedence: Environment Variable > YAML Config > Default Value

    # Core settings
    state['platform'] = os.getenv("GITKRITIK_PLATFORM") or yaml_config.get("platform", DEFAULT_PLATFORM)
    state['strategy'] = os.getenv("GITKRITIK_STRATEGY") or yaml_config.get("strategy", DEFAULT_STRATEGY)
    state['model'] = os.getenv("GITKRITIK_MODEL") or yaml_config.get("model", DEFAULT_MODEL)
    state['llm_provider'] = os.getenv("GITKRITIK_LLM_PROVIDER") or yaml_config.get("llm_provider", DEFAULT_LLM_PROVIDER)

    # Repo/PR Info (often comes from CI env vars, fallback to config)
    # Using specific CI variables as fallbacks
    ci_repo = os.getenv("GITHUB_REPOSITORY") or os.getenv("CI_PROJECT_PATH")
    ci_pr_mr_num = os.getenv("GITHUB_PR_NUMBER") or os.getenv("CI_MERGE_REQUEST_IID")

    state['repo'] = os.getenv("GITKRITIK_REPO") or ci_repo or yaml_config.get("repo")
    state['pr_number'] = os.getenv("GITKRITIK_PR_NUMBER") or ci_pr_mr_num or yaml_config.get("pr_number")

    # API Keys (Loaded ONLY from environment variables for security)
    state['openai_api_key'] = os.getenv("OPENAI_API_KEY")
    state['anthropic_api_key'] = os.getenv("ANTHROPIC_API_KEY")
    state['gemini_api_key'] = os.getenv("GEMINI_API_KEY")
    # Add other keys if needed (e.g., GITLAB_TOKEN, GITHUB_TOKEN are often used directly)

    # LLM parameters (Allow override via Env -> YAML -> Defaults)
    try:
        state['temperature'] = float(os.getenv("GITKRITIK_TEMPERATURE") or yaml_config.get("temperature", 0.3))
    except ValueError:
        print("[WARN] Invalid temperature value, using default 0.3")
        state['temperature'] = 0.3
    try:
        state['max_tokens'] = int(os.getenv("GITKRITIK_MAX_TOKENS") or yaml_config.get("max_tokens", 2048))
    except ValueError:
        print("[WARN] Invalid max_tokens value, using default 2048")
        state['max_tokens'] = 2048

    # Ensure core data structures exist if not already present
    state.setdefault("changed_files", [])
    state.setdefault("file_contexts", {})
    state.setdefault("agent_results", {})
    state.setdefault("inline_comments", [])
    state.setdefault("summary_review", None)

    # Optionally print loaded config (excluding keys)
    print(f"  Platform: {state['platform']}")
    print(f"  Provider: {state['llm_provider']}")
    print(f"  Model: {state['model']}")
    print(f"  Strategy: {state['strategy']}")
    print(f"  Repo: {state.get('repo', 'Not Set')}")
    print(f"  PR/MR #: {state.get('pr_number', 'Not Set')}")
    print(f"  Temp: {state['temperature']}, Max Tokens: {state['max_tokens']}")
    # DO NOT PRINT API KEYS

    return state # Return the updated dictionary