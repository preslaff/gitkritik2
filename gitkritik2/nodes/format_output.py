# nodes/format_output.py

from gitkritik2.core.models import ReviewState
from gitkritik2.core.utils import ensure_review_state

def format_output(state: dict) -> dict:
    print("[format_output] Formatting comments for CI posting")
    state = ensure_review_state(state)
    all_comments = []

    for agent_name, result in state.agent_results.items():
        if result and result.comments:
            for comment in result.comments:
                body = f"*{agent_name}* comment on line {comment.line}:\n{comment.message}"
                if comment.reasoning:
                    body += f"\n\n{comment.reasoning}"

                all_comments.append({
                    "file": comment.file,
                    "line": comment.line,
                    "body": body
                })

    state.inline_comments = all_comments

    # Only generate summary_review if it's not already there
    if not state.summary_review:
        summary_lines = []
        for agent_result in state.agent_results.values():
            if agent_result.reasoning:
                summary_lines.append(f"🔍 {agent_result.reasoning}")
        state.summary_review = "### Summary of AI Code Review\n\n" + "\n\n".join(summary_lines)

    #Debbuging the dict error
    
    return state.model_dump()

