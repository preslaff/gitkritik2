# platform/github.py

import os
import requests
from gitkritik2.core.models import Settings

GITHUB_API = "https://api.github.com"

def post_summary_comment_github(config: Settings, summary: str):
    """
    Posts a summary comment to the Conversation tab of a pull request.
    """
    print("[GitHub] Posting summary comment to Conversation tab")
    repo = config.repo
    pr_number = config.pr_number
    token = os.getenv("GITHUB_TOKEN")

    url = f"{GITHUB_API}/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    payload = {
        "body": summary
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        print("[GitHub]Summary comment posted")
    else:
        print(f"[GitHub]Failed to post summary: {response.status_code} {response.text}")

def post_inline_comment_github(config: Settings, comments: list[dict]):
    """
    Posts inline comments to the Files Changed tab.
    """
    print("[GitHub] Posting inline comments to Files Changed tab")
    repo = config.repo
    pr_number = config.pr_number
    token = os.getenv("GITHUB_TOKEN")

    url = f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    for comment in comments:
        payload = {
            "body": comment["body"],
            "path": comment["file"],
            "line": comment["line"],
            "side": "RIGHT"
        }

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            print(f"[GitHub]Comment posted on {comment['file']}:{comment['line']}")
        else:
            print(f"[GitHub]Failed to post inline comment: {response.status_code} {response.text}")


