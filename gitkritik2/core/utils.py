# core/utils.py
from gitkritik2.core.models import ReviewState

def ensure_review_state(state_data) -> ReviewState:
    """Ensures the input is a ReviewState object."""
    if isinstance(state_data, ReviewState):
        return state_data
    if isinstance(state_data, dict):
        # Ensure nested models are handled correctly if necessary
        # Pydantic should handle dict -> model conversion including nested ones
        try:
            return ReviewState(**state_data)
        except Exception as e:
            print(f"[ERROR] Failed to cast dict to ReviewState: {e}")
            print(f"State Dict: {state_data}")
            # Decide how to handle - raise error? return empty state?
            raise TypeError(f"Could not convert input dict to ReviewState: {e}") from e
    raise TypeError(f"Expected dict or ReviewState, got {type(state_data)}")

# Removed map_comments_to_diff_lines (superseded by structured parsing + filtering)
# Kept extract_diff_snippet if used elsewhere, otherwise remove
# import re
# def extract_diff_snippet(diff: str, target_line: int, context: int = 3) -> str:
#     ... (implementation if needed) ...