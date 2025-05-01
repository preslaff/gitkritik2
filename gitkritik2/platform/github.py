# platform/github.py
import os
import requests
from typing import List
from gitkritik2.core.models import ReviewState, Comment # Ensure Comment is imported

GITHUB_API = "https://api.github.com"

def _get_github_auth_headers() -> dict | None: # Added None return type possibility
    """Helper to get GitHub Auth headers."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("[GitHub] Error: GITHUB_TOKEN environment variable not set.")
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

# Keep post_summary_comment_github as refactored previously (accepting ReviewState)
def post_summary_comment_github(state: ReviewState):
    # ... (implementation remains the same) ...
    print("[GitHub] Posting summary comment to Conversation tab")
    if not state.repo or not state.pr_number or not state.summary_review:
        print("[GitHub] Missing repo, PR number, or summary content in state. Skipping.")
        return

    headers = _get_github_auth_headers()
    if not headers: return

    url = f"{GITHUB_API}/repos/{state.repo}/issues/{state.pr_number}/comments"
    payload = {"body": state.summary_review}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        print("[GitHub] Summary comment posted successfully.")
    except requests.exceptions.RequestException as e:
        print(f"[GitHub] Failed to post summary comment: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.status_code} {e.response.text}")


# --- REFACTORED VERSION ---
def post_inline_comment_github(state: ReviewState): # Takes ReviewState now
    """
    Posts inline comments to the Files Changed tab using the Review API for efficiency.
    Accepts ReviewState directly.
    """
    print("[GitHub] Posting inline comments via Review API")
    # Extract data from state
    if not state.repo or not state.pr_number or not state.inline_comments:
        print("[GitHub] Missing repo, PR number, or inline comments in state. Skipping.")
        return

    headers = _get_github_auth_headers()
    if not headers: return

    # 1. Get the commit ID of the PR HEAD
    pr_url = f"{GITHUB_API}/repos/{state.repo}/pulls/{state.pr_number}"
    commit_id = None
    try:
        print(f"[GitHub] Fetching PR details from: {pr_url}")
        pr_response = requests.get(pr_url, headers=headers, timeout=15)
        pr_response.raise_for_status()
        pr_data = pr_response.json()
        commit_id = pr_data.get("head", {}).get("sha")
        if not commit_id:
             print(f"[GitHub] Error: Could not retrieve HEAD commit SHA for PR #{state.pr_number}. Response: {pr_data}")
             return
        print(f"[GitHub] Found HEAD commit SHA: {commit_id}")
    except requests.exceptions.RequestException as e:
        print(f"[GitHub] Error fetching PR details: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Response: {e.response.status_code} {e.response.text}")
        return
    except Exception as e: # Catch potential JSON decoding errors
        print(f"[GitHub] Error processing PR details response: {e}")
        return


    # 2. Format comments for the Review API
    review_comments = []
    # state.inline_comments should contain Comment objects if ensure_review_state worked
    for comment_obj in state.inline_comments:
         # Access the platform_body attribute added by format_output
         if hasattr(comment_obj, 'platform_body') and comment_obj.platform_body and comment_obj.file and comment_obj.line is not None:
            review_comments.append({
                "path": comment_obj.file,
                "line": comment_obj.line,
                "body": comment_obj.platform_body, # Use the formatted body
            })
         else:
              print(f"[WARN] Skipping invalid comment object for GitHub review: {comment_obj}")


    if not review_comments:
         print("[GitHub] No valid comments formatted for review submission.")
         return

    # 3. Post the review
    review_url = f"{GITHUB_API}/repos/{state.repo}/pulls/{state.pr_number}/reviews"
    payload = {
        "commit_id": commit_id,
        "event": "COMMENT", # Post comments without changing PR state
        "comments": review_comments,
        # "body": "AI Review Comments" # Optional summary for the review itself
    }

    try:
        print(f"[GitHub] Posting review with {len(review_comments)} comments to: {review_url}")
        response = requests.post(review_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        print(f"[GitHub] Successfully posted review.")
    except requests.exceptions.RequestException as e:
        print(f"[GitHub] Failed to post review with inline comments: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.status_code} {e.response.text}")