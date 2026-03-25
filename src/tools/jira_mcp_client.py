import os
import sys
import yaml
import requests
from requests.auth import HTTPBasicAuth

def main():
    server_url = os.environ.get("JIRA_SERVER_URL")
    user_email = os.environ.get("JIRA_USER_EMAIL")
    api_token = os.environ.get("JIRA_API_TOKEN")
    project_key = os.environ.get("PROJECT_KEY")

    if not all([server_url, user_email, api_token, project_key]):
        print("Error: Missing Jira credentials or project key in environment variables.")
        sys.exit(1)

    print(f"Testing Jira connection to {server_url} for project {project_key}...")
    
    server_url = server_url.rstrip("/")
    api_url = f"{server_url}/rest/api/3/project/{project_key}"

    auth = HTTPBasicAuth(user_email, api_token)
    headers = {"Accept": "application/json"}

    response = requests.get(api_url, auth=auth, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print("Successfully connected and fetched project details.")
        
        # Build schema representation
        policy = {
            "jira_configuration": {
                "project_key": project_key,
                "project_name": data.get("name"),
                "issue_types": [it["name"] for it in data.get("issueTypes", [])]
            },
            "agent_permissions": {
                "allowed_transitions": [
                    "To Do -> In Progress",
                    "In Progress -> In Review",
                    "In Review -> Done"
                ],
                "guarded_transitions": [
                    "Done -> Approved"
                ]
            }
        }
        
        # Serialize to YAML
        with open("project-policy.yaml", "w") as f:
            yaml.dump(policy, f, default_flow_style=False)
            
        print("Successfully generated project-policy.yaml")
    else:
        print(f"Failed to connect to Jira. Status: {response.status_code}")
        print(response.text)
        sys.exit(1)

if __name__ == "__main__":
    main()
