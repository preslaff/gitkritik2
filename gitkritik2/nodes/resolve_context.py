# nodes/resolve_context.py
import os
import subprocess
import requests
import json # Needed for gh cli output parsing
from typing import Optional, Tuple

# Import the Pydantic model for internal use and type hints
from gitkritik2.core.models import ReviewState
from gitkritik2.core.utils import ensure_review_state

# --- Helper Functions ---

def _run_command(command: list[str], check: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """Runs a command, returns (stdout, stderr) tuple. Stdout/Stderr are None on error."""
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=check, # Set to True to raise CalledProcessError on non-zero exit
            encoding='utf-8'
        )
        return process.stdout.strip() if process.stdout else "", process.stderr.strip() if process.stderr else ""
    except FileNotFoundError:
        # Command not found (e.g., git or gh not installed)
        return None, f"Command not found: {command[0]}"
    except subprocess.CalledProcessError as e:
        # Command returned non-zero exit code
        return e.stdout.strip() if e.stdout else "", e.stderr.strip() if e.stderr else f"Command failed with exit code {e.returncode}"
    except Exception as e:
        # Other unexpected errors
        return None, f"Unexpected error running command {' '.join(command)}: {e}"

def get_remote_url(remote_name: str = "origin") -> Optional[str]:
    """Gets the URL of a specific git remote."""
    stdout, stderr = _run_command(["git", "remote", "get-url", remote_name])
    if stderr:
        print(f"[resolve_context][WARN] Failed to get remote URL for '{remote_name}': {stderr}")
        return None
    return stdout

def get_current_branch() -> Optional[str]:
    """Gets the current git branch name."""
    stdout, stderr = _run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    # Handle detached HEAD state
    if stdout == "HEAD":
        print("[resolve_context][WARN] Git is in a detached HEAD state. Cannot determine branch name automatically.")
        return None
    if stderr:
        print(f"[resolve_context][WARN] Failed to get current branch: {stderr}")
        return None
    return stdout

def detect_platform_and_repo(remote_url: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Detects platform (github/gitlab) and repo slug from remote URL."""
    if not remote_url:
        return None, None

    platform = None
    repo_slug = None
    if "github.com" in remote_url:
        platform = "github"
        # Handle different URL formats (HTTPS, SSH)
        if remote_url.startswith("git@"): # SSH format: git@github.com:owner/repo.git
             repo_slug = remote_url.split(":")[-1].replace(".git", "")
        else: # Assume HTTPS format: https://github.com/owner/repo.git
             repo_slug = remote_url.split("github.com/")[-1].replace(".git", "")
    elif "gitlab.com" in remote_url:
        platform = "gitlab"
        if remote_url.startswith("git@"): # SSH format: git@gitlab.com:owner/repo.git
             repo_slug = remote_url.split(":")[-1].replace(".git", "")
        else: # Assume HTTPS format: https://gitlab.com/owner/repo.git
             repo_slug = remote_url.split("gitlab.com/")[-1].replace(".git", "")
    else:
        print(f"[resolve_context][WARN] Could not determine platform from remote URL: {remote_url}")
        platform = "unknown"

    if repo_slug and len(repo_slug.split('/')) != 2:
         print(f"[resolve_context][WARN] Parsed repo slug '{repo_slug}' does not look like owner/repo.")
         # Decide if you want to return None or the potentially invalid slug
         # return platform, None
         return platform, repo_slug # Return potentially invalid slug for now

    return platform, repo_slug

def get_github_pr_number_via_api(repo_slug: str, branch: str) -> Optional[str]:
    """Fetches PR number from GitHub API."""
    print(f"[resolve_context] Trying GitHub API to find PR for branch '{branch}' in repo '{repo_slug}'...")
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("[resolve_context][WARN] GITHUB_TOKEN not set. Cannot query GitHub API.")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
        }
    # Need owner for the query parameter
    owner = repo_slug.split('/')[0]
    # URL encode branch name just in case
    encoded_branch = requests.utils.quote(branch, safe='')
    url = f"https://api.github.com/repos/{repo_slug}/pulls?head={owner}:{encoded_branch}&state=open"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        pulls = response.json()
        if pulls and isinstance(pulls, list):
            pr_number = str(pulls[0]["number"])
            print(f"[resolve_context] Found PR #{pr_number} via GitHub API.")
            return pr_number
        else:
            print(f"[resolve_context] No open PR found for branch '{branch}' via GitHub API.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"[resolve_context][WARN] GitHub API call failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Response: {e.response.status_code} {e.response.text}")
        return None
    except Exception as e:
        print(f"[resolve_context][WARN] Error parsing GitHub API response: {e}")
        return None

def get_github_pr_number_via_gh_cli(branch: str) -> Optional[str]:
    """Fetches PR number using GitHub CLI ('gh')."""
    print(f"[resolve_context] Trying GitHub CLI ('gh') to find PR for branch '{branch}'...")
    # Check if gh is installed first?
    # stdout_check, stderr_check = _run_command(["gh", "--version"])
    # if stderr_check is not None: # gh command failed
    #      print("[resolve_context] 'gh' command not found or failed. Skipping CLI check.")
    #      return None

    # Construct command: gh pr list --head <branch> --limit 1 --json number --jq .[0].number
    command = ["gh", "pr", "list", "--head", branch, "--limit", "1", "--json", "number", "--jq", ".[0].number"]
    stdout, stderr = _run_command(command)

    if stderr is not None and "no pull requests found" not in stderr.lower():
         # Ignore "no pull requests found" stderr, but log others
         print(f"[resolve_context][WARN] 'gh pr list' command failed: {stderr}")
         return None

    if stdout:
        pr_number = stdout.strip()
        if pr_number.isdigit():
             print(f"[resolve_context] Found PR #{pr_number} via GitHub CLI.")
             return pr_number
        else:
             # Sometimes gh might output different text if parsing fails
             print(f"[resolve_context][WARN] GitHub CLI returned non-numeric output: {stdout}")
             return None
    else:
         print(f"[resolve_context] No open PR found for branch '{branch}' via GitHub CLI.")
         return None


def get_gitlab_mr_number(repo_slug: str, branch: str) -> Optional[str]:
    """Fetches MR IID from GitLab API."""
    print(f"[resolve_context] Trying GitLab API to find MR for branch '{branch}' in repo '{repo_slug}'...")
    token = os.getenv("GITLAB_TOKEN") or os.getenv("CI_JOB_TOKEN")
    if not token:
        print("[resolve_context][WARN] GITLAB_TOKEN or CI_JOB_TOKEN not set. Cannot query GitLab API.")
        return None

    headers = {"PRIVATE-TOKEN": token}
    # URL encode the repo slug (owner/repo or group/project)
    encoded_repo = requests.utils.quote(repo_slug, safe='')
    # URL encode the branch name
    encoded_branch = requests.utils.quote(branch, safe='')
    url = f"https://gitlab.com/api/v4/projects/{encoded_repo}/merge_requests?source_branch={encoded_branch}&state=opened"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        mrs = response.json()
        if mrs and isinstance(mrs, list):
            mr_iid = str(mrs[0]["iid"]) # Use 'iid' for GitLab
            print(f"[resolve_context] Found MR !{mr_iid} via GitLab API.")
            return mr_iid
        else:
            print(f"[resolve_context] No open MR found for branch '{branch}' via GitLab API.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"[resolve_context][WARN] GitLab API call failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Response: {e.response.status_code} {e.response.text}")
        return None
    except Exception as e:
        print(f"[resolve_context][WARN] Error parsing GitLab API response: {e}")
        return None

# --- Main Node Function ---

def resolve_context(state: dict) -> dict:
    """
    Resolves platform, repository, and PR/MR context.
    Uses CI environment variables first, then falls back to git/API/CLI calls locally.
    """
    print("[resolve_context] Resolving platform, repo, and PR/MR context...")
    # Work with state dict directly, use ensure_review_state internally if needed for Pydantic models
    # _state = ensure_review_state(state) # Can use this if accessing complex state attrs

    is_ci = state.get("is_ci_mode", False)
    platform = state.get("platform")
    repo = state.get("repo")
    pr_number = state.get("pr_number") # Get potentially pre-filled values

    # --- Determine Platform and Repo Slug (use Git remote as ground truth) ---
    remote_url = get_remote_url()
    detected_platform, detected_repo = detect_platform_and_repo(remote_url)

    if detected_platform and detected_repo:
        print(f"[resolve_context] Detected via Git: Platform='{detected_platform}', Repo='{detected_repo}'")
        # Overwrite state values if Git detection succeeded, as it's more reliable locally
        state['platform'] = detected_platform
        state['repo'] = detected_repo
        platform = detected_platform # Update local var too
        repo = detected_repo
    elif platform and repo:
        # Use values from init_state if Git detection failed but they exist
        print(f"[resolve_context] Using context from init_state: Platform='{platform}', Repo='{repo}'")
    else:
        print("[resolve_context][ERROR] Could not determine Platform or Repo Slug. Cannot fetch PR/MR number.")
        # Ensure keys exist even if unresolved
        state.setdefault('platform', 'unknown')
        state.setdefault('repo', None)
        state.setdefault('pr_number', None)
        return state # Cannot proceed without repo info

    # --- Determine PR/MR Number ---
    if pr_number:
        print(f"[resolve_context] Using PR/MR number from initial state (likely CI env var): {pr_number}")
    else:
        # Only attempt to fetch if not already set and we have repo info
        branch = get_current_branch()
        if branch and repo:
            print(f"[resolve_context] Current branch: '{branch}'. Attempting to find associated PR/MR...")
            if platform == "github":
                # Try gh CLI first locally, fallback to API
                if not is_ci:
                     pr_number = get_github_pr_number_via_gh_cli(branch)
                if not pr_number: # If gh failed or in CI
                     pr_number = get_github_pr_number_via_api(repo, branch)
            elif platform == "gitlab":
                # Try GitLab API (could add glab CLI support later if desired)
                pr_number = get_gitlab_mr_number(repo, branch)
            else:
                 print(f"[resolve_context] Cannot fetch PR/MR number for unknown platform '{platform}'")

            if pr_number:
                 state['pr_number'] = pr_number
            else:
                 print(f"[resolve_context] Could not automatically determine PR/MR number for branch '{branch}'.")
                 state['pr_number'] = None # Ensure it's None if not found
        else:
             print("[resolve_context] Cannot fetch PR/MR number without current branch or repo slug.")
             state['pr_number'] = None

    # Final log
    print(f"[resolve_context] Final Context: Platform='{state.get('platform')}', Repo='{state.get('repo')}', PR/MR#='{state.get('pr_number', 'N/A')}'")

    # Return the updated state dictionary
    return state