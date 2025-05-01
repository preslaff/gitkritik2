# core/diff_utils.py
import re
from typing import List, Set, Tuple, Dict, Optional
from gitkritik2.core.models import Comment # Keep for filter function signature

# Import unidiff
try:
    from unidiff import PatchSet
    UNIDIFF_AVAILABLE = True
except ImportError:
    UNIDIFF_AVAILABLE = False
    print("[WARN] `unidiff` library not installed. Diff parsing will be less accurate.")
    print("[WARN] Please run: poetry add unidiff")


def get_added_modified_line_numbers(diff_text: str) -> Set[int]:
    """
    Parses a diff text using unidiff and returns a set of line numbers
    (relative to the new file) that were added ('+').
    """
    print("\n--- Debugging get_added_modified_line_numbers (using unidiff) ---")
    added_lines = set()

    if not diff_text:
        print("  Input diff_text is empty.")
        print("--- Finished get_added_modified_line_numbers ---")
        return added_lines

    if not UNIDIFF_AVAILABLE:
        print("  `unidiff` library not available. Cannot parse accurately.")
        print("--- Finished get_added_modified_line_numbers ---")
        # Optionally fall back to regex here, or just return empty
        return added_lines

    try:
        # Parse the diff text into patches
        patch_set = PatchSet.from_string(diff_text)

        if not patch_set:
            print("  unidiff: PatchSet is empty (no diffs found).")
            print("--- Finished get_added_modified_line_numbers ---")
            return added_lines

        # Assuming the diff_text is for a single file, process the first one
        # If multi-file diffs are possible input here, loop through patch_set
        if len(patch_set) > 1:
            print(f"  [WARN] unidiff: Found multiple files ({len(patch_set)}) in diff input. Processing only the first.")

        patched_file = patch_set[0]
        print(f"  unidiff: Processing file: {patched_file.path}")

        for hunk in patched_file:
            print(f"    Hunk Header: {hunk.section_header}")
            for line in hunk:
                if line.is_added:
                    # target_line_no is the line number in the new file
                    if line.target_line_no is not None:
                        added_lines.add(line.target_line_no)
                        print(f"      Line Added (+): New Line# {line.target_line_no}. Added to set.")
                    else:
                        print(f"      [WARN] unidiff: Added line found without target_line_no: {line.value.rstrip()}")
                # elif line.is_removed:
                    # print(f"      Line Removed (-): Old Line# {line.source_line_no}") # Optional debug
                # elif line.is_context:
                    # print(f"      Line Context ( ): Old Line# {line.source_line_no}, New Line# {line.target_line_no}") # Optional debug

    except Exception as e:
        print(f"[ERROR] unidiff: Failed to parse diff text: {e}")
        # Return empty set on parsing error
        added_lines = set()

    print(f"--- Finished get_added_modified_line_numbers ---")
    print(f"  Final Set of Added Lines: {added_lines if added_lines else '{}'}\n")
    return added_lines


# Keep the filter function, it now uses the more accurate set from above
def filter_comments_to_diff(
    comments: List[Comment], # Expects list of Comment Pydantic objects now
    diff_text: str,
    filename: str,
    agent_name: str
) -> List[Comment]:
    """
    Filters comments to keep only those landing on lines added or modified in the diff.
    Relies on get_added_modified_line_numbers for accuracy.
    """
    if not diff_text:
        print(f"[filter_comments_to_diff] Warning: Diff text missing for {filename}, cannot filter comments.")
        for c in comments: c.agent = agent_name # Still assign agent
        return comments # Return all if no diff info

    changed_line_numbers = get_added_modified_line_numbers(diff_text)

    if not changed_line_numbers:
        print(f"[filter_comments_to_diff] No added/modified line numbers identified in diff for {filename}. Discarding all comments for this file.")
        return [] # Discard all comments if no target lines found

    filtered_comments = []
    for comment in comments:
        # Ensure comment object is valid and has necessary attributes
        if not isinstance(comment, Comment) or comment.line is None:
            print(f"[WARN] filter_comments_to_diff: Skipping invalid comment object: {comment}")
            continue

        comment.agent = agent_name # Assign agent name regardless
        if comment.line in changed_line_numbers:
            filtered_comments.append(comment)
        else:
             print(f"[filter_comments_to_diff] Discarding comment for {filename} line {comment.line} (not in added lines: {changed_line_numbers}).")

    return filtered_comments