import requests

def get_pr_file_content(repo, pr_number, token):
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.raw"}
    files_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    resp = requests.get(files_url, headers={"Authorization": f"token {token}"})
    if resp.status_code != 200:
        print(f"Error fetching PR files: {resp.text}")
        return ""
    
    files = resp.json()
    for f in files:
        if f["filename"].endswith(".md"):
            raw_url = f["raw_url"]
            raw_resp = requests.get(raw_url, headers={"Authorization": f"token {token}"})
            return raw_resp.text
    return ""

def create_issue(repo, title, body, token):
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    payload = {"title": title, "body": body}
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 201:
        print(f"Error creating issue: {resp.text}")
        resp.raise_for_status()
    return resp.json()
