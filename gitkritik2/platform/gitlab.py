# platform/gitlab.py

import os
import requests
from gitkritik2.core.models import Settings

GITLAB_API = "https://gitlab.com/api/v4"

def post_summary_comment_gitlab(config: Settings, summary: str):
    """
    Posts a general summary comment to the GitLab MR (Overview tab).
    """
    print("[GitLab] Posting summary comment to Overview tab")
    token = os.getenv("GITLAB_TOKEN") or os.getenv("CI_JOB_TOKEN")
    headers = {
        "PRIVATE-TOKEN": token,
        "Content-Type": "application/json"
    }

    url = f"{GITLAB_API}/projects/{requests.utils.quote(config.repo, safe='')}/merge_requests/{config.pr_number}/notes"
    payload = {"body": summary}

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        print("[GitLab] Summary comment posted")
    else:
        print(f"[GitLab] Failed to post summary: {response.status_code} {response.text}")

def post_inline_comment_gitlab(config: Settings, comments: list[dict]):
    """
    Posts inline comments to the Changes tab using discussions.
    Each comment gets its own discussion.
    """
    print("[GitLab] Posting inline comments to Changes tab")
    token = os.getenv("GITLAB_TOKEN") or os.getenv("CI_JOB_TOKEN")
    headers = {
        "PRIVATE-TOKEN": token,
        "Content-Type": "application/json"
    }

    for comment in comments:
        payload = {
            "body": comment["body"],
            "position": {
                "position_type": "text",
                "new_path": comment["file"],
                "new_line": comment["line"]
            }
        }

        url = f"{GITLAB_API}/projects/{requests.utils.quote(config.repo, safe='')}/merge_requests/{config.pr_number}/discussions"
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 201:
            print(f"[GitLab] Inline comment posted on {comment['file']}:{comment['line']}")
        else:
            print(f"[GitLab] Failed to post inline comment: {response.status_code} {response.text}")


