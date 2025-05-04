# core/utils.py
import os
import subprocess
from typing import List, Optional, Tuple
from gitkritik2.core.models import ReviewState
from pydantic import ValidationError

# --- Command Execution Helpers ---

def run_subprocess_command(
    command: List[str],
    cwd: Optional[str],
    check: bool = False # Set to True to raise error on non-zero exit
    ) -> Tuple[Optional[str], Optional[str]]:
    """
    Runs a command in a subprocess, returns (stdout, stderr) tuple.
    Stdout is None only if command itself is not found or on unexpected error.
    Stderr contains error message on failure (non-zero exit or exception) or None on success.
    """
    if cwd is None:
        print("ERROR run_subprocess_command CWD was not provided!")
        return None, "Internal error: CWD not provided to command runner."
    print(f"[DEBUG run_subprocess_command] Running '{' '.join(command)}' in '{cwd}'")
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=check, # Raise CalledProcessError if check=True and exit != 0
            encoding='utf-8',
            cwd=cwd # Explicitly set CWD
        )
        stdout = process.stdout.strip() if process.stdout else ""
        stderr_msg = process.stderr.strip() if process.stderr else None # None if no stderr

        # If check=False, we need to look at returncode manually
        if not check and process.returncode != 0:
             print(f"[WARN] Command exited with code {process.returncode}: {' '.join(command)}")
             # Combine stderr with exit code info if stderr was empty
             stderr_msg = stderr_msg if stderr_msg else f"Command failed with exit code {process.returncode}"
             # Even on failure with check=False, stdout might exist
             return stdout, stderr_msg

        # If check=True, non-zero raises CalledProcessError caught below
        # If check=False and returncode is 0, stderr_msg might still have warnings (but we treat as success)
        return stdout, stderr_msg # Return None for stderr if command succeeded and produced no stderr output

    except FileNotFoundError:
        err_msg = f"Command not found: {command[0]}"
        print(f"[ERROR] {err_msg}")
        return None, err_msg # Return None for stdout on this error
    except subprocess.CalledProcessError as e:
        # This is caught only if check=True
        stdout = e.stdout.strip() if e.stdout else ""
        stderr_msg = e.stderr.strip() if e.stderr else f"Command failed with exit code {e.returncode}"
        print(f"[ERROR] Command failed (check=True): {' '.join(command)}")
        print(f"  Stderr: {stderr_msg}")
        return stdout, stderr_msg # Return potential stdout and the error
    except Exception as e:
        err_msg = f"Unexpected error running command {' '.join(command)}: {e}"
        print(f"[ERROR] {err_msg}")
        return None, err_msg # Return None for stdout on unexpected errors

def command_exists(command_name: str) -> bool:
     """Checks if a command exists and is likely executable using '--version'."""
     print(f"[DEBUG command_exists] Checking for '{command_name}'...")
     try:
          # Running '--version' is a common way to check, capture output to hide it
          stdout, stderr = run_subprocess_command([command_name, '--version'], check=True)
          # If check=True passes (no exception), the command exists.
          # We don't strictly need to check stdout/stderr here unless --version fails oddly.
          exists = True
          print(f"[DEBUG command_exists] Result for '{command_name}': {exists}")
          return exists
     except Exception:
          # Catches FileNotFoundError, CalledProcessError from check=True, etc.
          print(f"[DEBUG command_exists] Command '{command_name}' not found or '--version' failed.")
          return False

def get_merge_base(base_branch: str = "origin/main", cwd: Optional[str] = None) -> Optional[str]:
    """Finds the merge base between HEAD and the base branch using run_subprocess_command."""
    if cwd is None:
        print("[ERROR get_merge_base] CWD was not provided!")
        return None
    print(f"[DEBUG get_merge_base] Finding merge base between '{base_branch}' and HEAD in '{cwd}'")
    # ... (calls to run_subprocess_command, ensuring they pass the received cwd) ...
    # Check base branch
    _, stderr_base = run_subprocess_command(["git", "rev-parse", "--verify", f"{base_branch}^{{commit}}"], cwd=cwd,
                                            check=False)
    if stderr_base is not None:
        # ... (handle error) ...
        return None
    # Check HEAD
    _, stderr_head = run_subprocess_command(["git", "rev-parse", "--verify", "HEAD"], cwd=cwd, check=False)
    if stderr_head is not None:
        # ... (handle error) ...
        return None
    # Get merge-base
    stdout, stderr_mb = run_subprocess_command(["git", "merge-base", base_branch, "HEAD"], cwd=cwd, check=True)
    if stderr_mb is not None: # Should typically be caught by check=True, but handle just in case
         print(f"[WARN] Command 'git merge-base' succeeded but produced stderr: {stderr_mb}")
         # Continue if stdout looks valid, as some git versions might warn on stderr

    if stdout is None: # If check=True failed and returned None stdout
         print(f"[ERROR] Failed to get merge-base (stdout was None). Stderr: {stderr_mb}")
         return None

    merge_base_sha = stdout.strip()
    if not merge_base_sha or len(merge_base_sha) < 7: # Basic sanity check
         print(f"[ERROR] Invalid merge-base SHA obtained: '{merge_base_sha}'. Stderr: {stderr_mb}")
         return None

    print(f"[DEBUG get_merge_base] Found merge base: {merge_base_sha}")
    return merge_base_sha


# --- State Validation ---
def ensure_review_state(state_data) -> ReviewState:
    # ... (keep the implementation using model_validate) ...
    if isinstance(state_data, ReviewState):
        return state_data
    if isinstance(state_data, dict):
        try:
            return ReviewState.model_validate(state_data)
        except ValidationError as e:
            print(f"[ERROR] Pydantic validation failed casting dict to ReviewState:")
            print(e)
            raise TypeError(f"Could not validate input dict as ReviewState: {e}") from e
        except Exception as e:
            print(f"[ERROR] Unexpected error casting dict to ReviewState: {e}")
            raise TypeError(f"Could not convert input dict to ReviewState: {e}") from e
    raise TypeError(f"Input must be dict or ReviewState object, got {type(state_data)}")