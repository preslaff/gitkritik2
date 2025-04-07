# cli/main.py

import os
import subprocess
import typer
from typing import Optional
from gitkritik2.core.models import ReviewState
from gitkritik2.graph.build_graph import build_review_graph
from gitkritik2.cli.display import render_review_result

app = typer.Typer()

def inspect_git_state(unstaged: bool, all_files: bool):
    # Detect unpulled commits (warn user)
    subprocess.run(["git", "fetch"], stdout=subprocess.DEVNULL)
    status = subprocess.run(["git", "status", "-uno"], capture_output=True, text=True)
    if "Your branch is behind" in status.stdout:
        typer.secho("Your branch is behind the remote. Consider pulling before reviewing.", fg=typer.colors.YELLOW)

    if all_files:
        typer.echo("Reviewing all modified files (staged + unstaged).")
    elif unstaged:
        typer.echo("Reviewing unstaged changes.")
    else:
        typer.echo("Reviewing staged changes.")

@app.command()
def main(
    unstaged: bool = typer.Option(False, "--unstaged", help="Review unstaged changes."),
    all_files: bool = typer.Option(False, "--all", help="Review all changes (staged + unstaged)."),
    ci: bool = typer.Option(False, "--ci", help="Run in CI mode."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run but skip posting to PR/MR."),
    side_by_side: bool = typer.Option(False, "--side-by-side", help="Display side-by-side diff view."),
    config: Optional[str] = typer.Option(None, "--config", help="Path to config file (optional).")
):
    # Set environment for downstream CI-aware nodes
    if ci:
        os.environ["GITKRITIK_CI_MODE"] = "true"
    elif os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("GITLAB_CI") == "true":
        os.environ["GITKRITIK_CI_MODE"] = "true"
    else:
        os.environ["GITKRITIK_CI_MODE"] = "false"

    if dry_run:
        os.environ["GITKRITIK_DRY_RUN"] = "true"

    # Git state awareness
    inspect_git_state(unstaged, all_files)

    # Initialize the state
    state = ReviewState()
    state_dict = state.model_dump()
    state_dict["unstaged"] = unstaged
    state_dict["all_files"] = all_files
    state_dict["side_by_side"] = side_by_side

    # Run the LangGraph
    graph = build_review_graph().compile()
    final_state_dict = graph.invoke(state_dict)
    
    # ✅ Emergency fix to prevent ReviewState sneaking through
    if isinstance(final_state_dict, ReviewState):
        #print("Final result was a ReviewState object — converting to dict manually.")
        final_state_dict = final_state_dict.model_dump()

    final_state = ReviewState(**final_state_dict)

    # In local mode, render review nicely
    if os.getenv("GITKRITIK_CI_MODE") != "true":
        render_review_result(final_state, side_by_side=side_by_side)

if __name__ == "__main__":
    app()
