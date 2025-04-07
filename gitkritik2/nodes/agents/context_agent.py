# nodes/agents/context_agent.py

from gitkritik2.core.models import ReviewState, AgentResult, Comment
from gitkritik2.core.llm_interface import call_llm


def context_agent(state: ReviewState) -> ReviewState:
    print("[context_agent] Performing design-level review")
    all_comments = []
    state = ReviewState(**state)
    for filename, context in state.file_contexts.items():
        if not context.after:
            continue

        system_prompt = (
            "You are a senior software architect. Your task is to review code for architectural and design concerns, "
            "such as maintainability, cohesion, complexity, and adherence to clean code principles."
        )

        user_prompt = (
            f"Filename: {filename}\n\n"
            "Here is the current version of the file:\n\n"
            "```python\n"
            f"{context.after}\n"
            "```\n\n"
            "Please identify any issues such as:\n"
            "- Functions or classes doing too much (violating SRP)\n"
            "- Poor modularization or abstractions\n"
            "- Difficult-to-maintain patterns\n"
            "- Tight coupling or poor separation of concerns\n"
            "- Suggestions for improving the architecture\n\n"
            "Include line numbers and concise explanations for each finding."
        )

        common = {"filename": filename}
        response = call_llm(system_prompt, user_prompt, state, common)

        for line in response.strip().split("\n"):
            if line.strip() and ":" in line:
                try:
                    parts = line.split(":", 2)
                    line_num = int(parts[0])
                    message = parts[1].strip() + (":" + parts[2] if len(parts) > 2 else "")
                    all_comments.append(Comment(file=filename, line=line_num, message=message, agent="context"))
                except Exception:
                    continue

    state.agent_results["context"] = AgentResult(agent_name="context", comments=all_comments)
    return state.model_dump()

