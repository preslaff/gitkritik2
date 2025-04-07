from gitkritik2.core.models import ReviewState

def ensure_review_state(state) -> ReviewState:
    if isinstance(state, ReviewState):
        return state
    return ReviewState(**state)


