# core/utils.py
from gitkritik2.core.models import ReviewState # Import the model itself
from pydantic import ValidationError # Import Pydantic's validation error

def ensure_review_state(state_data) -> ReviewState:
    """
    Ensures the input is a ReviewState object.
    If input is a dict, validates and converts it using Pydantic's
    model_validate method, which correctly handles defaults.
    """
    if isinstance(state_data, ReviewState):
        return state_data
    if isinstance(state_data, dict):
        try:
            # Use model_validate for robust dict -> model conversion
            return ReviewState.model_validate(state_data)
        except ValidationError as e:
            # Catch Pydantic's specific validation error for better debugging
            print(f"[ERROR] Pydantic validation failed casting dict to ReviewState:")
            # Print simplified errors or the full list
            print(e)
            # Optionally print the problematic dictionary
            # import json
            # print("Problematic State Dict:")
            # print(json.dumps(state_data, indent=2))
            # Re-raise as TypeError or a custom exception for LangGraph
            raise TypeError(f"Could not validate input dict as ReviewState: {e}") from e
        except Exception as e:
            # Catch other unexpected errors during validation
            print(f"[ERROR] Unexpected error casting dict to ReviewState: {e}")
            raise TypeError(f"Could not convert input dict to ReviewState: {e}") from e
    # If it's neither a dict nor a ReviewState, raise error
    raise TypeError(f"Input must be dict or ReviewState object, got {type(state_data)}")