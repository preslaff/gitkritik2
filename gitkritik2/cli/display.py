# cli/display.py

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from gitkritik2.core.models import ReviewState
from collections import defaultdict
import difflib
import re

console = Console()
ELLIPSIS_CONTEXT = 2

def render_review_result(state: ReviewState, side_by_side: bool = False, show_ellipsis: bool = True) -> None:
    all_comments = []

    for agent_result in state.agent_results.values():
        all_comments.extend(agent_result.comments)

    _render_inline_comments(all_comments, state.context_chunks, side_by_side, show_ellipsis)

    if state.summary_review:
        console.rule("[bold green]Summary Review")
        console.print(Markdown(state.summary_review.strip()), highlight=False)

def _render_inline_comments(comments, chunks, side_by_side, show_ellipsis):
    if not comments:
        return

    grouped_comments = defaultdict(list)
    for comment in comments:
        body = comment.message
        if comment.reasoning:
            body += f"\n\n💡 {comment.reasoning}"
        grouped_comments[comment.file].append((comment.line, body))

    chunk_map = _index_chunks_by_path(chunks)

    for file_path, file_comments in grouped_comments.items():
        console.rule(f"[bold blue]{file_path}")
        diff_text = chunk_map.get(file_path)

        if diff_text and side_by_side:
            old_lines, new_lines = _extract_old_new_lines(diff_text)
            _render_side_by_side_diff(old_lines, new_lines, file_comments, show_ellipsis)
        elif diff_text:
            _render_numbered_new_file_with_comments(diff_text, file_comments, show_ellipsis)

def _render_numbered_new_file_with_comments(diff_text, comments, show_ellipsis):
    new_line_num = None
    comment_map = defaultdict(list)
    for line, msg in comments:
        comment_map[line].append(msg)

    lines = diff_text.splitlines()
    display_lines = []
    context_lines = set()
    comment_lines = set(comment_map.keys())

    real_new_line = 0

    for i, line in enumerate(lines):
        if line.startswith("@@"):
            match = re.search(r"\+([0-9]+)", line)
            if match:
                new_line_num = int(match.group(1)) - 1
            display_lines.append((None, Text(line, style="bold magenta")))
            continue

        if new_line_num is None:
            display_lines.append((None, Text(line)))
            continue

        is_new = line.startswith("+") and not line.startswith("+++")
        is_context = line.startswith(" ")
        is_removed = line.startswith("-") and not line.startswith("---")

        if is_new or is_context:
            new_line_num += 1
            real_new_line = new_line_num
            line_content = line[1:] if len(line) > 1 else ""
            style = "green" if is_new else "white"
            display_lines.append((real_new_line, Text(f"{real_new_line:>4} │ {line_content}", style=style)))
        elif is_removed:
            line_content = line[1:] if len(line) > 1 else ""
            display_lines.append((None, Text(f"     │ {line_content}", style="red")))
        else:
            display_lines.append((None, Text(line)))

    if show_ellipsis:
        to_keep = set()
        for cl in comment_lines:
            for offset in range(-ELLIPSIS_CONTEXT, ELLIPSIS_CONTEXT + 1):
                to_keep.add(cl + offset)

        for line_num, rendered in display_lines:
            if line_num is None or line_num in to_keep:
                console.print(rendered)
                if line_num in comment_map:
                    for comment in comment_map[line_num]:
                        console.print(f"   💬 [yellow]{comment}[/yellow]")
            elif line_num not in comment_lines:
                console.print("...")
    else:
        for line_num, rendered in display_lines:
            console.print(rendered)
            if line_num in comment_map:
                for comment in comment_map[line_num]:
                    console.print(f"   💬 [yellow]{comment}[/yellow]")

def _extract_old_new_lines(diff_text):
    old_lines = []
    new_lines = []
    for line in diff_text.splitlines():
        if line.startswith("-") and not line.startswith("---"):
            old_lines.append(line[1:])
        elif line.startswith("+") and not line.startswith("+++"):
            new_lines.append(line[1:])
        elif not line.startswith("@@"):
            old_lines.append(line[1:] if line.startswith(" ") else line)
            new_lines.append(line[1:] if line.startswith(" ") else line)
    return old_lines, new_lines

def _render_side_by_side_diff(old_lines, new_lines, comments, show_ellipsis):
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Old#", width=6)
    table.add_column("Old Code", overflow="fold")
    table.add_column("New#", width=6)
    table.add_column("New Code", overflow="fold")

    comment_map = defaultdict(list)
    for line, msg in comments:
        comment_map[line].append(msg)

    diff = list(difflib.ndiff(old_lines, new_lines))
    old_num = new_num = 1
    buffer = []

    def flush_buffer():
        for row in buffer:
            table.add_row(*row)
        buffer.clear()

    for line in diff:
        tag = line[0]
        code = line[2:]

        if tag == ' ':
            flush_buffer()
            table.add_row(str(old_num), code, str(new_num), code)
            old_num += 1
            new_num += 1
        elif tag == '-':
            buffer.append([str(old_num), Text(code, style="red"), "", ""])
            old_num += 1
        elif tag == '+':
            code_text = Text(code, style="green")
            if comment_map.get(new_num):
                code_text.append("\n")
                for c in comment_map[new_num]:
                    code_text.append(f"💬 {c}", style="yellow")
                    code_text.append("\n")
            buffer.append(["", "", str(new_num), code_text])
            new_num += 1

    flush_buffer()
    console.print(table)

def _index_chunks_by_path(chunks):
    result = {}
    for chunk in chunks:
        for line in chunk.splitlines():
            if line.startswith("diff --git"):
                parts = line.split(" b/")
                if len(parts) == 2:
                    result[parts[1].strip()] = chunk
                    break
    return result


