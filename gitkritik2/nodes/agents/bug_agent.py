# nodes/agents/bug_agent.py
from typing import List, Dict
from gitkritik2.core.models import ReviewState, AgentResult, Comment, LLMReviewResponse, FileContext
from gitkritik2.core.llm_interface import get_llm
from gitkritik2.core.utils import ensure_review_state
from gitkritik2.core.diff_utils import filter_comments_to_diff

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import Runnable, RunnablePassthrough

def bug_agent(state: ReviewState) -> ReviewState:
    print("[bug_agent] Reviewing files for potential bugs")
    all_comments = []
    state = ReviewState(**state)
    for filename, context in state.file_contexts.items():
        if not context.after:
            continue

# 1. Define Parser & Prompt (outside function)
parser = PydanticOutputParser(pydantic_object=LLMReviewResponse)

prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a senior software engineer reviewing code for potential bugs, edge cases, and risky assumptions. "
            "Focus **only** on the lines changed in the provided diff (lines starting with '+' or modified lines implied by the hunk context). "
            "Use the full file content and any provided symbol definitions for context only. "
            "Identify logic bugs, unhandled cases, errors, exceptions, or risky patterns *within the changes*. "
            "Mention any assumptions the *changed code* makes that could break.\n"
            "Provide comments with accurate line numbers relative to the *new* file version.\n\n"
            "Format Instructions:\n{format_instructions}", # Add format instructions from parser
        ),
        (
            "human",
            "Filename: {filename}\n\n"
            "Relevant Diff:\n"
            "```diff\n"
            "{diff}\n"
            "```\n\n"
            "Full File Content (for context):\n"
            "```\n" # Consider adding language hint, e.g. ```python
            "{file_content}\n"
            "```\n\n"
            "Available Symbol Context (if any):\n"
            "{symbol_context}\n\n"
            "Review the changes shown in the diff and provide your findings ONLY for those changed lines, following the format instructions precisely.",
        ),
    ]
)

def bug_agent(state: dict) -> dict:
    print("[bug_agent] Reviewing files for potential bugs (LangChain refactor)")
    _state = ensure_review_state(state)
    llm = get_llm(_state)
    if not llm:
        print("[bug_agent] LLM not available, skipping.")
        # Ensure agent_results exists even if skipping
        if "agent_results" not in state: state["agent_results"] = {}
        state["agent_results"]["bug"] = AgentResult(agent_name="bug", comments=[], reasoning="LLM not available").model_dump()
        return state

    # Define the LCEL Chain
    # Use RunnablePassthrough to pass filename and diff along for filtering
    chain = (
        RunnablePassthrough.assign(
            parsed_response = prompt_template | llm | parser
        )
    )

    all_comments: List[Comment] = []

    for filename, context in _state.file_contexts.items():
        if not context.after or not context.diff:
            print(f"[bug_agent] Skipping {filename} - missing content or diff.")
            continue

        print(f"[bug_agent] Processing {filename}...")
        symbol_context_str = "No external symbol context provided."
        if context.symbol_definitions:
            symbol_context_str = "\n".join([f"- {s}:\n```\n{d}\n```" for s, d in context.symbol_definitions.items()])

        try:
            # Invoke the Chain
            # Input dict keys must match template variables AND passthrough keys
            result = chain.invoke(
                {
                    "filename": filename,
                    "diff": context.diff,
                    "file_content": context.after,
                    "symbol_context": symbol_context_str,
                    "format_instructions": parser.get_format_instructions(),
                }
            )

            parsed_response: LLMReviewResponse = result['parsed_response']
            raw_comments = parsed_response.comments

            # Filter Comments to actual diff lines using the passed 'diff'
            filtered_comments = filter_comments_to_diff(raw_comments, result['diff'], result['filename'], agent_name="bug")
            all_comments.extend(filtered_comments)

        except Exception as e:
            print(f"[bug_agent] Error processing {filename}: {e}")
            # Consider adding an error comment
            # all_comments.append(Comment(file=filename, line=0, message=f"Bug Agent Error: {e}", agent="bug"))


    # Update the state dictionary directly before returning
    if "agent_results" not in state: state["agent_results"] = {}
    state["agent_results"]["bug"] = AgentResult(
        agent_name="bug",
        comments=all_comments,
    ).model_dump() # Store as dict in state

    return state