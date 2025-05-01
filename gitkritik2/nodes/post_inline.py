# gitkritik2/nodes/post_inline.py

import os
from gitkritik2.core.models import ReviewState
from gitkritik2.core.utils import ensure_review_state

from gitkritik2.platform.github import post_inline_comment_github
from gitkritik2.platform.gitlab import post_inline_comment_gitlab

def post_inline(state: dict) -> dict:
    print("[post_inline] Posting inline comments")
    state = ensure_review_state(state)

    if os.getenv("GITKRITIK_DRY_RUN") == "true":
        print("[post_inline] Skipping — dry run mode")
        return state

    inline_enabled = os.getenv("GITKRITIK_INLINE", "false").lower() == "true"
    if not inline_enabled:
        print("[post_inline] Skipping — inline comments not enabled (--inline not passed)")
        return state

    platform = state.platform
    comments = state.inline_comments

    if not comments:
        print("[post_inline] No comments to post")
        return state

    if platform == "github":
        post_inline_comment_github(state, comments)
    elif platform == "gitlab":
        post_inline_comment_gitlab(state, comments)
    else:
        print(f"[post_inline] Unsupported platform: {platform}")

    return state.model_dump()
