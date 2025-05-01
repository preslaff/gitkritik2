# nodes/post_inline.py
import os
from gitkritik2.core.models import ReviewState
from gitkritik2.core.utils import ensure_review_state
from gitkritik2.platform.github import post_inline_comment_github
from gitkritik2.platform.gitlab import post_inline_comment_gitlab


def post_inline(state: dict) -> dict:
    print("[post_inline] Posting inline comments")
    _state: ReviewState | None = None
    try:
        # Validate state structure FIRST
        _state = ensure_review_state(state)
    except Exception as e:
        print(f"[ERROR] post_inline received invalid state: {e}")
        return state  # Return original dict state on validation failure

    # Perform checks using the validated _state object
    if os.getenv("GITKRITIK_DRY_RUN") == "true":
        print("[post_inline] Skipping — dry run mode")
        return state

    inline_posting_enabled = os.getenv("GITKRITIK_INLINE") == "true"
    if not inline_posting_enabled:
        print("[post_inline] Skipping inline posting — not requested by GITKRITIK_INLINE env var")
        return state

    # Check the validated comments list (which includes 'platform_body')
    if not _state.inline_comments:
        print("[post_inline] No inline comments found in state to post")
        return state

    # Platform functions now take ReviewState and extract data internally
    if _state.platform == "github":
        post_inline_comment_github(_state)
    elif _state.platform == "gitlab":
        post_inline_comment_gitlab(_state)
    else:
        print(f"[post_inline] Unsupported platform for inline comments: {_state.platform}")

    return state  # Return original state dict

