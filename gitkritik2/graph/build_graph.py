# graph/build_graph.py

import os
from langgraph.graph import StateGraph
# from gitkritik2.core.models import ReviewState # Not needed directly if using dict state

# Core setup nodes
from gitkritik2.nodes.init_state import init_state
from gitkritik2.nodes.detect_ci_context import detect_ci_context
from gitkritik2.nodes.detect_changes import detect_changes
from gitkritik2.nodes.prepare_context import prepare_context

# Agents
from gitkritik2.nodes.agents.style_agent import style_agent
from gitkritik2.nodes.agents.bug_agent import bug_agent
from gitkritik2.nodes.agents.design_agent import design_agent # Renamed
from gitkritik2.nodes.agents.context_agent import context_agent # New ReAct agent
from gitkritik2.nodes.agents.summary_agent import summary_agent

# Post-processing & IO
from gitkritik2.nodes.merge_results import merge_results
from gitkritik2.nodes.format_output import format_output
from gitkritik2.nodes.post_inline import post_inline
from gitkritik2.nodes.post_summary import post_summary

def build_review_graph() -> StateGraph:
    # Use dict for state communication between nodes
    graph = StateGraph(dict)

    # Add all nodes
    graph.add_node("init_state", init_state)
    graph.add_node("detect_changes", detect_changes)
    graph.add_node("prepare_context", prepare_context)
    # ADD new context agent
    graph.add_node("context_agent", context_agent)
    graph.add_node("style_agent", style_agent)
    graph.add_node("bug_agent", bug_agent)
    graph.add_node("design_agent", design_agent) # Renamed
    graph.add_node("summary_agent", summary_agent)
    graph.add_node("merge_results", merge_results)
    graph.add_node("format_output", format_output)
    graph.add_node("post_inline", post_inline)
    graph.add_node("post_summary", post_summary)

    # Conditional CI detection node
    is_ci = os.getenv("GITKRITIK_CI_MODE") == "true"
    if is_ci:
        graph.add_node("detect_ci_context", detect_ci_context)

    # Define Edges (Control Flow)
    graph.set_entry_point("init_state")

    if is_ci:
        graph.add_edge("init_state", "detect_ci_context")
        graph.add_edge("detect_ci_context", "detect_changes")
    else:
        graph.add_edge("init_state", "detect_changes")

    # Main review pipeline
    graph.add_edge("detect_changes", "prepare_context")
    # Gather context *after* preparing files, *before* detailed review
    graph.add_edge("prepare_context", "context_agent")
    # Run detailed review agents after context gathering
    graph.add_edge("context_agent", "bug_agent") # Bug agent first, benefits most
    graph.add_edge("bug_agent", "design_agent") # Then design
    graph.add_edge("design_agent", "style_agent") # Style last among reviewers
    # Summarize after all reviews are done
    graph.add_edge("style_agent", "summary_agent")
    # Process and post results
    graph.add_edge("summary_agent", "merge_results")
    graph.add_edge("merge_results", "format_output")
    graph.add_edge("format_output", "post_inline")
    graph.add_edge("post_inline", "post_summary")

    # Set the final node
    graph.set_finish_point("post_summary")

    return graph