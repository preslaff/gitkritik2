# core/config.py

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from gitkritik2.core.models import Settings

load_dotenv()  # Load from .env if present

def load_config_file() -> dict:
    """Loads YAML config from .kritikrc.yaml if present."""
    path = Path(".kritikrc.yaml")
    if path.exists():
        with open(path, "r") as f:
            return yaml.safe_load(f)
    return {}

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

