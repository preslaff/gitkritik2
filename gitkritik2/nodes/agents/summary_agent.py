# nodes/agents/summary_agent.py
from gitkritik2.core.models import ReviewState, AgentResult
from gitkritik2.core.llm_interface import get_llm
from gitkritik2.core.utils import ensure_review_state

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable

def summary_agent(state: ReviewState) -> ReviewState:
    print("[summary_agent] Generating high-level summary")
    state = ReviewState(**state)

# Define Prompt Template (outside function)
prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a senior AI reviewer summarizing a code change across multiple files based on the provided diffs. "
            "Your goal is to produce a clear, concise overview of the key changes, their purpose (if inferrable), "
            "any significant architectural shifts, major additions/removals, or potential high-level impacts. "
            "Keep the summary brief and suitable for a pull request comment."
        ),
        (
            "human",
            "Please summarize the following code changes presented as diffs:\n\n"
            "```diff\n"
            "{diff_summary}\n" # Use the combined diff input
            "```\n\n"
            "Provide a concise, high-level summary."
        ),
    ]
)


def summary_agent(state: dict) -> dict:
    print("[summary_agent] Generating high-level summary (LangChain refactor)")
    _state = ensure_review_state(state)
    llm = get_llm(_state)
    if not llm:
        print("[summary_agent] LLM not available, skipping summary.")
        state["summary_review"] = "Summary generation skipped: LLM not available."
        if "agent_results" not in state: state["agent_results"] = {}
        state["agent_results"]["summary"] = AgentResult(agent_name="summary", comments=[], reasoning=state["summary_review"]).model_dump()
        return state

    # Prepare combined diff input
    summary_input = ""
    if not _state.file_contexts:
        print("[summary_agent] No file contexts found to summarize.")
        summary_input = "No changes detected or context prepared."
    else:
        for filename, context in _state.file_contexts.items():
            summary_input += f"\n--- Diff for {filename} ---\n"
            # Prioritize the actual diff chunk if available
            diff_content = context.diff if context.diff else f"No diff content for {filename}."
            # Limit length per file to avoid excessive input
            max_len = 3000 # Adjust as needed
            summary_input += (diff_content[:max_len] + '... (truncated)' if len(diff_content) > max_len else diff_content) + "\n"

    # Define Chain
    chain: Runnable = prompt_template | llm | StrOutputParser()

    summary_text = "[ERROR] Summary generation failed."
    try:
        print("[summary_agent] Invoking LLM for summary...")
        summary_text = chain.invoke({"diff_summary": summary_input.strip()})
        print("[summary_agent] Summary received.")
    except Exception as e:
        print(f"[summary_agent] Error during summary generation: {e}")
        summary_text = f"[ERROR] Summary generation failed: {e}"

    # Update state dictionary
    state["summary_review"] = summary_text.strip()
    if "agent_results" not in state: state["agent_results"] = {}
    state["agent_results"]["summary"] = AgentResult(
        agent_name="summary",
        comments=[], # Summary agent doesn't produce inline comments
        reasoning=state["summary_review"] # Store summary as reasoning
    ).model_dump()

    return state