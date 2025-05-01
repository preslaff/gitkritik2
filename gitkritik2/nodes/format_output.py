# nodes/format_output.py
from typing import List, Dict, Any
from gitkritik2.core.models import Comment # Use Comment model for type hints

def format_output(state: dict) -> dict:
    """
    Formats inline comments for platform posting (e.g., adding markdown).
    Also ensures a summary review exists.
    Operates on state['inline_comments'] containing comment dictionaries.
    """
    print("[format_output] Formatting comments for platform posting")

    formatted_comments_data: List[Dict[str, Any]] = []
    original_comments: List[dict] = state.get("inline_comments", [])

    if not original_comments:
        print("[format_output] No inline comments to format.")
        state["inline_comments"] = [] # Ensure it's set
    else:
        for comment_dict in original_comments:
            if not isinstance(comment_dict, dict):
                 print(f"[WARN] Skipping non-dict item in inline_comments: {comment_dict}")
                 continue

            # Create the formatted message body for platforms
            # Using Markdown emphasis for agent name
            agent_name = comment_dict.get("agent", "AI")
            line_num = comment_dict.get("line", "N/A")
            message = comment_dict.get("message", "*No message body*")

            # Basic formatting - adjust Markdown/prefix as needed for GitHub/GitLab
            formatted_body = f"**[{agent_name.capitalize()}]** (Line {line_num}):\n{message}"

            # Create a new dict for the formatted comment to avoid modifying original
            # Pass through essential fields needed by platform posting functions
            formatted_comment = {
                "file": comment_dict.get("file"),
                "line": comment_dict.get("line"),
                "body": formatted_body, # The formatted message for the platform
                # Include original message/agent if needed elsewhere, otherwise remove
                # "original_message": message,
                # "agent": agent_name,
            }
            formatted_comments_data.append(formatted_comment)

        state["inline_comments"] = formatted_comments_data # Replace with formatted ones

    # Ensure summary review exists (fallback generation)
    if not state.get("summary_review"):
        print("[format_output] Generating fallback summary review.")
        summary_lines = []
        agent_results_dict: Dict[str, dict] = state.get("agent_results", {})
        for agent_name, result_dict in agent_results_dict.items():
             # Ensure result_dict is valid and check for 'reasoning' if agents provide it
             if isinstance(result_dict, dict):
                  reasoning = result_dict.get("reasoning")
                  if reasoning and agent_name != "summary": # Don't include summary agent's own reasoning here
                       summary_lines.append(f"**{agent_name.capitalize()}**: {reasoning}")

        if summary_lines:
            fallback_summary = "### AI Code Review Notes\n\n" + "\n\n".join(summary_lines)
        else:
            # Check if there were any inline comments at all
            if formatted_comments_data:
                 fallback_summary = "AI review generated inline comments but no specific reasoning points."
            else:
                 fallback_summary = "AI review completed. No specific comments or summary points generated."

        state["summary_review"] = fallback_summary

    return state