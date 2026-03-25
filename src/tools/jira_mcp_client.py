import os
import sys
import json
import yaml
import requests
from requests.auth import HTTPBasicAuth


def _get_auth():
    server_url = os.environ.get("JIRA_SERVER_URL", "").rstrip("/")
    user_email = os.environ.get("JIRA_USER_EMAIL")
    api_token = os.environ.get("JIRA_API_TOKEN")
    if not all([server_url, user_email, api_token]):
        raise ValueError("Missing JIRA_SERVER_URL, JIRA_USER_EMAIL, or JIRA_API_TOKEN")
    return server_url, HTTPBasicAuth(user_email, api_token)


def search_issues(project_key, status=None, max_results=50):
    server_url, auth = _get_auth()
    jql = f"project={project_key}"
    if status:
        jql += f" AND status='{status}'"
    url = f"{server_url}/rest/api/3/search"
    resp = requests.get(url, auth=auth, headers={"Accept": "application/json"},
                        params={"jql": jql, "maxResults": max_results})
    resp.raise_for_status()
    return resp.json().get("issues", [])


def get_issue(issue_key):
    server_url, auth = _get_auth()
    url = f"{server_url}/rest/api/3/issue/{issue_key}"
    resp = requests.get(url, auth=auth, headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()


def create_issue(project_key, summary, description, issue_type="Story", labels=None):
    server_url, auth = _get_auth()
    url = f"{server_url}/rest/api/3/issue"
    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]
            },
            "issuetype": {"name": issue_type},
        }
    }
    if labels:
        payload["fields"]["labels"] = labels
    resp = requests.post(url, auth=auth, headers={"Accept": "application/json", "Content-Type": "application/json"},
                         json=payload)
    if resp.status_code not in (200, 201):
        print(f"Jira create_issue failed: {resp.status_code} {resp.text}")
    resp.raise_for_status()
    return resp.json()


def add_comment(issue_key, comment_text):
    server_url, auth = _get_auth()
    url = f"{server_url}/rest/api/3/issue/{issue_key}/comment"
    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment_text}]}]
        }
    }
    resp = requests.post(url, auth=auth, headers={"Accept": "application/json", "Content-Type": "application/json"},
                         json=payload)
    resp.raise_for_status()
    return resp.json()


def get_transitions(issue_key):
    server_url, auth = _get_auth()
    url = f"{server_url}/rest/api/3/issue/{issue_key}/transitions"
    resp = requests.get(url, auth=auth, headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp.json().get("transitions", [])


def transition_issue(issue_key, transition_name):
    transitions = get_transitions(issue_key)
    target = next((t for t in transitions if t["name"].lower() == transition_name.lower()), None)
    if not target:
        available = [t["name"] for t in transitions]
        print(f"Transition '{transition_name}' not found. Available: {available}")
        return None
    server_url, auth = _get_auth()
    url = f"{server_url}/rest/api/3/issue/{issue_key}/transitions"
    resp = requests.post(url, auth=auth, headers={"Content-Type": "application/json"},
                         json={"transition": {"id": target["id"]}})
    resp.raise_for_status()
    print(f"Successfully transitioned {issue_key} to '{transition_name}'")
    return True


def get_project_meta(project_key):
    server_url, auth = _get_auth()
    url = f"{server_url}/rest/api/3/project/{project_key}"
    resp = requests.get(url, auth=auth, headers={"Accept": "application/json"})
    resp.raise_for_status()
    data = resp.json()
    return {
        "project_key": project_key,
        "project_name": data.get("name"),
        "issue_types": [it["name"] for it in data.get("issueTypes", [])]
    }


def generate_policy(project_key, policy_path="project-policy.yaml"):
    meta = get_project_meta(project_key)
    policy = {
        "jira_configuration": meta,
        "agent_permissions": {
            "allowed_transitions": ["To Do -> In Progress", "In Progress -> In Review", "In Review -> Done"],
            "guarded_transitions": ["Done -> Approved"]
        }
    }
    with open(policy_path, "w") as f:
        yaml.dump(policy, f, default_flow_style=False)
    print(f"Generated {policy_path}")
    return policy


if __name__ == "__main__":
    project_key = os.environ.get("PROJECT_KEY", "SCRUM")
    generate_policy(project_key)
