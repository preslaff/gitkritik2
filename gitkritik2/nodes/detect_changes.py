# nodes/detect_changes.py
import os
from typing import List, Optional
# Import the centralized helpers
from gitkritik2.core.utils import run_subprocess_command, get_merge_base

def detect_changes(state: dict) -> dict:
    """
    Detects changed files based on CLI flags stored in the state dictionary.
    Updates state['changed_files']. Uses centralized command runner with CWD.
    """
    print("[detect_changes] Detecting changed files based on flags")
    # Determine target directory ONCE
    target_repo_dir = os.getcwd()
    print(f"[detect_changes] Operating in target directory: {target_repo_dir}")

    review_all = state.get("review_all_files", False)
    review_unstaged = state.get("review_unstaged", False)
    # is_ci = state.get("is_ci_mode", False) # Not directly needed here anymore

    diff_command: List[str] = []
    description = ""
    changed_files_output: Optional[str] = None
    cmd_stderr: Optional[str] = None

    if review_all:
        # Review all modified files (staged + unstaged) vs HEAD
        diff_command = ["git", "diff", "--name-only", "HEAD"]
        description = "all modified files (staged & unstaged)"
        changed_files_output, cmd_stderr = run_subprocess_command(diff_command, cwd=target_repo_dir)
    elif review_unstaged:
        # Review only unstaged changes vs index
        diff_command = ["git", "diff", "--name-only"]
        description = "unstaged files"
        changed_files_output, cmd_stderr = run_subprocess_command(diff_command, cwd=target_repo_dir)
    else:
        # Default: Review staged changes OR committed changes vs merge base
        description = "staged files"
        staged_files_output, staged_cmd_stderr = run_subprocess_command(
            ["git", "diff", "--name-only", "--staged", "--diff-filter=ACMRTUXB"], # Filter for relevant changes
            cwd=target_repo_dir
        )

        if staged_cmd_stderr is None and staged_files_output: # Check stderr is None (success) and stdout has content
             print("[detect_changes] Found staged changes.")
             state['changed_files'] = staged_files_output.splitlines()
             return state # Return early if staged files found
        else:
             if staged_cmd_stderr is not None:
                  print(f"[WARN] Failed to get staged diff: {staged_cmd_stderr}")
             print("[detect_changes] No staged changes found or error occurred. Comparing committed changes against merge base with origin/main.")
             # Fallback to diffing against merge-base with origin/main
             merge_base = get_merge_base(cwd=target_repo_dir) # Pass CWD
             if merge_base:
                 diff_command = ["git", "diff", "--name-only", f"{merge_base}...HEAD", "--diff-filter=ACMRTUXB"]
                 description = f"committed changes since merge-base ({merge_base[:7]})"
                 changed_files_output, cmd_stderr = run_subprocess_command(diff_command, cwd=target_repo_dir)
             else:
                 # Ultimate fallback: diff against HEAD~1 if merge-base failed
                 print("[WARN] Could not determine merge base. Falling back to diffing HEAD against its parent (may not be accurate for PRs).")
                 diff_command = ["git", "diff", "--name-only", "HEAD~1...HEAD", "--diff-filter=ACMRTUXB"] # Diff last commit
                 description = "last commit (fallback)"
                 changed_files_output, cmd_stderr = run_subprocess_command(diff_command, cwd=target_repo_dir)


    # Process the result from the chosen diff command (if not returned early)
    if changed_files_output is not None and cmd_stderr is None:
        state['changed_files'] = changed_files_output.splitlines()
        print(f"[detect_changes] Found {len(state['changed_files'])} changed files ({description}).")
    else:
         state['changed_files'] = [] # Ensure it's empty on error or no output
         print(f"[detect_changes] Failed to get diff or no changes found for {description}. Error: {cmd_stderr}")

    # Ensure key exists even if empty
    state.setdefault("changed_files", [])
    return state