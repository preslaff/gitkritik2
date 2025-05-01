# core/config.py
import os
import yaml
from pathlib import Path
from typing import Optional # Import Optional
from dotenv import load_dotenv
from gitkritik2.core.models import Settings

load_dotenv()

DEFAULT_CONFIG_FILENAME = ".kritikrc.yaml"

# Modify the function signature to accept an optional path
def load_config_file(config_path: Optional[str] = None) -> dict:
    """
    Loads YAML config from the specified path or the default .kritikrc.yaml.
    """
    # Use the provided path, otherwise fall back to the default filename
    path_to_check = Path(config_path) if config_path else Path(DEFAULT_CONFIG_FILENAME)

    if path_to_check.exists() and path_to_check.is_file():
        print(f"[Config] Loading configuration from: {path_to_check}")
        try:
            with open(path_to_check, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
                # Ensure it returns a dict even if YAML is empty or invalid structure
                return config_data if isinstance(config_data, dict) else {}
        except Exception as e:
             print(f"[ERROR] Failed to load or parse config file {path_to_check}: {e}")
             return {} # Return empty dict on error
    else:
        # Only print if a specific path was given and not found
        if config_path:
             print(f"[WARN] Specified config file not found: {config_path}")
        else:
             print(f"[Config] Default config file '{DEFAULT_CONFIG_FILENAME}' not found. Using defaults/env vars.")
        return {} # Return empty dict if file doesn't exist

def load_kritik_config() -> Settings:
    file_config = load_config_file()

    # Env takes precedence over YAML
    return Settings(
        platform=os.getenv("GITKRITIK_PLATFORM") or file_config.get("platform", "github"),
        model=os.getenv("GITKRITIK_MODEL") or file_config.get("model", "gpt-4"),
        strategy=os.getenv("GITKRITIK_STRATEGY") or file_config.get("strategy", "hybrid"),
        repo=os.getenv("GITHUB_REPOSITORY") or os.getenv("CI_PROJECT_PATH") or file_config.get("repo"),
        pr_number=os.getenv("GITHUB_PR_NUMBER") or os.getenv("CI_MERGE_REQUEST_IID") or file_config.get("pr_number")
    )

