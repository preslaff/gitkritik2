# cli/display.py

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from gitkritik2.core.models import ReviewState # Keep for type hint on input function
from collections import defaultdict
import difflib
import re

console = Console()
ELLIPSIS_CONTEXT = 2 # Number of context lines around comments when using ellipsis

# Color mapping for agents (customize as needed)
AGENT_COLORS = {
    "bug": "bold red",
    "style": "bold yellow",
    "design": "bold blue",
    "context": "bold cyan",
    "summary": "bold green",
    "default": "bold white",
}

def render_review_result(final_state: ReviewState, side_by_side: bool = False, show_inline: bool = False) -> None:
    """Renders the final review state to the console."""

    # Get merged comments from the state (now contains dicts with 'body' formatted for platform)
    # We need the original message structure for local display, so this assumes
    # format_output hasn't overwritten the original message/agent fields, OR
    # we get comments directly from agent_results before format_output runs.
    # Let's modify to pull from agent_results for cleaner display data.

    all_agent_comments = []
    for agent_name, result_data in final_state.agent_results.items():
         if isinstance(result_data, dict):
              comments_list = result_data.get("comments", [])
              if isinstance(comments_list, list):
                   for comment_data in comments_list:
                        # Create a temporary structure or ensure needed fields exist
                        if isinstance(comment_data, dict):
                             all_agent_comments.append({
                                  "file": comment_data.get("file"),
                                  "line": comment_data.get("line"),
                                  "message": comment_data.get("message", "*No message*"), # Original message
                                  "agent": comment_data.get("agent", agent_name) # Use agent from comment or result
                             })

    if show_inline and all_agent_comments:
         console.rule("[bold cyan]Inline Comments")
         # We need the diff chunks from file_contexts now
         file_contexts = final_state.file_contexts # Dict[str, FileContext]
         diff_chunk_map = {path: fc.diff for path, fc in file_contexts.items() if fc.diff}

         _render_inline_comments(all_agent_comments, diff_chunk_map, side_by_side)
    elif show_inline:
         console.print("[yellow]No inline comments generated.[/yellow]")


    if final_state.summary_review:
        console.rule("[bold green]Summary Review")
        # Render summary using Markdown
        console.print(Markdown(final_state.summary_review.strip()))
    else:
        console.print("[yellow]No summary review generated.[/yellow]")


def _render_inline_comments(comments: List[Dict], diff_chunk_map: Dict[str, str], side_by_side: bool):
    """Renders inline comments, grouping by file."""
    if not comments:
        return

    # Group comments by file
    grouped_comments = defaultdict(list)
    for comment_data in comments:
         # Store line number and the comment dict itself for access to agent/message
         if comment_data.get("file") and comment_data.get("line") is not None:
              grouped_comments[comment_data["file"]].append(
                   (comment_data["line"], comment_data)
              )

    for file_path, file_comments in sorted(grouped_comments.items()):
        console.rule(f"[bold default]{file_path}")
        diff_text = diff_chunk_map.get(file_path)

        if not diff_text:
             console.print(f"[yellow]No diff content found for {file_path}, cannot display inline comments accurately.[/yellow]")
             # Optionally print comments non-inline
             for line, comment_data in sorted(file_comments):
                  agent = comment_data.get("agent", "AI")
                  message = comment_data.get("message", "")
                  color = AGENT_COLORS.get(agent, AGENT_COLORS["default"])
                  console.print(f"  L{line} 💬 [{color}]{agent.capitalize()}:[/] [yellow]{message}[/]")
             continue

        # Sort comments by line number for processing
        file_comments.sort(key=lambda item: item[0])

        if side_by_side:
            # Placeholder: Side-by-side rendering needs significant work
            # to integrate comments cleanly within the rich Table.
            # Current implementation might be buggy.
            console.print("[yellow]Side-by-side view with comments is complex, showing unified view instead.[/yellow]")
            _render_unified_diff_with_comments(diff_text, file_comments)
            # _render_side_by_side_diff(diff_text, file_comments) # Call if implemented
        else:
            _render_unified_diff_with_comments(diff_text, file_comments)


def _render_unified_diff_with_comments(diff_text: str, comments: List[Tuple[int, dict]]):
    """Renders a unified diff with comments inserted below relevant lines."""
    lines = diff_text.splitlines()
    comment_map = defaultdict(list)
    for line_num, comment_data in comments:
        comment_map[line_num].append(comment_data)

    current_new_line = 0
    hunk_header_pattern = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')
    in_hunk = False

    for line in lines:
        # Handle Hunk Header
        match = hunk_header_pattern.match(line)
        if match:
            current_new_line = int(match.group(1)) - 1 # Start before first line
            console.print(Text(line, style="magenta"))
            in_hunk = True
            continue

        if not in_hunk: # Print lines before first hunk (e.g., diff --git header)
             console.print(Text(line, style="dim"))
             continue

        # Process lines within a hunk
        line_num_to_check = -1
        rendered_line = None
        style = "white" # Default for context lines

        if line.startswith('+') and not line.startswith('+++'):
            current_new_line += 1
            line_num_to_check = current_new_line
            style = "green"
            # Add space for alignment if needed, or handle in Text prefix
            rendered_line = Text(f"{current_new_line:>4} + {line[1:]}", style=style)
        elif line.startswith('-') and not line.startswith('---'):
            style = "red"
            rendered_line = Text(f"     - {line[1:]}", style=style)
            # Don't increment current_new_line
        elif line.startswith(' '):
            current_new_line += 1
            line_num_to_check = current_new_line # Comments can attach to context lines too
            rendered_line = Text(f"{current_new_line:>4}   {line[1:]}", style=style)
        else:
             # Handle other lines like \ No newline at end of file
             rendered_line = Text(f"       {line}", style="dim")


        # Print the code line
        if rendered_line:
             console.print(rendered_line)

        # Print comments associated with this new line number
        if line_num_to_check in comment_map:
            for comment_data in comment_map[line_num_to_check]:
                 agent = comment_data.get("agent", "AI")
                 message = comment_data.get("message", "")
                 color = AGENT_COLORS.get(agent, AGENT_COLORS["default"])
                 # Indent comments slightly
                 console.print(f"   💬 [{color}]{agent.capitalize()}:[/] [yellow]{message}[/]")


# Placeholder for side-by-side rendering - this is complex with rich tables
def _render_side_by_side_diff(diff_text: str, comments: List[Tuple[int, dict]]):
     console.print("[italic yellow]Side-by-side rendering not fully implemented.[/italic]")
     # Fallback to unified view for now
     _render_unified_diff_with_comments(diff_text, comments)