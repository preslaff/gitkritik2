# nodes/resolve_context.py
import os
# import subprocess # No longer needed directly
import requests
import json
from typing import Optional, Tuple
from gitkritik2.core.models import ReviewState # Keep for internal type hints
# Import the centralized helpers
from gitkritik2.core.utils import run_subprocess_command, command_exists

# --- Remove local _run_command helper ---

# --- Refactor git callers to use centralized helper and pass CWD ---
def get_remote_url(remote_name: str = "origin", cwd: str = None) -> Optional[str]:
    """Gets the URL of a specific git remote."""
    stdout, stderr = run_subprocess_command(["git", "remote", "get-url", remote_name], cwd=cwd)
    if stderr:
        print(f"[resolve_context][WARN] Failed to get remote URL for '{remote_name}': {stderr}")
        return None
    return stdout

def get_current_branch(cwd: str = None) -> Optional[str]:
    """Gets the current git branch name."""
    stdout, stderr = run_subprocess_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if stdout == "HEAD":
        print("[resolve_context][WARN] Git is in a detached HEAD state. Cannot determine branch name.")
        return None
    if stderr:
        print(f"[resolve_context][WARN] Failed to get current branch: {stderr}")
        return None
    return stdout

# --- detect_platform_and_repo remains the same ---
# nodes/resolve_context.py

# ... (other imports and functions) ...

def detect_platform_and_repo(remote_url: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Detects platform (github/gitlab) and repo slug from remote URL."""
    if not remote_url:
        return None, None

    platform: Optional[str] = None # Initialize with type hint
    repo_slug: Optional[str] = None # Initialize with type hint

    if "github.com" in remote_url:
        platform = "github"
        if remote_url.startswith("git@"):
             repo_slug = remote_url.split(":")[-1].replace(".git", "")
        else:
             repo_slug = remote_url.split("github.com/")[-1].replace(".git", "")
    elif "gitlab.com" in remote_url:
        platform = "gitlab"
        if remote_url.startswith("git@"):
             repo_slug = remote_url.split(":")[-1].replace(".git", "")
        else:
             repo_slug = remote_url.split("gitlab.com/")[-1].replace(".git", "")
    else:
        print(f"[resolve_context][WARN] Could not determine platform from remote URL: {remote_url}")
        # --- FIX: Assign default values here ---
        platform = "unknown"
        repo_slug = None # Or "" if preferred for unknown platform
        # --- End FIX ---

    # This warning check is fine
    if repo_slug and len(repo_slug.split('/')) != 2:
         print(f"[resolve_context][WARN] Parsed repo slug '{repo_slug}' does not look like owner/repo.")
         # Optional: Set repo_slug to None if format is critical downstream
         # repo_slug = None

    # Now platform is guaranteed to be assigned before returning
    return platform, repo_slug

# ... (rest of the file) ...


# --- get_github_pr_number_via_api remains the same (uses requests) ---
# nodes/resolve_context.py

# ... (imports and other functions) ...

def get_github_pr_number_via_api(repo_slug: str, branch: str) -> Optional[str]:
    """Fetches PR number from GitHub API."""
    print(f"[resolve_context] Trying GitHub API for branch '{branch}' in repo '{repo_slug}'...")
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("[resolve_context][WARN] GITHUB_TOKEN not set. Cannot query API.")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    owner = repo_slug.split('/')[0]
    encoded_branch = requests.utils.quote(branch, safe='')
    url = f"https://api.github.com/repos/{repo_slug}/pulls?head={owner}:{encoded_branch}&state=open"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        pulls = response.json()
        if pulls and isinstance(pulls, list):
            # Ensure we use a consistent variable name and return it
            found_pr_number = str(pulls[0]["number"])
            print(f"[resolve_context] Found PR #{found_pr_number} via GitHub API.")
            return found_pr_number # Return the found number
        else:
            print(f"[resolve_context] No open PR found for branch '{branch}' via API.")
            return None # Return None if no PR found
    except requests.exceptions.RequestException as e:
        print(f"[resolve_context][WARN] GitHub API call failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Response: {e.response.status_code} {e.response.text}")
        return None # Return None on error
    except Exception as e: # Catch JSONDecodeError etc.
        print(f"[resolve_context][WARN] Error processing GitHub API response: {e}")
        return None # Return None on error

    # --- FIX: Remove this line ---
    # return pr_number # This line is unreachable and pr_number might not be defined
    # --- End FIX ---

# --- Refactor gh cli check and call ---
def get_github_pr_number_via_gh_cli(branch: str, cwd: str = None) -> Optional[str]:
    """Fetches PR number using GitHub CLI ('gh'), checks existence first."""
    print(f"[resolve_context] Trying GitHub CLI ('gh') to find PR for branch '{branch}'...")

    # Check if gh exists before trying to run it
    if not command_exists("gh"):
         print("[resolve_context][WARN] 'gh' command not found or not executable. Skipping CLI check.")
         return None

    command = ["gh", "pr", "list", "--head", branch, "--limit", "1", "--json", "number", "--jq", ".[0].number"]
    # Pass CWD - gh commands often depend on being in the correct repo dir
    stdout, stderr = run_subprocess_command(command, cwd=cwd)

    if stderr is not None:
         # Allow "no pull requests found" or similar messages
         no_pr_msgs = ["no pull requests found", "no open pull request found"]
         is_no_pr_found = any(msg in stderr.lower() for msg in no_pr_msgs)
         if not is_no_pr_found:
              # Log other errors
              print(f"[resolve_context][WARN] 'gh pr list' command failed or produced stderr: {stderr}")
         else:
             print(f"[resolve_context] No open PR found for branch '{branch}' via GitHub CLI.")
         return None # Return None if error or no PR found

    if stdout:
        pr_number = stdout.strip()
        if pr_number.isdigit():
             print(f"[resolve_context] Found PR #{pr_number} via GitHub CLI.")
             return pr_number
        else:
             print(f"[resolve_context][WARN] GitHub CLI returned non-numeric output: {stdout}")
             return None
    else:
         # Should be covered by stderr check, but as fallback
         print(f"[resolve_context] No PR number returned by GitHub CLI.")
         return None


# --- get_gitlab_mr_number remains the same (uses requests) ---
def get_gitlab_mr_number(repo_slug: str, branch: str) -> Optional[str]:
    # ... (no changes needed here) ...
    return mr_iid


# --- Main Node Function ---
def resolve_context(state: dict) -> dict:
    """
    Resolves platform, repository, and PR/MR context.
    Uses CI environment variables first, then falls back to git/API/CLI calls locally.
    """
    print("[resolve_context] Resolving platform, repo, and PR/MR context...")
    # Determine target directory ONCE
    target_repo_dir = os.getcwd()
    print(f"[resolve_context] Operating in target directory: {target_repo_dir}")

    # Get initial values from state
    is_ci = state.get("is_ci_mode", False)
    platform = state.get("platform")
    repo = state.get("repo")
    pr_number = state.get("pr_number")

    # --- Determine Platform and Repo Slug (use Git remote as ground truth) ---
    # Pass CWD to git helpers
    remote_url = get_remote_url(cwd=target_repo_dir)
    detected_platform, detected_repo = detect_platform_and_repo(remote_url)

    if detected_platform and detected_repo:
        print(f"[resolve_context] Detected via Git: Platform='{detected_platform}', Repo='{detected_repo}'")
        state['platform'] = detected_platform
        state['repo'] = detected_repo
        platform = detected_platform
        repo = detected_repo
    # ... (rest of logic using platform/repo) ...

    # --- Determine PR/MR Number ---
    if not pr_number: # Only fetch if not provided by CI/config
        # Pass CWD to git helpers
        branch = get_current_branch(cwd=target_repo_dir)
        if branch and repo:
            print(f"[resolve_context] Current branch: '{branch}'. Attempting to find associated PR/MR...")
            if platform == "github":
                if not is_ci:
                     # Pass CWD to gh helper
                     pr_number = get_github_pr_number_via_gh_cli(branch, cwd=target_repo_dir)
                if not pr_number:
                     pr_number = get_github_pr_number_via_api(repo, branch)
            elif platform == "gitlab":
                pr_number = get_gitlab_mr_number(repo, branch)
            # ... (rest of PR/MR number logic) ...
            state['pr_number'] = pr_number if pr_number else None # Ensure None if not found
        else:
             print("[resolve_context] Cannot fetch PR/MR number without current branch or repo slug.")
             state['pr_number'] = None

    # ... (Final log) ...
    return state