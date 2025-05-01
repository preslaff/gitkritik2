# nodes/post_summary.py
import os
# Ensure ReviewState is imported if you need type hints
from gitkritik2.core.models import ReviewState
from gitkritik2.platform.github import post_summary_comment_github
from gitkritik2.platform.gitlab import post_summary_comment_gitlab
from gitkritik2.core.utils import ensure_review_state

def post_summary(state: dict) -> dict:
    print("[post_summary] Posting summary comment")
    _state: ReviewState | None = None
    try:
        # Validate state structure FIRST
        _state = ensure_review_state(state)
    except Exception as e:
        print(f"[ERROR] post_summary received invalid state: {e}")
        return state # Return original dict state on validation failure

    # Perform checks using the validated _state object
    if os.getenv("GITKRITIK_DRY_RUN") == "true":
        print("[post_summary] Skipping — dry run mode")
        return state

    # Check the validated summary field
    summary = _state.summary_review # Extract summary from state
    if not summary:
        print("[post_summary] No summary review content found in state to post")
        return state

    platform = _state.platform # Extract platform from state
    print(f"[post_summary] Platform detected: {platform}")

    if platform == "github":
        print("[GitHub] Posting summary comment to Conversation tab")
        # Call with ONLY the state object
        post_summary_comment_github(_state) # <-- FIX: Remove 'summary' argument
    elif platform == "gitlab":
        print("[GitLab] Posting summary comment to Changes tab")
         # Call with ONLY the state object
        post_summary_comment_gitlab(_state) # <-- FIX: Remove 'summary' argument
    else:
        print(f"[post_summary] Unsupported platform for summary comment: {platform}")

    return state # Return original state dict