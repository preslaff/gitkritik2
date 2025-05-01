# graph/build_graph.py
import os
from langgraph.graph import StateGraph

# Core setup nodes
from gitkritik2.nodes.init_state import init_state
# --- Rename Import ---
from gitkritik2.nodes.resolve_context import resolve_context # <-- Renamed
# --- End Rename ---
from gitkritik2.nodes.detect_changes import detect_changes
from gitkritik2.nodes.prepare_context import prepare_context

# Agents (ensure imports match potentially renamed files)
from gitkritik2.nodes.agents.style_agent import style_agent
from gitkritik2.nodes.agents.bug_agent import bug_agent
from gitkritik2.nodes.agents.design_agent import design_agent # Assuming renamed
from gitkritik2.nodes.agents.context_agent import context_agent
from gitkritik2.nodes.agents.summary_agent import summary_agent

# Post-processing & IO
from gitkritik2.nodes.merge_results import merge_results
from gitkritik2.nodes.format_output import format_output
from gitkritik2.nodes.post_inline import post_inline
from gitkritik2.nodes.post_summary import post_summary

def build_review_graph() -> StateGraph:
    graph = StateGraph(dict)

    # Add all nodes
    graph.add_node("init_state", init_state)
    # --- Rename Node ---
    graph.add_node("resolve_context", resolve_context) # <-- Renamed
    # --- End Rename ---
    graph.add_node("detect_changes", detect_changes)
    graph.add_node("prepare_context", prepare_context)
    graph.add_node("context_agent", context_agent)
    graph.add_node("style_agent", style_agent)
    graph.add_node("bug_agent", bug_agent)
    graph.add_node("design_agent", design_agent)
    graph.add_node("summary_agent", summary_agent)
    graph.add_node("merge_results", merge_results)
    graph.add_node("format_output", format_output)
    graph.add_node("post_inline", post_inline)
    graph.add_node("post_summary", post_summary)

    # Define Edges (Control Flow)
    graph.set_entry_point("init_state")
    # Run context resolution right after initialization
    graph.add_edge("init_state", "resolve_context")
    # Continue the main flow from the resolved context
    graph.add_edge("resolve_context", "detect_changes")
    graph.add_edge("detect_changes", "prepare_context")
    graph.add_edge("prepare_context", "context_agent")
    graph.add_edge("context_agent", "bug_agent")
    graph.add_edge("bug_agent", "design_agent")
    graph.add_edge("design_agent", "style_agent")
    graph.add_edge("style_agent", "summary_agent")
    graph.add_edge("summary_agent", "merge_results")
    graph.add_edge("merge_results", "format_output")
    graph.add_edge("format_output", "post_inline")
    graph.add_edge("post_inline", "post_summary")

    # Set the final node
    graph.set_finish_point("post_summary")

    return graph