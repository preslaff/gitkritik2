# nodes/detect_ci_context.py

import os
import subprocess
import requests
from gitkritik2.core.models import ReviewState, Settings
from gitkritik2.core.utils import ensure_review_state

def get_remote_url() -> str:
    result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
    return result.stdout.strip()

def get_current_branch() -> str:
    result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
    return result.stdout.strip()

def detect_platform_and_repo(remote_url: str):
    if "github.com" in remote_url:
        platform = "github"
        repo_slug = remote_url.split("github.com/")[-1].replace(".git", "")
    elif "gitlab.com" in remote_url:
        platform = "gitlab"
        repo_slug = remote_url.split("gitlab.com/")[-1].replace(".git", "")
    else:
        platform = "unknown"
        repo_slug = ""
    return platform, repo_slug

def get_github_pr_number(repo: str, branch: str) -> str:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.github.com/repos/{repo}/pulls?head={repo.split('/')[0]}:{branch}"

    response = requests.get(url, headers=headers)
    if response.ok and response.json():
        return str(response.json()[0]["number"])
    return None

def get_gitlab_mr_number(repo: str, branch: str) -> str:
    token = os.getenv("GITLAB_TOKEN") or os.getenv("CI_JOB_TOKEN")
    headers = {"PRIVATE-TOKEN": token}
    encoded_repo = requests.utils.quote(repo, safe="")
    url = f"https://gitlab.com/api/v4/projects/{encoded_repo}/merge_requests?source_branch={branch}"

    response = requests.get(url, headers=headers)
    if response.ok and response.json():
        return str(response.json()[0]["iid"])
    return None

def detect_ci_context(state: dict) -> dict:
    print("[detect_ci_context] Detecting platform, repo, and PR/MR context...")
    state = ensure_review_state(state)
    remote_url = get_remote_url()
    branch = get_current_branch()
    platform, repo = detect_platform_and_repo(remote_url)

    pr_number = None
    if platform == "github":
        pr_number = get_github_pr_number(repo, branch)
    elif platform == "gitlab":
        pr_number = get_gitlab_mr_number(repo, branch)

    print(f"Platform: {platform}, Repo: {repo}, Branch: {branch}, PR/MR #: {pr_number or 'Not found'}")

    state.kritik_config = Settings(
        platform=platform,
        repo=repo,
        pr_number=pr_number,
        model=state.kritik_config.model if state.kritik_config else "gpt-4",
        strategy=state.kritik_config.strategy if state.kritik_config else "hybrid"
    )

    #Debbuging the dict error
    
    return state.model_dump()

