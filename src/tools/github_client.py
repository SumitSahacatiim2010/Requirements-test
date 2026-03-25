import os
import json
import base64
import requests

GITHUB_API = "https://api.github.com"


def _headers(token):
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}


# --------------- Pull Request Helpers ---------------

def get_pr_file_content(repo, pr_number, token):
    """Fetch the raw text of all .md files changed in a PR."""
    files_url = f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}/files"
    resp = requests.get(files_url, headers=_headers(token))
    resp.raise_for_status()
    contents = []
    for f in resp.json():
        if f["filename"].endswith(".md"):
            raw_resp = requests.get(f["raw_url"], headers=_headers(token))
            contents.append(raw_resp.text)
    return "\n\n".join(contents)


def get_open_prs(repo, token):
    """List open PRs for cross-referencing with Jira."""
    url = f"{GITHUB_API}/repos/{repo}/pulls?state=open"
    resp = requests.get(url, headers=_headers(token))
    resp.raise_for_status()
    return resp.json()


def get_merged_prs(repo, token, since=None):
    """List recently closed+merged PRs."""
    url = f"{GITHUB_API}/repos/{repo}/pulls?state=closed&sort=updated&direction=desc&per_page=30"
    resp = requests.get(url, headers=_headers(token))
    resp.raise_for_status()
    return [pr for pr in resp.json() if pr.get("merged_at")]


# --------------- Issue Helpers ---------------

def create_issue(repo, title, body, token, labels=None):
    url = f"{GITHUB_API}/repos/{repo}/issues"
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    resp = requests.post(url, headers=_headers(token), json=payload)
    if resp.status_code != 201:
        print(f"Error creating issue: {resp.text}")
    resp.raise_for_status()
    return resp.json()


def get_issue_body(repo, issue_number, token):
    url = f"{GITHUB_API}/repos/{repo}/issues/{issue_number}"
    resp = requests.get(url, headers=_headers(token))
    resp.raise_for_status()
    return resp.json().get("body", "")


def add_issue_comment(repo, issue_number, body, token):
    url = f"{GITHUB_API}/repos/{repo}/issues/{issue_number}/comments"
    resp = requests.post(url, headers=_headers(token), json={"body": body})
    resp.raise_for_status()
    return resp.json()


def close_issue(repo, issue_number, token):
    url = f"{GITHUB_API}/repos/{repo}/issues/{issue_number}"
    resp = requests.patch(url, headers=_headers(token), json={"state": "closed"})
    resp.raise_for_status()
    return resp.json()


# --------------- Git Branch State Store ---------------

def save_state_to_branch(repo, token, branch, filename, content):
    """Save JSON state to a file on a specific branch via the GitHub Contents API."""
    url = f"{GITHUB_API}/repos/{repo}/contents/{filename}"
    headers = _headers(token)

    # Check if the file already exists (need its SHA to update)
    sha = None
    resp = requests.get(url, headers=headers, params={"ref": branch})
    if resp.status_code == 200:
        sha = resp.json().get("sha")

    encoded = base64.b64encode(content.encode()).decode()
    payload = {
        "message": f"chore: save agent state {filename} [skip ci]",
        "content": encoded,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(url, headers=headers, json=payload)
    if resp.status_code not in (200, 201):
        print(f"Error saving state: {resp.text}")
    resp.raise_for_status()
    print(f"State saved to {branch}:{filename}")
    return resp.json()


def load_state_from_branch(repo, token, branch, filename):
    """Load JSON state from a file on a specific branch."""
    url = f"{GITHUB_API}/repos/{repo}/contents/{filename}"
    resp = requests.get(url, headers=_headers(token), params={"ref": branch})
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    content = base64.b64decode(resp.json()["content"]).decode()
    return json.loads(content)


def ensure_branch_exists(repo, token, branch, source_branch="main"):
    """Create an orphan branch if it doesn't exist."""
    url = f"{GITHUB_API}/repos/{repo}/git/refs"
    resp = requests.get(f"{url}/heads/{branch}", headers=_headers(token))
    if resp.status_code == 200:
        return  # branch exists

    # Get SHA of source branch
    source_resp = requests.get(f"{url}/heads/{source_branch}", headers=_headers(token))
    source_resp.raise_for_status()
    sha = source_resp.json()["object"]["sha"]

    # Create the new branch
    create_resp = requests.post(url, headers=_headers(token),
                                json={"ref": f"refs/heads/{branch}", "sha": sha})
    create_resp.raise_for_status()
    print(f"Created branch '{branch}'")
