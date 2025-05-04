# nodes/prepare_context.py
import os
from typing import List, Optional, Dict
# Keep FileContext import if used for type hints internally
from gitkritik2.core.models import FileContext
# Import the centralized helpers
from gitkritik2.core.utils import run_subprocess_command, get_merge_base

# --- Remove local helper functions _run_git_command, _get_merge_base ---

# --- Refactor file content/diff getters to use centralized helper and CWD ---
def get_file_content_from_git(ref: str, filepath: str, cwd: str) -> Optional[str]:
    """Gets file content at a specific git reference, using specified CWD."""
    if ".." in filepath or filepath.startswith("/"):
        print(f"[WARN] Invalid file path requested: {filepath}")
        return None
    # Use check=False, failure might mean file didn't exist at ref (which is valid)
    stdout, stderr = run_subprocess_command(["git", "show", f"{ref}:{filepath}"], cwd=cwd, check=False)
    if stderr is not None:
        print(f"[WARN] `git show {ref}:{filepath}` failed: {stderr}")
        return None # Return None on error
    return stdout # Might be empty string if file was empty

def get_diff_for_file(base_ref: str, filepath: str, cwd: str) -> Optional[str]:
    """Gets the specific diff for a single file against the base reference, using specified CWD."""
    if ".." in filepath or filepath.startswith("/"):
        print(f"[WARN] Invalid file path requested for diff: {filepath}")
        return None
    # Use check=False, failure might mean file didn't exist at base_ref
    stdout, stderr = run_subprocess_command(
        ["git", "diff", "--patch-with-raw", base_ref, "--", filepath], # Use patch-with-raw for better parsing? Or stick to default.
        cwd=cwd,
        check=False
    )
    if stderr is not None:
         print(f"[WARN] `git diff {base_ref} -- {filepath}` failed: {stderr}")
         # Decide if you want diff content even if command warned/failed partially
         # return stdout if stdout else None
         return None # Safer to return None if diff command had issues
    return stdout

# --- Main Node Function ---
def prepare_context(state: dict) -> dict:
    """
    Prepares FileContext objects (as dicts) for each changed file,
    including before/after content and diffs relative to the merge base. Uses CWD.
    """
    print("[prepare_context] Preparing file context and diffs")
    # Determine target directory ONCE
    target_repo_dir = os.getcwd()
    print(f"[prepare_context] Operating in target directory: {target_repo_dir}")

    changed_files: List[str] = state.get("changed_files", [])
    file_contexts: Dict[str, dict] = {} # Store FileContext info as dicts

    if not changed_files:
        print("[prepare_context] No changed files detected.")
        state["file_contexts"] = {}
        return state

    # Determine the base reference using the utility function with CWD
    base_ref = get_merge_base(cwd=target_repo_dir)
    if not base_ref:
        print("[ERROR] Cannot prepare context: Failed to determine merge base. Trying origin/main as fallback.")
        base_ref = "origin/main" # Fallback

    print(f"[prepare_context] Using base reference: {base_ref}")

    for filepath in changed_files:
        print(f"  Processing: {filepath}")
        # Pass CWD to helper functions
        before_content = get_file_content_from_git(base_ref, filepath, cwd=target_repo_dir)

        after_content: Optional[str] = None
        # --- Reading 'after' content using absolute path derived from CWD ---
        absolute_filepath = os.path.abspath(os.path.join(target_repo_dir, filepath))
        try:
            if os.path.exists(absolute_filepath) and os.path.isfile(absolute_filepath):
                with open(absolute_filepath, "r", encoding="utf-8") as f:
                    after_content = f.read()
            else:
                 # File exists in git diff list but not on disk (e.g., deleted)
                 print(f"    File not found in working directory (possibly deleted): {absolute_filepath}")
                 after_content = None # Correct state for deleted file
        except Exception as e:
             print(f"    Error reading file from working directory {absolute_filepath}: {e}")
             after_content = f"[ERROR] Could not read file: {e}"

        # Pass CWD to helper function
        file_diff = get_diff_for_file(base_ref, filepath, cwd=target_repo_dir)

        # Create FileContext data as a dictionary
        file_contexts[filepath] = {
            "path": filepath, # Keep relative path as key/identifier
            "before": before_content,
            "after": after_content,
            "diff": file_diff,
            "strategy": state.get("strategy", "hybrid"),
            "symbol_definitions": {}, # Initialize for context_agent
        }

    state["file_contexts"] = file_contexts
    return state