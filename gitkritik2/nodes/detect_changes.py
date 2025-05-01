# nodes/detect_changes.py
import subprocess
from typing import List, Optional
# from gitkritik2.core.utils import ensure_review_state # Not strictly needed if working with dict

def _run_git_command(command: List[str]) -> Optional[str]:
    """Helper to run git command and return stdout or None on error."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8' # Explicitly set encoding
        )
        return result.stdout.strip()
    except FileNotFoundError:
         print(f"[ERROR] 'git' command not found. Is Git installed and in PATH?")
         return None
    except subprocess.CalledProcessError as e:
        print(f"[WARN] Git command failed: {' '.join(command)}")
        print(f"  Error: {e}")
        print(f"  Stderr: {e.stderr.strip()}")
        return None
    except Exception as e:
        print(f"[ERROR] Unexpected error running git command {' '.join(command)}: {e}")
        return None

def _get_merge_base(base_branch: str = "origin/main") -> Optional[str]:
    """Finds the merge base between HEAD and the base branch."""
    # Ensure remote is updated
    _run_git_command(["git", "fetch", "origin", "--prune", "--quiet"]) # Fetch origin quietly
    # Check if base_branch exists
    if _run_git_command(["git", "rev-parse", "--verify", base_branch, "--quiet"]) is None:
         print(f"[WARN] Base branch '{base_branch}' not found locally. Cannot determine merge base.")
         return None
    # Check if HEAD exists (e.g., not an empty repo)
    if _run_git_command(["git", "rev-parse", "--verify", "HEAD", "--quiet"]) is None:
         print("[WARN] HEAD commit not found. Skipping merge-base calculation.")
         return None

    return _run_git_command(["git", "merge-base", base_branch, "HEAD"])

def detect_changes(state: dict) -> dict:
    """
    Detects changed files based on CLI flags stored in the state dictionary.
    Updates state['changed_files'].
    """
    print("[detect_changes] Detecting changed files based on flags")

    review_all = state.get("review_all_files", False)
    review_unstaged = state.get("review_unstaged", False)
    is_ci = state.get("is_ci_mode", False)

    diff_command: List[str] = []
    description = ""

    if review_all:
        # Review all modified files (staged + unstaged) vs HEAD
        diff_command = ["git", "diff", "--name-only", "HEAD"]
        description = "all modified files (staged & unstaged)"
    elif review_unstaged:
        # Review only unstaged changes vs index
        diff_command = ["git", "diff", "--name-only"]
        description = "unstaged files"
    else:
        # Default: Review staged changes OR committed changes vs merge base
        # Prefer staged if available
        staged_files_output = _run_git_command(["git", "diff", "--name-only", "--staged", "--diff-filter=ACMRTUXB"]) # Filter for relevant changes
        if staged_files_output:
             print("[detect_changes] Found staged changes.")
             state['changed_files'] = staged_files_output.splitlines()
             return state
        else:
             print("[detect_changes] No staged changes found. Comparing committed changes against merge base with origin/main.")
             # Fallback to diffing against merge-base with origin/main
             merge_base = _get_merge_base()
             if merge_base:
                 diff_command = ["git", "diff", "--name-only", f"{merge_base}...HEAD", "--diff-filter=ACMRTUXB"]
                 description = f"committed changes since merge-base ({merge_base[:7]})"
             else:
                 # Ultimate fallback: diff against HEAD~1 if merge-base failed? Or just empty?
                 print("[WARN] Could not determine merge base. Falling back to diffing HEAD against its parent (may not be accurate for PRs).")
                 diff_command = ["git", "diff", "--name-only", "HEAD~1...HEAD", "--diff-filter=ACMRTUXB"] # Diff last commit
                 description = "last commit (fallback)"


    if diff_command:
        print(f"[detect_changes] Running: {' '.join(diff_command)}")
        changed_files_output = _run_git_command(diff_command)
        if changed_files_output is not None: # Handle case where command fails
            state['changed_files'] = changed_files_output.splitlines()
            print(f"[detect_changes] Found {len(state['changed_files'])} changed files ({description}).")
        else:
             state['changed_files'] = [] # Ensure it's empty on error
             print(f"[detect_changes] Failed to get diff for {description}.")
    else:
         # This case should ideally not be reached if logic above is sound
         print("[detect_changes] No diff command determined. Setting changed_files to empty.")
         state['changed_files'] = []

    # Ensure key exists even if empty
    state.setdefault("changed_files", [])
    return state