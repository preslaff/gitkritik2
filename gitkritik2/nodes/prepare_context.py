# nodes/prepare_context.py
import subprocess
from typing import List, Optional, Dict
from gitkritik2.core.models import FileContext # Keep for internal structure/typing
# from gitkritik2.core.utils import ensure_review_state # Not needed

def _run_git_command(command: List[str]) -> Optional[str]:
    """Helper duplicated for simplicity, move to shared utils if preferred."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        return result.stdout
    except Exception: # Catch broad exceptions here as content might be missing legitimately
        return None

def _get_merge_base(base_branch: str = "origin/main") -> Optional[str]:
    """Helper duplicated for simplicity."""
    try:
        # Ensure remote is updated (optional, detect_changes might do it)
        # subprocess.run(["git", "fetch", "origin", "--prune", "--quiet"], check=True)
        base = subprocess.run(["git", "merge-base", base_branch, "HEAD"], capture_output=True, text=True, check=True, encoding='utf-8')
        return base.stdout.strip()
    except Exception:
        print(f"[WARN] Failed to get merge base with {base_branch} in prepare_context.")
        return None

def get_file_content_from_git(ref: str, filepath: str) -> Optional[str]:
    """Gets file content at a specific git reference."""
    # Basic path sanitization
    if ".." in filepath or filepath.startswith("/"):
        print(f"[WARN] Invalid file path requested: {filepath}")
        return None
    return _run_git_command(["git", "show", f"{ref}:{filepath}"])

def get_diff_for_file(base_ref: str, filepath: str) -> Optional[str]:
    """Gets the specific diff for a single file against the base reference."""
    if ".." in filepath or filepath.startswith("/"):
        print(f"[WARN] Invalid file path requested for diff: {filepath}")
        return None
    # Using unified=0 might miss important context for LLMs, use default unified diff
    return _run_git_command(["git", "diff", base_ref, "--", filepath])

def prepare_context(state: dict) -> dict:
    """
    Prepares FileContext objects (as dicts) for each changed file,
    including before/after content and diffs relative to the merge base.
    """
    print("[prepare_context] Preparing file context and diffs")
    changed_files: List[str] = state.get("changed_files", [])
    file_contexts: Dict[str, dict] = {} # Store FileContext info as dicts

    if not changed_files:
        print("[prepare_context] No changed files detected.")
        state["file_contexts"] = {}
        return state

    # Determine the base reference (consistent with detect_changes default logic)
    base_ref = _get_merge_base()
    if not base_ref:
        print("[ERROR] Cannot prepare context: Failed to determine merge base. Trying origin/main.")
        # Fallback, might be inaccurate if origin/main isn't fetched or relevant
        base_ref = "origin/main"

    print(f"[prepare_context] Using base reference: {base_ref}")

    for filepath in changed_files:
        print(f"  Processing: {filepath}")
        # Get content before the changes
        before_content = get_file_content_from_git(base_ref, filepath)

        # Get content after the changes (from working directory)
        after_content: Optional[str] = None
        try:
            # Ensure working dir path is correct relative to where script runs
            # Assuming script runs from repo root
            with open(filepath, "r", encoding="utf-8") as f:
                after_content = f.read()
        except FileNotFoundError:
             # File might have been deleted in the current changes
             print(f"    File not found in working directory (possibly deleted): {filepath}")
             after_content = None # Explicitly None for deleted files
        except Exception as e:
             print(f"    Error reading file from working directory {filepath}: {e}")
             after_content = f"[ERROR] Could not read file: {e}" # Store error

        # Get the specific diff for this file
        file_diff = get_diff_for_file(base_ref, filepath)

        # Create FileContext data as a dictionary
        file_contexts[filepath] = {
            "path": filepath,
            "before": before_content, # Will be None if added file or git error
            "after": after_content,   # Will be None if deleted file or read error
            "diff": file_diff,       # Will be None if git diff failed
            "strategy": state.get("strategy", "hybrid"), # Carry over strategy
            "symbol_definitions": {}, # Initialize empty dict for context_agent
        }

    state["file_contexts"] = file_contexts
    # 'context_chunks' doesn't seem necessary if agents use file_contexts directly
    # state.pop("context_chunks", None) # Remove if not used downstream

    return state