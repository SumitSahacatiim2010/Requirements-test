import os
import sys
import argparse
from langchain_google_genai import ChatGoogleGenerativeAI

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from tools.github_client import get_pr_file_content, create_issue
except ImportError:
    pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", help="Pull request number containing the PRD")
    args = parser.parse_args()

    pr_number = args.pr
    repo = os.environ.get("GITHUB_REPOSITORY", "SumitSahacatiim2010/Requirements-test")
    token = os.environ.get("GITHUB_TOKEN")
    
    if not pr_number or not token:
        print("Missing PR number or GITHUB_TOKEN in environment variables.")
        sys.exit(1)

    print(f"Fetching markdown files for PR #{pr_number} from {repo}...")
    prd_text = get_pr_file_content(repo, pr_number, token)
    
    if not prd_text:
        print("No markdown PRD files found in PR.")
        sys.exit(1)
        
    print(f"Successfully fetched PRD text ({len(prd_text)} chars). Executing Gemini Product Manager Node...")
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    
    prompt = f"""You are an Expert Agile Product Manager. Read the following Product Requirements Document (PRD) and break it down into a highly structured backlog.
Please output:
1. A list of defining **Epics**.
2. Granular **User Stories** (format: As a [role], I want [action] so that [benefit]).
3. Detailed Acceptance Criteria for each story.

Format your output as a clean Markdown document. Do NOT output anything other than the markdown backlog itself.

PRD TEXT:
{prd_text}
"""
    response = llm.invoke(prompt)
    backlog_markdown = response.content
    
    print("Agent output successfully generated. Creating GitHub Issue for HITL Approval...")
    
    issue_body = f"## Draft Backlog for PR #{pr_number}\n\n" + backlog_markdown + "\n\n---\n*Comment `/approve` to sync these changes to Jira.*"
    
    issue = create_issue(repo, f"Draft Backlog Review: PR #{pr_number}", issue_body, token)
    
    print(f"Successfully created Draft Backlog Issue: {issue.get('html_url')}")

if __name__ == "__main__":
    main()
