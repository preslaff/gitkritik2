# cli/main.py
import os
import subprocess
import typer
from typing import Optional
from gitkritik2.core.models import ReviewState # Import for type hinting
from gitkritik2.graph.build_graph import build_review_graph
from gitkritik2.cli.display import render_review_result
# Removed config import, handled by init_state now
# from gitkritik2.core.config import load_kritik_config
from dotenv import load_dotenv

load_dotenv() # Load .env before accessing env vars

app = typer.Typer()

# Keep inspect_git_state as before

@app.command()
def main(
    unstaged: bool = typer.Option(False, "--unstaged", "-u", help="Review unstaged changes."),
    all_files: bool = typer.Option(False, "--all", "-a", help="Review all changes (staged + unstaged)."),
    ci: bool = typer.Option(False, "--ci", help="Run in CI mode (auto-detects if GITHUB_ACTIONS or GITLAB_CI is true)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run review but skip posting comments to platform."),
    side_by_side: bool = typer.Option(False, "--side-by-side", "-s", help="Display side-by-side diff view locally."),
    inline: bool = typer.Option(False, "--inline", "-i", help="Enable posting inline comments (requires --ci usually) AND render inline locally."),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file (e.g., .kritikrc.yaml) (optional).")
):
    """Runs AI code review on Git changes."""

    # --- Capture Target Directory ---
    target_repo_dir = os.getcwd()
    print(f"[CLI Main] Target Repository Directory: {target_repo_dir}")
    # --- End Capture ---

    # --- Environment Setup ---
    is_ci_mode = ci or os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("GITLAB_CI") == "true"
    os.environ["GITKRITIK_CI_MODE"] = "true" if is_ci_mode else "false"

    if dry_run:
        os.environ["GITKRITIK_DRY_RUN"] = "true"
        typer.secho("Dry run mode enabled: Comments will not be posted.", fg=typer.colors.YELLOW)

    # Set env var for inline *posting* control based on --inline flag
    # The post_inline node checks this env var
    os.environ["GITKRITIK_INLINE"] = "true" if inline else "false"

    if not is_ci_mode:
        # Only inspect git state if not in CI (CI runners often have detached HEADs)
        # inspect_git_state(unstaged, all_files) # Decide if this check is useful locally
        pass
    else:
        typer.echo("Running in CI mode.")


    # --- Initialize State Dictionary ---
    # Start with flags needed by early nodes (init_state will load more)
    initial_state_dict = {
        # --- Add Target Directory to State ---
        "target_repo_dir": target_repo_dir,
        # --- End Add ---
        "config_file_path": config,
        "review_unstaged": unstaged,
        "review_all_files": all_files,
        "is_ci_mode": is_ci_mode,
        "dry_run": dry_run,
        "show_inline_locally": inline,
        "side_by_side_display": side_by_side,
        # Initialize empty containers
        "changed_files": [],
        "file_contexts": {},
        "agent_results": {},
        "inline_comments": [],
    }

    # --- Build and Run Graph ---
    typer.echo("Building review graph...")
    graph = build_review_graph().compile()

    typer.echo("Invoking review graph...")
    # LangSmith Integration: If env vars are set, tracing happens automatically here.
    final_state_dict = graph.invoke(initial_state_dict)
    typer.echo("Review graph execution finished.")

    # --- Process Final State ---
    # Ensure final state is a dict before creating the Pydantic model
    if not isinstance(final_state_dict, dict):
         typer.secho(f"Error: Graph did not return a dictionary state. Got: {type(final_state_dict)}", fg=typer.colors.RED)
         raise typer.Exit(code=1)

    try:
        # Create the final state model for easier access and display
        final_state = ReviewState(**final_state_dict)
    except Exception as e:
        typer.secho(f"Error creating final ReviewState model: {e}", fg=typer.colors.RED)
        print("Final state dictionary received from graph:")
        import json; print(json.dumps(final_state_dict, indent=2)) # Print state for debugging
        raise typer.Exit(code=1)

    # --- Display Locally ---
    if not final_state.is_ci_mode:
        typer.echo("\n--- Review Results ---")
        render_review_result(
            final_state,
            side_by_side=final_state.side_by_side_display,
            show_inline=final_state.show_inline_locally # Use the specific flag
        )
    else:
         typer.echo("CI mode: Skipping local display. Check PR/MR for comments.")

    # Optional: Add exit code based on findings?
    # num_bug_comments = len(final_state.agent_results.get("bug", AgentResult(agent_name="bug", comments=[])).comments)
    # if num_bug_comments > 0:
    #     typer.secho(f"Found {num_bug_comments} potential bugs.", fg=typer.colors.RED)
    #     # raise typer.Exit(code=1) # Optionally fail CI build

if __name__ == "__main__":
    app()