# nodes/agents/bug_agent.py

from gitkritik2.core.models import ReviewState, AgentResult, Comment
from gitkritik2.core.llm_interface import call_llm
from gitkritik2.core.utils import ensure_review_state

def bug_agent(state: ReviewState) -> ReviewState:
    print("[bug_agent] Reviewing files for potential bugs")
    all_comments = []
    state = ensure_review_state(state)
    for filename, context in state.file_contexts.items():
        if not context.after:
            continue

        system_prompt = (
            "You are a senior software engineer reviewing code for potential bugs, edge cases, and risky assumptions. "
            "Focus on things that might break in production or lead to incorrect behavior."
        )

        user_prompt = (
            f"Filename: {filename}\n\n"
            "Here is the full current version of the file:\n\n"
            "```python\n"
            f"{context.after}\n"
            "```\n\n"
            "Please identify any logic bugs, unhandled input cases, off-by-one errors, exceptions, or other risky patterns.\n"
            "Mention any assumptions the code makes that could break.\n\n"
            "Include line numbers and concise explanations for each issue."
        )

        common = {"filename": filename}
        response = call_llm(system_prompt, user_prompt, state, common)

        for line in response.strip().split("\n"):
            if line.strip() and ":" in line:
                try:
                    parts = line.split(":", 2)
                    line_num = int(parts[0])
                    message = parts[1].strip() + (":" + parts[2] if len(parts) > 2 else "")
                    all_comments.append(Comment(file=filename, line=line_num, message=message, agent="bug"))
                except Exception:
                    continue

    state.agent_results["bug"] = AgentResult(agent_name="bug", comments=all_comments)
    return state.model_dump()  # converts ReviewState → dict

