# nodes/agents/style_agent.py

from gitkritik2.core.models import ReviewState, AgentResult, Comment
from gitkritik2.core.llm_interface import call_llm
from gitkritik2.core.utils import ensure_review_state

def style_agent(state: ReviewState) -> ReviewState:
    print("[style_agent] Reviewing files for style issues")
    all_comments = []
    state = ReviewState(**state)
    for filename, context in state.file_contexts.items():
        if not context.after:
            continue

        system_prompt = (
            "You are an expert code reviewer focused on clean code, naming, and structure. "
            "Point out any style or structure issues in the following file."
        )

        user_prompt = (
            f"Filename: {filename}\n\n"
            "Here is the current version of the file:\n\n"
            "```python\n"
            f"{context.after}\n"
            "```\n\n"
            "Identify any issues related to:\n\n"
            "- Variable and function naming\n"
            "- Code layout and formatting\n"
            "- Function length or cohesion\n"
            "- Readability or duplication\n\n"
            "Please provide line numbers and specific suggestions."
        )

        common = {"filename": filename}
        response = call_llm(system_prompt, user_prompt, state, common)

        for line in response.strip().split("\n"):
            if line.strip() and ":" in line:
                try:
                    parts = line.split(":", 2)
                    line_num = int(parts[0])
                    message = parts[1].strip() + (":" + parts[2] if len(parts) > 2 else "")
                    all_comments.append(Comment(file=filename, line=line_num, message=message, agent="style"))
                except Exception:
                    continue

    state.agent_results["style"] = AgentResult(agent_name="style", comments=all_comments)
    return state.model_dump()

