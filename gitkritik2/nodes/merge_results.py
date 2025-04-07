# nodes/merge_results.py

from gitkritik2.core.models import ReviewState, Comment
from gitkritik2.core.utils import ensure_review_state

def merge_results(state: dict) -> dict:
    print("[merge_results] Merging agent comments")
    state = ensure_review_state(state)
    merged: list[Comment] = []

    for agent_name, result in state.agent_results.items():
        if result and result.comments:
            merged.extend(result.comments)

    # Optional: de-duplicate or sort comments here
    # For now, we just flatten them into the main list
    state.inline_comments = merged

    #Debbuging the dict error
    
    return state.model_dump()



