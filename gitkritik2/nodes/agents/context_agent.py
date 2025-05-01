# nodes/agents/context_agent.py
import re
from typing import List, Dict, Any, Optional

from gitkritik2.core.models import ReviewState, AgentResult, Comment, FileContext
from gitkritik2.core.llm_interface import get_llm
from gitkritik2.core.utils import ensure_review_state
from gitkritik2.core.tools import get_symbol_definition # Import your tool

from langchain_core.prompts import PromptTemplate # Use basic PromptTemplate for ReAct
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain.schema import AgentAction, AgentFinish

 # --- ReAct Agent Setup ---

# Revised prompt template with clearer Action Input instructions
REACT_CONTEXT_PROMPT_TEMPLATE = (
    "You are an AI assistant analyzing code changes to understand cross-file dependencies.\n"
    "Your goal is to identify symbols (functions, classes) used in the CHANGED code (lines starting with '+' in the diff)\n"
    "that are likely imported from OTHER files within the project. For each identified symbol,\n"
    "determine its likely source file path (relative to project root) based on 'import' statements in the full file content,\n"
    "and use the available tool to fetch its definition. Only fetch definitions for symbols defined within the project, not external libraries.\n\n"
    "Available Tools:\n"
    "{tools}\n\n" # Formatted list of tools and descriptions provided by the framework
    "Use the following format for your reasoning process:\n\n"
    "Thought: [Your reasoning about identifying an imported symbol and its source file based on imports in the full content and usage in the diff +lines]\n"
    "Action: Use the '{tool_names}' tool.\n" # Tool name provided by the framework
    # --- Explicit Instruction for Action Input ---
    "Action Input: Provide the arguments as a valid JSON dictionary on a single line. The JSON dictionary MUST contain BOTH the key \"file_path\" (string, relative path from project root) and the key \"symbol_name\" (string, the exact symbol). Example: {{\"file_path\": \"src/utils/helpers.py\", \"symbol_name\": \"process_user_data\"}}\n"
    # --- End Explicit Instruction ---
    "Observation: [Result from the tool will be inserted here]\n"
    "Thought: [Your reasoning about the observation and whether more context is needed]\n"
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
    "Thought:{agent_scratchpad}" # Scratchpad provided by the framework
)


react_prompt = PromptTemplate.from_template(REACT_CONTEXT_PROMPT_TEMPLATE)
tools: List[BaseTool] = [get_symbol_definition]

def _parse_final_answer_for_definitions(final_answer: str) -> Dict[str, str]:
    """Parses the 'Definitions Fetched:' section of the agent's final answer."""
    definitions = {}
    definitions_section_marker = "Definitions Fetched:"
    if definitions_section_marker not in final_answer:
        print("[_parse_final_answer] Warning: 'Definitions Fetched:' marker not found in Final Answer.")
        return definitions

    content_after_marker = final_answer.split(definitions_section_marker, 1)[1]
    pattern = re.compile(r"^\s*\[?([\w_.-]+)\]?:\s?(.*)")
    current_symbol = None
    current_definition_lines = []

    for line in content_after_marker.strip().split('\n'):
        match = pattern.match(line)
        if match:
            if current_symbol:
                 definitions[current_symbol] = "\n".join(current_definition_lines).strip()
            current_symbol = match.group(1)
            current_definition_lines = [match.group(2)]
        elif current_symbol:
             current_definition_lines.append(line)

    if current_symbol:
        definitions[current_symbol] = "\n".join(current_definition_lines).strip()

    if "No symbols looked up." in content_after_marker and not definitions:
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
        # This uses the react_prompt which now includes {tools}
        react_agent = create_react_agent(llm, tools, react_prompt)
        agent_executor = AgentExecutor(
            agent=react_agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors="Agent Error: Could not parse LLM output. Please check format and try again.",
            max_iterations=6,
        )
    except Exception as e:
        print(f"[context_agent] Error creating ReAct agent/executor: {e}")
        # This error might still occur if other required variables are missing,
        # but the reported 'tools' variable should now be satisfied.
        if "agent_results" not in state: state["agent_results"] = {}
        state["agent_results"]["context"] = AgentResult(
            agent_name="context", comments=[],
            reasoning=f"Context gathering skipped: Agent creation failed: {e}"
        ).model_dump()
        return state

    # Store collected definitions here before updating state
    collected_definitions_per_file: Dict[str, Dict[str, str]] = {}

    for filename, context in _state.file_contexts.items():
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
            # The 'create_react_agent' setup should handle injecting 'tools' and 'tool_names'
            # into the underlying prompt when formatting.
            response = agent_executor.invoke({
                "filename": filename,
                "diff": context.diff,
                "file_content": context.after,
                # No need to manually pass tools/tool_names here if using create_react_agent
                # It gets them from the 'tools' list passed during creation.
            })

            final_answer = response.get("output", "")
            print(f"[context_agent] ReAct Final Answer for {filename}: {final_answer}")
            parsed_definitions = _parse_final_answer_for_definitions(final_answer)
            collected_definitions_per_file[filename] = parsed_definitions
            print(f"[context_agent] Parsed definitions for {filename}: {list(parsed_definitions.keys())}")

        except Exception as e:
            print(f"[context_agent] Error invoking ReAct agent for {filename}: {e}")
            collected_definitions_per_file[filename] = {"__agent_error__": f"Agent execution failed: {e}"}


    # --- Update State ---
    if "file_contexts" in state:
        for filename, definitions in collected_definitions_per_file.items():
             if filename in state["file_contexts"]:
                 if isinstance(state["file_contexts"][filename], dict):
                     if definitions:
                          state["file_contexts"][filename]["symbol_definitions"] = definitions
                 else:
                      print(f"[WARN] ContextAgent: state['file_contexts'][{filename}] is not a dict, cannot update symbol_definitions.")

    if "agent_results" not in state: state["agent_results"] = {}
    state["agent_results"]["context"] = AgentResult(
         agent_name="context",
         comments=[],
         reasoning="Completed context gathering attempt via ReAct."
    ).model_dump()

    return state