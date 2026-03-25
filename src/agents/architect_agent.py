import os
import sys
import json
import argparse
import re
from langchain_google_genai import ChatGoogleGenerativeAI

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.github_client import get_issue_body, add_issue_comment, close_issue
from tools.jira_mcp_client import create_issue as jira_create_issue
from state.checkpoint_manager import load_checkpoint


def run_architect_review(backlog_markdown):
    """Use Gemini to append non-functional requirements and technical constraints to the backlog."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

    prompt = f"""You are an Expert Solutions Architect. Review the following draft backlog and enhance it.

For each User Story, add:
1. **Non-Functional Requirements** (performance, security, scalability, observability)
2. **Technical Notes** (suggested API patterns, data models, caching strategies)
3. **Dependencies** (other stories or external services this story depends on)

Also output a final JSON array with this exact schema for each story:
```json
[
  {{
    "summary": "Story title",
    "description": "Full story text with acceptance criteria and NFRs",
    "issue_type": "Story",
    "labels": ["agent-generated"]
  }}
]
```

DRAFT BACKLOG:
{backlog_markdown}
"""
    response = llm.invoke(prompt)
    return response.content


def extract_jira_payloads(architect_output):
    """Extract JSON array of Jira issue payloads from the architect output."""
    # Find JSON array in the output
    match = re.search(r'\[\s*\{.*?\}\s*\]', architect_output, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            print("[Architect] Warning: Could not parse JSON from output, using fallback.")
    return []


def push_stories_to_jira(stories, project_key):
    """Create Jira issues from the extracted story payloads."""
    created = []
    for story in stories:
        try:
            result = jira_create_issue(
                project_key=project_key,
                summary=story.get("summary", "Untitled Story"),
                description=story.get("description", ""),
                issue_type=story.get("issue_type", "Story"),
                labels=story.get("labels", ["agent-generated"])
            )
            created.append(result)
            print(f"[Architect] Created Jira issue: {result.get('key', 'unknown')}")
        except Exception as e:
            print(f"[Architect] Failed to create Jira issue: {e}")
    return created


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", required=True, help="GitHub Issue number to resume from")
    args = parser.parse_args()

    issue_number = args.resume
    repo = os.environ.get("GITHUB_REPOSITORY", "SumitSahacatiim2010/Requirements-test")
    token = os.environ.get("GITHUB_TOKEN")
    project_key = os.environ.get("JIRA_PROJECT_KEY", "SCRUM")

    if not token:
        print("Error: GITHUB_TOKEN not set")
        sys.exit(1)

    # 1. Load checkpoint
    print(f"[Architect] Loading checkpoint for Issue #{issue_number}...")
    state = load_checkpoint(repo, token, issue_number)

    if not state:
        # Fallback: read the issue body directly
        print("[Architect] No checkpoint found, reading issue body directly...")
        issue_body = get_issue_body(repo, issue_number, token)
        backlog_markdown = issue_body
    else:
        backlog_markdown = state.get("backlog_markdown", "")
        print(f"[Architect] Checkpoint loaded. PR #{state.get('pr_number')}, status: {state.get('status')}")

    if not backlog_markdown:
        print("[Architect] No backlog content found. Exiting.")
        sys.exit(1)

    # 2. Run Architect Gemini Agent
    print("[Architect] Running architectural review with Gemini...")
    architect_output = run_architect_review(backlog_markdown)
    print("[Architect] Architect review complete.")

    # 3. Extract structured Jira payloads
    stories = extract_jira_payloads(architect_output)
    print(f"[Architect] Extracted {len(stories)} stories for Jira.")

    # 4. Push to Jira
    if stories:
        created_issues = push_stories_to_jira(stories, project_key)
        jira_summary = "\n".join([f"- {i.get('key', '?')}: {i.get('fields', {}).get('summary', '?')}"
                                   for i in created_issues if i])

        # 5. Comment on the GitHub Issue with results
        comment = (
            f"## ✅ Approved & Synced to Jira\n\n"
            f"**{len(created_issues)} stories created in Jira project `{project_key}`:**\n\n"
            f"{jira_summary}\n\n"
            f"_Architect Agent review applied. Non-functional requirements appended._"
        )
        add_issue_comment(repo, issue_number, comment, token)
        close_issue(repo, issue_number, token)
        print(f"[Architect] Issue #{issue_number} updated and closed.")
    else:
        add_issue_comment(repo, issue_number,
                          "⚠️ Could not extract structured stories from architect output. Please review manually.",
                          token)
        print("[Architect] Warning: No stories extracted.")


if __name__ == "__main__":
    main()
