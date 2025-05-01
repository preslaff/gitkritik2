# nodes/format_output.py
from typing import List, Dict, Any
# from gitkritik2.core.models import Comment # Keep if needed for type hints

def format_output(state: dict) -> dict:
    print("[format_output] Formatting comments for platform posting")

    post_ready_comments_data: List[Dict[str, Any]] = []
    original_comments: List[dict] = state.get("inline_comments", [])

    if not original_comments:
        print("[format_output] No inline comments to format.")
        state["inline_comments"] = [] # Ensure it's set
    else:
        for comment_dict in original_comments:
            if not isinstance(comment_dict, dict):
                 print(f"[WARN] Skipping non-dict item in inline_comments: {comment_dict}")
                 continue

            # Get original fields needed by Comment model AND for formatting
            agent_name = comment_dict.get("agent", "AI")
            line_num = comment_dict.get("line") # Assume required
            original_message = comment_dict.get("message") # Assume required

            if line_num is None or original_message is None:
                 print(f"[WARN] Skipping comment missing line or message: {comment_dict}")
                 continue

            # Create the formatted body for platforms
            formatted_body = f"**[{agent_name.capitalize()}]** (Line {line_num}):\n{original_message}"

            # Create a new dict that STILL conforms to Comment, plus the formatted body
            output_comment = {
                "file": comment_dict.get("file"), # Required
                "line": line_num, # Required
                "message": original_message, # REQUIRED by Comment model
                "agent": agent_name, # Optional in Comment, but good to keep
                # Add the formatted body under a specific key for posting nodes
                "platform_body": formatted_body,
                # Pass through reasoning if it exists and is needed?
                # "reasoning": comment_dict.get("reasoning"),
            }
            post_ready_comments_data.append(output_comment)

        # Store the list containing dicts that are STILL valid Comment structures
        # but have the extra 'platform_body' key
        state["inline_comments"] = post_ready_comments_data

    # Ensure summary review exists (fallback generation) - This part seems okay
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
            if post_ready_comments_data:
                 fallback_summary = "AI review generated inline comments but no specific reasoning points."
            else:
                 fallback_summary = "AI review completed. No specific comments or summary points generated."

        state["summary_review"] = fallback_summary

    return state