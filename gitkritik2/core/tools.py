# core/tools.py
import os
import re
from langchain_core.tools import tool

# NOTE: Requires robust implementation (AST parsing, Jedi, LSP) for production use.
# This basic text search is fragile. Consider adding `pip install jedi`.

def _find_project_root(start_path: str) -> str:
    """Finds the git project root."""
    path = os.path.abspath(start_path)
    while True:
        if os.path.isdir(os.path.join(path, '.git')):
            return path
        parent = os.path.dirname(path)
        if parent == path: # Reached root directory
            return os.path.abspath('.') # Fallback to current dir
        path = parent

@tool
def get_symbol_definition(file_path: str, symbol_name: str) -> str:
    """
    Retrieves the definition (function/class signature, docstring, or relevant code snippet)
    for a given symbol_name within the specified project file_path.
    Use this when you need to understand what an imported function or class does.
    Provide the file path relative to the project root. Handles basic Python 'def' and 'class'.
    """
    print(f"Tool Call: get_symbol_definition(file_path='{file_path}', symbol_name='{symbol_name}')")
    try:
        project_root = _find_project_root('.')
        target_path = os.path.abspath(os.path.join(project_root, file_path))

        if not target_path.startswith(project_root) or '..' in file_path:
             return f"Error: Access denied. Attempted to read file outside project: {file_path}"

        if not os.path.exists(target_path):
            return f"Error: File not found at path: {file_path}"

        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.readlines() # Read lines for easier context grabbing

        definition_lines = []
        in_definition = False
        indent_level = -1
        # Basic heuristic - find 'def symbol_name(' or 'class symbol_name:' with flexible spacing
        pattern = rf"^(async\s+def|def|class)\s+{re.escape(symbol_name)}\s*[(:]" # Match start

        for i, line in enumerate(content):
            match = re.search(pattern, line.lstrip())
            if match:
                # Try to grab preceding comments/decorators too
                for j in range(max(0, i-5), i): # Look back up to 5 lines
                    stripped_line = content[j].strip()
                    if stripped_line.startswith('@') or stripped_line.startswith('#'):
                         definition_lines.append(content[j].rstrip())
                    elif stripped_line: # Stop if non-empty, non-comment/decorator found
                         definition_lines = [] # Reset if context isn't clean
                         break
                    # else allow empty lines before

                definition_lines.append(line.rstrip()) # Add the definition line itself
                in_definition = True
                indent_level = len(line) - len(line.lstrip(' '))

                # Grab subsequent lines based on indentation
                for k in range(i + 1, len(content)):
                    line_k = content[k]
                    # Skip empty lines immediately following definition line
                    if not line_k.strip() and len(definition_lines) == (i - max(0, i-5) + 1):
                        continue

                    current_indent = len(line_k) - len(line_k.lstrip(' '))

                    # Include lines that are indented more, or empty lines within the block
                    if line_k.strip() == "" or current_indent > indent_level:
                        definition_lines.append(line_k.rstrip())
                    # Include lines at the same indent level only if they seem part of a multiline string or construct
                    elif current_indent == indent_level and (line_k.strip().startswith(('"""', "'''")) or definition_lines[-1].strip().endswith(('\\', '(', '{', '['))):
                        definition_lines.append(line_k.rstrip())
                    else:
                        break # Dedented or same level non-empty line ends definition block
                break # Found first match

        if definition_lines:
             # Limit snippet size
             max_lines = 30
             snippet = "\n".join(definition_lines[:max_lines])
             if len(definition_lines) > max_lines:
                 snippet += "\n# ... (definition truncated)"
             return f"Definition found for '{symbol_name}' in '{file_path}':\n```python\n{snippet}\n```"
        else:
             return f"Error: Could not find definition for '{symbol_name}' in '{file_path}' using basic search."

    except Exception as e:
        print(f"[ERROR] Tool get_symbol_definition failed: {e}")
        return f"Error reading or parsing file '{file_path}': {e}"