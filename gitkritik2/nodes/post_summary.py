# gitkritik2/nodes/post_summary.py

import os
from gitkritik2.core.models import ReviewState
from gitkritik2.platform.github import post_summary_comment_github
from gitkritik2.platform.gitlab import post_summary_comment_gitlab
from gitkritik2.core.utils import ensure_review_state

def post_summary(state: dict) -> dict:
    print("[post_summary] Posting summary comment")
    state = ensure_review_state(state)

    if os.getenv("GITKRITIK_DRY_RUN") == "true":
        print("[post_summary] Skipping — dry run mode")
        return state

    summary = state.summary_review
    if not summary:
        print("[post_summary] No summary to post")
        return state

    platform = state.platform
    print(f"[post_summary] Platform detected: {platform}")

    if platform == "github":
        print("[GitHub] Posting summary comment to Conversation tab")
        post_summary_comment_github(state, summary)
    elif platform == "gitlab":
        print("[GitLab] Posting summary comment to Changes tab")
        post_summary_comment_gitlab(state, summary)
    else:
        print(f"[post_summary] Unsupported platform: {platform}")

    return state.model_dump()
