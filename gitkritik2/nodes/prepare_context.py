# nodes/prepare_context.py

import subprocess
from gitkritik2.core.models import ReviewState, FileContext
from gitkritik2.core.utils import ensure_review_state

def get_file_content_from_git(ref: str, filepath: str) -> str:
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{filepath}"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""

def get_diff_summary(filepath: str) -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "--unified=0", "origin/main", "--", filepath],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""

def get_full_diff_chunk(filepath: str) -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "origin/main", "--", filepath],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""

def prepare_context(state: dict) -> dict:
    print("[prepare_context] Preparing file context and diffs")
    context_chunks = []  #Initialize before use
    state = ensure_review_state(state)
    for filepath in state.changed_files:
        before = get_file_content_from_git("origin/main", filepath)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                after = f.read()
        except FileNotFoundError:
            after = ""

        diff_summary = get_diff_summary(filepath)
        full_chunk = get_full_diff_chunk(filepath)

        state.file_contexts[filepath] = FileContext(
            path=filepath,
            before=before,
            after=after,
            diff=diff_summary,
            strategy=state.kritik_config.strategy
        )

        if full_chunk:
            context_chunks.append(full_chunk)

    state.context_chunks = context_chunks
    #Debbuging the dict error
    
    return state.model_dump()

