# nodes/agents/design_agent.py
# (Formerly context_agent.py)
from typing import List, Dict
from gitkritik2.core.models import ReviewState, AgentResult, Comment, LLMReviewResponse, FileContext
from gitkritik2.core.llm_interface import get_llm
from gitkritik2.core.utils import ensure_review_state
from gitkritik2.core.diff_utils import filter_comments_to_diff

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import Runnable, RunnablePassthrough

# 1. Define Parser & Prompt (outside function)
parser = PydanticOutputParser(pydantic_object=LLMReviewResponse)

prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a senior software architect reviewing code for architectural and design concerns. "
            "Focus **only** on the lines changed in the provided diff (lines starting with '+' or modified lines implied by the hunk context). "
            "Use the full file content and any provided symbol definitions for context only. "
            "Identify issues such as maintainability, cohesion, complexity, coupling, SRP violations, and adherence to clean code principles *within the changes*. "
            "Suggest improvements where applicable.\n"
            "Provide comments with accurate line numbers relative to the *new* file version.\n\n"
            "Format Instructions:\n{format_instructions}",
        ),
        (
            "human",
            "Filename: {filename}\n\n"
            "Relevant Diff:\n"
            "```diff\n"
            "{diff}\n"
            "```\n\n"
            "Full File Content (for context):\n"
            "```\n"
            "{file_content}\n"
            "```\n\n"
            "Available Symbol Context (if any):\n"
            "{symbol_context}\n\n"
            "Review the design and architecture implications of the changes shown in the diff ONLY, following the format instructions precisely.",
        ),
    ]
)

def design_agent(state: dict) -> dict:
    print("[design_agent] Reviewing files for design/architecture issues (LangChain refactor)")
    _state = ensure_review_state(state)
    llm = get_llm(_state)
    if not llm:
        print("[design_agent] LLM not available, skipping.")
        if "agent_results" not in state: state["agent_results"] = {}
        state["agent_results"]["design"] = AgentResult(agent_name="design", comments=[], reasoning="LLM not available").model_dump()
        return state

    chain = (
        RunnablePassthrough.assign(
            parsed_response = prompt_template | llm | parser
        )
    )

    all_comments: List[Comment] = []

    for filename, context in _state.file_contexts.items():
        if not context.after or not context.diff:
            print(f"[design_agent] Skipping {filename} - missing content or diff.")
            continue

        print(f"[design_agent] Processing {filename}...")
        symbol_context_str = "No external symbol context provided."
        if context.symbol_definitions:
            symbol_context_str = "\n".join([f"- {s}:\n```\n{d}\n```" for s, d in context.symbol_definitions.items()])

        try:
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
            filtered_comments = filter_comments_to_diff(raw_comments, result['diff'], result['filename'], agent_name="design")
            all_comments.extend(filtered_comments)

        except Exception as e:
            print(f"[design_agent] Error processing {filename}: {e}")
            # all_comments.append(Comment(file=filename, line=0, message=f"Design Agent Error: {e}", agent="design"))

    if "agent_results" not in state: state["agent_results"] = {}
    state["agent_results"]["design"] = AgentResult(
        agent_name="design",
        comments=all_comments,
    ).model_dump()

    return state