# nodes/merge_results.py
from typing import List, Dict, Any
from gitkritik2.core.models import Comment # Use Comment model for type hints

def merge_results(state: dict) -> dict:
    """
    Merges comments from state['agent_results'] into state['inline_comments'].
    Performs sorting and optional deduplication.
    """
    print("[merge_results] Merging agent comments")
    merged_comments_data: List[Dict[str, Any]] = [] # Store as list of dicts

    agent_results_dict: Dict[str, dict] = state.get("agent_results", {})
    if not agent_results_dict:
        print("[merge_results] No agent results found to merge.")
        state["inline_comments"] = []
        return state

    for agent_name, result_dict in agent_results_dict.items():
        # Ensure result_dict is a dict and has 'comments' key
        if isinstance(result_dict, dict) and "comments" in result_dict:
            comments_list = result_dict.get("comments", [])
            if isinstance(comments_list, list):
                 # Assume comments are stored as dicts compatible with Comment model
                 for comment_data in comments_list:
                      if isinstance(comment_data, dict):
                           # Ensure agent field is populated if missing
                           comment_data.setdefault("agent", agent_name)
                           merged_comments_data.append(comment_data)
                      # Add handling if comments are stored as Pydantic objects
                      # elif isinstance(comment_data, Comment):
                      #      comment_dict = comment_data.model_dump()
                      #      comment_dict.setdefault("agent", agent_name)
                      #      merged_comments_data.append(comment_dict)
            else:
                 print(f"[WARN] 'comments' field for agent '{agent_name}' is not a list.")
        else:
            print(f"[WARN] Invalid or missing result structure for agent '{agent_name}'.")


    # Optional: sort by file and line number
    try:
        merged_comments_data.sort(key=lambda c: (c.get("file", ""), c.get("line", 0)))
    except Exception as e:
        print(f"[WARN] Could not sort comments: {e}")

    # Optional: de-duplicate based on file, line, and message body
    # Note: This might remove valid distinct comments if message is identical but agent/reasoning differs
    seen_keys = set()
    unique_comments = []
    for comment_data in merged_comments_data:
        # Create a key for deduplication - adjust if needed
        key = (
             comment_data.get("file"),
             comment_data.get("line"),
             comment_data.get("message", "").strip() # Dedupe based on core message
        )
        if key not in seen_keys:
            seen_keys.add(key)
            unique_comments.append(comment_data)

    print(f"[merge_results] Merged {len(unique_comments)} unique comments from {len(merged_comments_data)} total.")
    state["inline_comments"] = unique_comments # Store list of unique comment dicts
    return state