# core/tools.py
import os
import re
from typing import Optional
from langchain_core.tools import tool
from langsmith import traceable # Keep if using LangSmith

try:
    import jedi
    JEDI_AVAILABLE = True
except ImportError:
    JEDI_AVAILABLE = False
    print("[WARN] `jedi` library not installed. Symbol definition lookup will be less accurate.")
    print("[WARN] Please run: poetry add jedi")


def _find_project_root(start_path: str) -> str:
    """Finds the git project root."""
    # (Keep this helper function as it was)
    path = os.path.abspath(start_path)
    while True:
        if os.path.isdir(os.path.join(path, '.git')):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return os.path.abspath('.')
        path = parent

def _format_jedi_definition(definition: "jedi.api.classes.BaseDefinition") -> str:
    """Formats the extracted Jedi definition into a readable string."""
    output_parts = []
    try:
        # Description often contains the signature
        signature = definition.description
        if signature:
            # Prepend def/class if not present in description (heuristic)
            line_code = definition.get_line_code().strip()
            if line_code.startswith(("def ", "async def ", "class ")) and not signature.startswith(("def ", "async def ", "class ")):
                 prefix = line_code.split(definition.name)[0]
                 signature = prefix + signature

            output_parts.append(f"Signature: `{signature}`")

        docstring = definition.docstring(raw=True).strip()
        if docstring:
            # Indent docstring for clarity
            indented_docstring = "\n".join([f"  {line}" for line in docstring.splitlines()])
            output_parts.append(f"Docstring:\n```\n{indented_docstring}\n```")

        if not output_parts:
             # Fallback to line code if no signature/docstring
             output_parts.append(f"Code: `{definition.get_line_code().strip()}`")

        return "\n".join(output_parts)

    except Exception as e:
        print(f"[WARN] Error formatting Jedi definition for {definition.name}: {e}")
        # Fallback if formatting fails
        return f"Code: `{definition.get_line_code().strip()}` (formatting error: {e})"


@tool
@traceable # Keep if using LangSmith
def get_symbol_definition(file_path: str, symbol_name: str) -> str:
    """
    Retrieves the definition (function/class signature, docstring) for a Python
    symbol_name within the specified project file_path using static analysis.
    Use this when you need to understand what an imported function or class does.
    Provide the file path relative to the project root.
    """
    print(f"Tool Call: get_symbol_definition(file_path='{file_path}', symbol_name='{symbol_name}')")

    if not JEDI_AVAILABLE:
        return "Error: `jedi` library is not installed. Cannot perform accurate symbol lookup."

    try:
        project_root = _find_project_root('.')
        target_path = os.path.abspath(os.path.join(project_root, file_path))

        # Basic security/validation checks
        if not target_path.startswith(project_root) or '..' in file_path:
             return f"Error: Access denied. Attempted to read file outside project root: {file_path}"
        if not os.path.exists(target_path) or not os.path.isfile(target_path):
            return f"Error: File not found or is not a file at resolved path: {target_path}"
        if not target_path.lower().endswith(".py"):
             return f"Error: Can only analyze Python (.py) files. Path: {file_path}"

        with open(target_path, 'r', encoding='utf-8') as f:
            file_content = f.read()

        # Use Jedi to find definitions
        script = jedi.Script(code=file_content, path=target_path)
        # Use goto_definitions for potentially better accuracy than get_names
        # Find first usage of symbol_name (simple approach) to start inference
        # Note: This might not be the definition line itself
        line, column = None, None
        try:
             # Find first occurrence to get line/col for jedi.infer
             # This is still a bit naive, might find comments or strings
             match_index = file_content.find(symbol_name)
             if match_index != -1:
                  line = file_content.count('\n', 0, match_index) + 1
                  column = match_index - file_content.rfind('\n', 0, match_index) -1
        except Exception:
             pass # Ignore errors finding line/col, try get_names as fallback

        definitions = []
        if line is not None and column is not None:
            try:
                definitions = script.infer(line=line, column=column)
            except Exception as infer_e:
                 print(f"[WARN] jedi.infer failed for {symbol_name} at {line}:{column}: {infer_e}. Falling back to get_names.")
                 definitions = [] # Clear definitions if infer failed

        # Fallback or primary method: Search all names if infer didn't work well
        if not definitions:
            try:
                names = script.get_names(all_scopes=True, definitions=True)
                definitions = [d for d in names if d.name == symbol_name]
            except Exception as get_names_e:
                 print(f"[ERROR] jedi.get_names failed for {target_path}: {get_names_e}")
                 return f"Error: Jedi failed to analyze file {file_path}."


        if definitions:
            # Prefer definitions that are functions or classes
            # Sort to prioritize functions/classes over imports/variables if multiple found
            definitions.sort(key=lambda d: (d.type != 'function', d.type != 'class', d.line))
            found_def = definitions[0] # Take the most likely definition

            print(f"  Jedi found '{found_def.name}' (type: {found_def.type}) at line {found_def.line} in {found_def.module_path}")
            formatted_output = _format_jedi_definition(found_def)
            return f"Definition found for '{symbol_name}' in '{file_path}':\n{formatted_output}"

        else:
            print(f"  Jedi could not find definition for '{symbol_name}' in {file_path}")
            return f"Error: Jedi could not find definition for '{symbol_name}' in '{file_path}'."

    except Exception as e:
        print(f"[ERROR] Tool get_symbol_definition failed: {e}")
        # Be careful not to expose too much internal detail in error messages to LLM
        return f"Error processing file '{file_path}': An unexpected error occurred during analysis."