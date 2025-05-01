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

    if not state.inline_comments:
        print("[post_inline] No comments to post")
        return state

    if os.getenv("GITKRITIK_INLINE") != "true":
        print("[post_inline] Skipping inline posting — not requested by --inline")
        return state

    if state.platform == "github":
        print("[GitHub] Posting inline comments to Files changed tab")
        post_inline_comment_github(state)
    elif state.platform == "gitlab":
        print("[GitLab] Posting inline comments to Changes tab")
        post_inline_comment_gitlab(state)
    else:
        print(f"[post_inline] Unsupported platform: {state.platform}")

    return state.model_dump()