import os
import sys
import json
import argparse
import yaml
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.jira_mcp_client import search_issues, get_issue, add_comment
from tools.github_client import get_open_prs, get_merged_prs, add_issue_comment


# Heuristic state mapping: GitHub PR state -> expected Jira status
STATE_MAP = {
    "open": "In Progress",
    "merged": "Done",
    "closed": "Done",
}


def load_policy():
    policy_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                               "project-policy.yaml")
    if os.path.exists(policy_path):
        with open(policy_path) as f:
            return yaml.safe_load(f)
    return {}


def load_db(db_path):
    if os.path.exists(db_path):
        with open(db_path, "r") as f:
            return json.load(f)
    return {"linkages": {}, "last_sync": None, "suggestions": []}


def save_db(db, db_path):
    db["last_sync"] = datetime.utcnow().isoformat()
    with open(db_path, "w") as f:
        json.dump(db, f, indent=2)


def extract_jira_key_from_pr(pr):
    """Extract Jira issue key from PR title or branch name (e.g., SCRUM-123)."""
    import re
    title = pr.get("title", "")
    branch = pr.get("head", {}).get("ref", "")
    combined = f"{title} {branch}"
    matches = re.findall(r'[A-Z]+-\d+', combined)
    return matches


def run_sync(db, repo, token, project_key):
    """Main synchronization logic."""
    policy = load_policy()
    allowed_transitions = policy.get("agent_permissions", {}).get("allowed_transitions", [])
    guarded_transitions = policy.get("agent_permissions", {}).get("guarded_transitions", [])

    suggestions = []

    # 1. Ingest open Jira issues
    print("[Sync] Fetching open Jira issues...")
    try:
        jira_issues = search_issues(project_key, status=None)
        print(f"[Sync] Found {len(jira_issues)} Jira issues.")
    except Exception as e:
        print(f"[Sync] Warning: Could not fetch Jira issues: {e}")
        jira_issues = []

    jira_map = {}
    for issue in jira_issues:
        key = issue["key"]
        status = issue["fields"]["status"]["name"]
        jira_map[key] = {"status": status, "summary": issue["fields"]["summary"]}

    # 2. Cross-reference open PRs
    print("[Sync] Fetching open GitHub PRs...")
    try:
        open_prs = get_open_prs(repo, token)
        print(f"[Sync] Found {len(open_prs)} open PRs.")
    except Exception as e:
        print(f"[Sync] Warning: Could not fetch open PRs: {e}")
        open_prs = []

    for pr in open_prs:
        jira_keys = extract_jira_key_from_pr(pr)
        for key in jira_keys:
            db["linkages"][key] = {
                "pr_number": pr["number"],
                "pr_state": "open",
                "pr_title": pr["title"],
                "last_seen": datetime.utcnow().isoformat()
            }

            # Heuristic: PR is open but Jira is still "To Do"
            if key in jira_map and jira_map[key]["status"] == "To Do":
                transition_str = "To Do -> In Progress"
                if transition_str in allowed_transitions:
                    suggestion = f"PR #{pr['number']} is open for {key}, but Jira status is 'To Do'. Suggest moving to 'In Progress'."
                    suggestions.append({"issue_key": key, "suggestion": suggestion, "action": "comment"})
                    print(f"[Sync] Suggestion: {suggestion}")

    # 3. Cross-reference merged PRs
    print("[Sync] Fetching recently merged GitHub PRs...")
    try:
        merged_prs = get_merged_prs(repo, token)
        print(f"[Sync] Found {len(merged_prs)} recently merged PRs.")
    except Exception as e:
        print(f"[Sync] Warning: Could not fetch merged PRs: {e}")
        merged_prs = []

    for pr in merged_prs:
        jira_keys = extract_jira_key_from_pr(pr)
        for key in jira_keys:
            db["linkages"][key] = {
                "pr_number": pr["number"],
                "pr_state": "merged",
                "pr_title": pr["title"],
                "merged_at": pr.get("merged_at"),
                "last_seen": datetime.utcnow().isoformat()
            }

            # Heuristic: PR merged but Jira still "In Progress" or "In Review"
            if key in jira_map and jira_map[key]["status"] in ("In Progress", "In Review"):
                transition_str = f"{jira_map[key]['status']} -> Done"
                if any(transition_str.startswith(t.split(" -> ")[0]) for t in allowed_transitions):
                    suggestion = f"PR #{pr['number']} merged for {key}, but Jira status is '{jira_map[key]['status']}'. Suggest moving to 'Done'."
                    suggestions.append({"issue_key": key, "suggestion": suggestion, "action": "comment"})
                    print(f"[Sync] Suggestion: {suggestion}")

    # 4. Post non-destructive suggestions as Jira comments
    for s in suggestions:
        try:
            add_comment(s["issue_key"], f"🤖 Agent Suggestion: {s['suggestion']}")
            print(f"[Sync] Commented on {s['issue_key']}")
        except Exception as e:
            print(f"[Sync] Warning: Could not comment on {s['issue_key']}: {e}")

    db["suggestions"] = suggestions
    return db


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", required=True, help="Path to the traceability JSON database")
    parser.add_argument("--project-key", default=None, help="Jira project key")
    args = parser.parse_args()

    repo = os.environ.get("GITHUB_REPOSITORY", "SumitSahacatiim2010/Requirements-test")
    token = os.environ.get("GITHUB_TOKEN")
    project_key = args.project_key or os.environ.get("JIRA_PROJECT_KEY", "SCRUM")

    if not token:
        print("Error: GITHUB_TOKEN not set")
        sys.exit(1)

    print(f"[Sync] Starting hourly synchronization for {repo} <-> Jira {project_key}")
    db = load_db(args.db_path)
    db = run_sync(db, repo, token, project_key)
    save_db(db, args.db_path)
    print(f"[Sync] Synchronization complete. {len(db['linkages'])} linkages tracked.")


if __name__ == "__main__":
    main()
