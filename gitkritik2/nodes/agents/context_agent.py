# nodes/agents/context_agent.py
import re
from typing import List, Dict, Any, Optional

from gitkritik2.core.models import ReviewState, AgentResult, Comment, FileContext
from gitkritik2.core.llm_interface import get_llm
from gitkritik2.core.utils import ensure_review_state
from gitkritik2.core.tools import get_symbol_definition # Import your tool

from langchain_core.prompts import PromptTemplate
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain.schema import AgentAction, AgentFinish

# --- ReAct Agent Setup ---

# Define the specific ReAct prompt template using string concatenation
# to avoid any triple-quote issues with Markdown rendering.
REACT_CONTEXT_PROMPT_TEMPLATE = (
    "You are an AI assistant analyzing code changes to understand cross-file dependencies.\n"
    "Your goal is to identify symbols (functions, classes) used in the CHANGED code (lines starting with '+' in the diff)\n"
    "that are likely imported from OTHER files within the project. For each identified symbol,\n"
    "determine its likely source file path (relative to project root) based on 'import' statements in the full file content,\n"
    "and use the available tool to fetch its definition. Only fetch definitions for symbols defined within the project, not external libraries.\n\n"
    "Available Tools:\n"
    "{tool_description}\n\n"
    "Use the following format for your reasoning process:\n\n"
    "Thought: Identify a symbol used in the CHANGED code snippet (+ lines) that seems imported from another project file. Find its corresponding import statement in the full file content to determine the source file path (relative to project root). Decide if fetching its definition is necessary.\n"
    "Action: Use the '{tool_names}' tool.\n"
    "Action Input: {{\"file_path\": \"path/relative/to/root/of/definition.py\", \"symbol_name\": \"symbol_to_lookup\"}}\n"
    "Observation: [Result from the get_symbol_definition tool will be inserted here]\n"
    "Thought: I now have the definition/context for the symbol. How does this inform the review of the changed code snippet? Do I need to look up another symbol from the changed code? Or am I done gathering context for this file?\n"
    "... (repeat Thought/Action/Action Input/Observation loop N times for relevant symbols)\n\n"
    "Thought: I have finished gathering context for all relevant imported symbols used in the changed lines of this file.\n"
    "Final Answer: Successfully gathered context.\n"
    "Definitions Fetched:\n"
    "[symbol_name_1]: Result from tool (definition or error message)\n"
    "[symbol_name_2]: Result from tool (definition or error message)\n"
    "... (List ALL symbols looked up and their corresponding full Observation result)\n"
    '[If no symbols were looked up, state "No symbols looked up."]\n\n'
    "Begin!\n\n"
    "Current file being reviewed: {filename}\n\n"
    "Changed code snippet (Diff - Focus on '+' lines):\n"
    "```diff\n"
    "{diff}\n"
    "```\n\n"
    "Full file content (for finding imports and original context):\n"
    "```\n"
    "{file_content}\n"
    "```\n\n"
    "Thought:{agent_scratchpad}"
)


react_prompt = PromptTemplate.from_template(REACT_CONTEXT_PROMPT_TEMPLATE)
tools: List[BaseTool] = [get_symbol_definition]

def _parse_final_answer_for_definitions(final_answer: str) -> Dict[str, str]:
    """Parses the 'Definitions Fetched:' section of the agent's final answer."""
    definitions = {}
    definitions_section_marker = "Definitions Fetched:"
    if definitions_section_marker not in final_answer:
        print("[_parse_final_answer] Warning: 'Definitions Fetched:' marker not found in Final Answer.")
        return definitions # Marker not found

    content_after_marker = final_answer.split(definitions_section_marker, 1)[1]

    # Regex to capture lines like '[symbol]: Definition content...' potentially spanning multiple lines
    # It captures the symbol name (allowing brackets) and the first line of its definition.
    # Subsequent lines are appended until a new symbol pattern is found.
    # Making the initial space optional after the colon
    pattern = re.compile(r"^\s*\[?([\w_.-]+)\]?:\s?(.*)")
    current_symbol = None
    current_definition_lines = []

    for line in content_after_marker.strip().split('\n'):
        match = pattern.match(line)
        if match:
            # Store the previous definition if we were tracking one
            if current_symbol:
                 definitions[current_symbol] = "\n".join(current_definition_lines).strip()

            # Start tracking the new symbol
            current_symbol = match.group(1)
            current_definition_lines = [match.group(2)] # Start with the first line of content
        elif current_symbol:
            # Append to the current definition if it's a continuation line
             current_definition_lines.append(line)
        # else: line is before the first symbol or formatting noise, ignore

    # Store the last definition found
    if current_symbol:
        definitions[current_symbol] = "\n".join(current_definition_lines).strip()

    # Handle the case where no symbols were explicitly listed
    if "No symbols looked up." in content_after_marker and not definitions:
         print("[_parse_final_answer] Agent indicated no symbols were looked up.")
         pass # Correctly parsed as empty

    if not definitions and definitions_section_marker in final_answer and "No symbols looked up." not in content_after_marker:
         print("[_parse_final_answer] Warning: 'Definitions Fetched:' marker found, but no definitions parsed.")

    return definitions


def context_agent(state: dict) -> dict:
    """
    LangGraph node using a ReAct agent to gather cross-file context
    by parsing the agent's final answer.
    """
    print("[context_agent] Gathering cross-file context using ReAct")
    _state = ensure_review_state(state)
    llm = get_llm(_state)

    if not llm:
        print("[context_agent] LLM not available, skipping context gathering.")
        if "agent_results" not in state: state["agent_results"] = {}
        state["agent_results"]["context"] = AgentResult(
            agent_name="context", comments=[],
            reasoning="Context gathering skipped: LLM not available"
        ).model_dump()
        return state

    # Create the ReAct agent components
    try:
        # Ensure LLM is compatible with ReAct agents (most Chat models are)
        react_agent = create_react_agent(llm, tools, react_prompt)
        agent_executor = AgentExecutor(
            agent=react_agent,
            tools=tools,
            verbose=True, # Essential for debugging ReAct steps
            handle_parsing_errors="Agent Error: Could not parse LLM output. Please check format and try again.",
            max_iterations=6, # Limit loops to prevent runaways
            # return_intermediate_steps=False # Keep False unless parsing Final Answer fails
        )
    except Exception as e:
        print(f"[context_agent] Error creating ReAct agent/executor: {e}")
        if "agent_results" not in state: state["agent_results"] = {}
        state["agent_results"]["context"] = AgentResult(
            agent_name="context", comments=[],
            reasoning=f"Context gathering skipped: Agent creation failed: {e}"
        ).model_dump()
        return state

    # Store collected definitions here before updating state
    collected_definitions_per_file: Dict[str, Dict[str, str]] = {}

    for filename, context in _state.file_contexts.items():
        # Skip if essential context is missing or no changes
        # Ensure diff has content beyond just header lines
        has_changes = context.diff and any(
             line.startswith(('-', '+')) and not (line.startswith('---') or line.startswith('+++'))
             for line in context.diff.splitlines()
        )
        if not context.after or not context.diff or not has_changes:
            print(f"[context_agent] Skipping {filename} - missing content, diff, or no substantive changes.")
            continue

        print(f"[context_agent] Processing {filename} for context...")

        try:
            # Invoke the ReAct agent executor
            response = agent_executor.invoke({
                "filename": filename,
                "diff": context.diff,
                "file_content": context.after,
                "tool_description": "\n".join([f"{t.name}: {t.description}" for t in tools]),
                "tool_names": ", ".join([t.name for t in tools]),
                # agent_scratchpad handled internally
            })

            final_answer = response.get("output", "")
            print(f"[context_agent] ReAct Final Answer for {filename}: {final_answer}")

            # Attempt to parse definitions from the final answer
            parsed_definitions = _parse_final_answer_for_definitions(final_answer)
            collected_definitions_per_file[filename] = parsed_definitions
            print(f"[context_agent] Parsed definitions for {filename}: {list(parsed_definitions.keys())}")

        except Exception as e:
            print(f"[context_agent] Error invoking ReAct agent for {filename}: {e}")
            collected_definitions_per_file[filename] = {"__agent_error__": f"Agent execution failed: {e}"}


    # --- Update State ---
    # Merge the collected symbol definitions back into the main state dictionary
    if "file_contexts" in state:
        for filename, definitions in collected_definitions_per_file.items():
             if filename in state["file_contexts"]:
                 # Assuming state nodes work with dicts as per StateGraph(dict)
                 if isinstance(state["file_contexts"][filename], dict):
                     # Only update if definitions were actually found or an error occurred
                     if definitions:
                          state["file_contexts"][filename]["symbol_definitions"] = definitions
                 else: # Defensive check
                      print(f"[WARN] ContextAgent: state['file_contexts'][{filename}] is not a dict, cannot update symbol_definitions.")

    # Update agent_results
    if "agent_results" not in state: state["agent_results"] = {}
    state["agent_results"]["context"] = AgentResult(
         agent_name="context",
         comments=[], # This agent primarily updates FileContext state
         reasoning="Completed context gathering attempt via ReAct."
    ).model_dump() # Store as dict

    return state