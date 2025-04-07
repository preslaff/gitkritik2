import subprocess
from gitkritik2.core.models import ReviewState
from gitkritik2.core.utils import ensure_review_state

def detect_changes(state: dict) -> dict:
    print("[detect_changes] Running git diff to find changed files")
    state = ensure_review_state(state)  # ✅ Convert dict to model

    try:
        subprocess.run(["git", "rev-parse", "--verify", "HEAD"], check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("[detect_changes] No commits yet — skipping diff")
        state.changed_files = []
        return state.model_dump()

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError:
        print("[detect_changes] origin/main not available — falling back to HEAD diff")
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )

    state.changed_files = result.stdout.strip().splitlines()
    
    #Debbuging the dict error
    
    return state.model_dump()