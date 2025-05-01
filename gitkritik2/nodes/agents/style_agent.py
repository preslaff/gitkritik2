# nodes/agents/style_agent.py
from typing import List, Dict
from gitkritik2.core.models import ReviewState, AgentResult, Comment, LLMReviewResponse, FileContext
from gitkritik2.core.llm_interface import get_llm
from gitkritik2.core.utils import ensure_review_state
from gitkritik2.core.diff_utils import filter_comments_to_diff

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import Runnable, RunnablePassthrough


def style_agent(state: ReviewState) -> ReviewState:
    print("[style_agent] Reviewing files for style issues")
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
            "You are an expert code reviewer focused on clean code style, naming, formatting, and structure. "
            "Focus **only** on the lines changed in the provided diff (lines starting with '+' or modified lines implied by the hunk context). "
            "Use the full file content for context only. "
            "Identify issues related to variable/function naming, layout, formatting, readability, duplication, or function length/cohesion *within the changes*. "
            "Provide specific suggestions where possible.\n"
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
            # Style agent usually doesn't need external symbol context
            # "Available Symbol Context (if any):\n"
            # "{symbol_context}\n\n"
            "Review the style of the changes shown in the diff ONLY, following the format instructions precisely.",
        ),
    ]
)

def style_agent(state: dict) -> dict:
    print("[style_agent] Reviewing files for style issues (LangChain refactor)")
    _state = ensure_review_state(state)
    llm = get_llm(_state)
    if not llm:
        print("[style_agent] LLM not available, skipping.")
        if "agent_results" not in state: state["agent_results"] = {}
        state["agent_results"]["style"] = AgentResult(agent_name="style", comments=[], reasoning="LLM not available").model_dump()
        return state

    chain = (
        RunnablePassthrough.assign(
            parsed_response = prompt_template | llm | parser
        )
    )

    all_comments: List[Comment] = []

    for filename, context in _state.file_contexts.items():
        if not context.after or not context.diff:
            print(f"[style_agent] Skipping {filename} - missing content or diff.")
            continue

        print(f"[style_agent] Processing {filename}...")
        try:
            result = chain.invoke(
                {
                    "filename": filename,
                    "diff": context.diff,
                    "file_content": context.after,
                    # "symbol_context": "N/A", # Not typically needed for style
                    "format_instructions": parser.get_format_instructions(),
                }
            )
            parsed_response: LLMReviewResponse = result['parsed_response']
            raw_comments = parsed_response.comments
            filtered_comments = filter_comments_to_diff(raw_comments, result['diff'], result['filename'], agent_name="style")
            all_comments.extend(filtered_comments)

        except Exception as e:
            print(f"[style_agent] Error processing {filename}: {e}")
            # all_comments.append(Comment(file=filename, line=0, message=f"Style Agent Error: {e}", agent="style"))

    if "agent_results" not in state: state["agent_results"] = {}
    state["agent_results"]["style"] = AgentResult(
        agent_name="style",
        comments=all_comments,
    ).model_dump()

    return state