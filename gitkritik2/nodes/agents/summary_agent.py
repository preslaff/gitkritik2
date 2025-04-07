# nodes/agents/summary_agent.py

from gitkritik2.core.models import ReviewState, AgentResult
from gitkritik2.core.llm_interface import call_llm
from gitkritik2.core.utils import ensure_review_state

def summary_agent(state: ReviewState) -> ReviewState:
    print("[summary_agent] Generating high-level summary")
    state = ensure_review_state(state)

    # Merge all file contexts into a single summary input
    summary_input = ""
    for filename, context in state.file_contexts.items():
        summary_input += f"\n--- {filename} ---\n"
        summary_input += context.diff or context.after[:2000]  # fallback if diff is missing

    system_prompt = (
        "You are a senior AI reviewer summarizing a code change across multiple files. "
        "Your goal is to produce a clear, concise overview of what was changed, why it matters, "
        "and any general observations worth highlighting in the pull request."
    )

    user_prompt = (
        "Here are the diffs and file changes for this commit or pull request:\n\n"
        "```\n"
        f"{summary_input.strip()}\n"
        "```\n\n"
        "Please summarize the key changes in natural language. Highlight any notable improvements, "
        "complex refactors, or design shifts."
    )

    common = {"context": "multi-file diff summary"}
    response = call_llm(system_prompt, user_prompt, state, common)

    state.summary_review = response.strip()
    state.agent_results["summary"] = AgentResult(agent_name="summary", comments=[], reasoning=state.summary_review)

    return state.model_dump()

