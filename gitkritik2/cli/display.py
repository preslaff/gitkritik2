from typing import List, Dict, Tuple # Ensure these are imported

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from rich.style import Style # Import Style
from gitkritik2.core.models import ReviewState # Keep for type hint
from collections import defaultdict
import difflib
import re

console = Console()
ELLIPSIS_CONTEXT = 2 # Number of context lines around comments when using ellipsis

# --- Define Styles Explicitly ---
ADDED_STYLE = Style(color="green")
REMOVED_STYLE = Style(color="red")
CONTEXT_STYLE = Style(color="white") # Or try "dim" for less emphasis: Style(dim=True)
HUNK_HEADER_STYLE = Style(color="magenta", bold=True)
COMMENT_MESSAGE_STYLE = Style(color="yellow")
DEFAULT_AGENT_STYLE = Style(bold=True, color="white")

# Define agent prefix styles more robustly
AGENT_PREFIX_STYLES = {
    "bug": Style(color="red", bold=True),
    "style": Style(color="yellow", bold=True),
    "design": Style(color="blue", bold=True),
    "context": Style(color="cyan", bold=True),
    "summary": Style(color="green", bold=True),
    # Add other agent names if needed
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
    """Renders a unified diff with comments inserted below relevant lines using explicit Styles."""
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
            current_new_line = int(match.group(1)) - 1
            console.print(Text(line, style=HUNK_HEADER_STYLE)) # Use defined style
            in_hunk = True
            continue

        if not in_hunk:
             console.print(Text(line, style=Style(dim=True))) # Dim header lines
             continue

        # Process lines within a hunk
        line_num_to_check = -1
        rendered_text: Optional[Text] = None # Use Optional from typing

        if line.startswith('+') and not line.startswith('+++'):
            current_new_line += 1
            line_num_to_check = current_new_line
            # Create Text object with line number and code, apply style
            rendered_text = Text.assemble(
                (f"{current_new_line:>4} + ", CONTEXT_STYLE), # Line number in default style
                (line[1:], ADDED_STYLE) # Added code in green
            )
        elif line.startswith('-') and not line.startswith('---'):
             # Create Text object, apply style
            rendered_text = Text.assemble(
                 ("     - ", CONTEXT_STYLE), # Padding
                 (line[1:], REMOVED_STYLE) # Removed code in red
            )
            # Don't increment current_new_line
        elif line.startswith(' '):
            current_new_line += 1
            line_num_to_check = current_new_line
            # Create Text object, apply style
            rendered_text = Text.assemble(
                (f"{current_new_line:>4}   ", CONTEXT_STYLE), # Line number and padding
                (line[1:], CONTEXT_STYLE) # Context code in default style
            )
        else:
             # Handle other lines like \ No newline at end of file
             rendered_text = Text(f"       {line}", style=Style(dim=True))

        # Print the code line
        if rendered_text:
             console.print(rendered_text)

        # Print comments associated with this new line number using Text.assemble
        if line_num_to_check in comment_map:
            for comment_data in comment_map[line_num_to_check]:
                 agent = comment_data.get("agent", "AI")
                 message = comment_data.get("message", "")
                 # Get the specific agent style, fallback to default
                 agent_style = AGENT_PREFIX_STYLES.get(agent, DEFAULT_AGENT_STYLE)

                 # Assemble the comment line using Text objects for better style control
                 comment_line = Text.assemble(
                     ("   💬 ", "default"), # Comment indicator
                     (f"[{agent.capitalize()}]:", agent_style), # Agent prefix with its style
                     (" ", "default"), # Space
                     (message, COMMENT_MESSAGE_STYLE) # Message in yellow
                 )
                 console.print(comment_line)

# Placeholder for side-by-side rendering - this is complex with rich tables
def _render_side_by_side_diff(diff_text: str, comments: List[Tuple[int, dict]]):
     console.print("[italic yellow]Side-by-side rendering not fully implemented.[/italic]")
     # Fallback to unified view for now
     _render_unified_diff_with_comments(diff_text, comments)