# core/diff_utils.py
import re
from typing import List, Set, Tuple
from gitkritik2.core.models import Comment

def parse_hunk_ranges(diff_text: str) -> List[Tuple[int, int]]:
    """
    Parses @@ hunk headers to get line ranges in the new file.
    Returns list of tuples: (new_start_line, num_lines_in_hunk_new_file).
    """
    hunk_ranges = []
    # Regex to capture the new file range (+start,count)
    hunk_header_pattern = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')
    for line in diff_text.splitlines():
        match = hunk_header_pattern.match(line)
        if match:
            start_line = int(match.group(1))
            count = int(match.group(2) or 1) # Default to 1 if count is omitted
            if count > 0: # Ignore hunks that only remove lines
                hunk_ranges.append((start_line, count))
    return hunk_ranges

def get_added_modified_line_numbers(diff_text: str) -> Set[int]:
    """
    Parses a diff text and returns a set of line numbers (relative to the new file)
    that were added ('+') or part of a modification context.
    """
    added_lines = set()
    current_new_line = 0
    # Regex to capture the new file start line from the hunk header
    hunk_header_pattern = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')

    for line in diff_text.splitlines():
        match = hunk_header_pattern.match(line)
        if match:
            # Reset line counter based on hunk header
            current_new_line = int(match.group(1)) -1 # Start counter before first line
            continue

        # Track line numbers only within hunks
        if current_new_line >= 0:
            if line.startswith('+'):
                current_new_line += 1
                added_lines.add(current_new_line)
            elif line.startswith(' '):
                current_new_line += 1
                # Optionally include context lines if needed: added_lines.add(current_new_line)
            elif line.startswith('-'):
                # Removed lines don't advance the new file line number
                pass

    return added_lines


def filter_comments_to_diff(
    comments: List[Comment],
    diff_text: str,
    filename: str, # For logging/context
    agent_name: str # For updating comment
) -> List[Comment]:
    """
    Filters comments to keep only those landing on lines added or modified in the diff.
    Uses precise line number tracking based on '+' lines.
    """
    if not diff_text:
        print(f"[filter_comments_to_diff] Warning: Diff text missing for {filename}, cannot filter comments.")
        for c in comments: c.agent = agent_name # Still assign agent
        return comments # Return all if no diff info

    try:
        # Get the exact set of line numbers that were added/modified
        changed_line_numbers = get_added_modified_line_numbers(diff_text)
        if not changed_line_numbers:
            # This can happen if the diff only contains removals or metadata changes
            print(f"[filter_comments_to_diff] No added/modified lines found in diff for {filename}.")
            return []
    except Exception as e:
        print(f"[filter_comments_to_diff] Error parsing diff for changed lines ({filename}): {e}")
        return [] # Safer to return no comments if diff parsing fails

    filtered_comments = []
    for comment in comments:
        comment.agent = agent_name # Assign agent name regardless
        if comment.line in changed_line_numbers:
            filtered_comments.append(comment)
        else:
             print(f"[filter_comments_to_diff] Discarding comment for {filename} line {comment.line} (not in added/modified lines: {changed_line_numbers}).")

    return filtered_comments