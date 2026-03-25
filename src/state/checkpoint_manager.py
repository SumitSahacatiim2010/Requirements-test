import os
import json
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.github_client import save_state_to_branch, load_state_from_branch, ensure_branch_exists

STATE_BRANCH = "agent-state-checkpoints"


def save_checkpoint(repo, token, issue_id, state_dict):
    """Serialize agent state as JSON and commit it to the state branch via GitHub API."""
    ensure_branch_exists(repo, token, STATE_BRANCH)
    filename = f"state/issue_{issue_id}.json"
    content = json.dumps(state_dict, indent=2, default=str)
    save_state_to_branch(repo, token, STATE_BRANCH, filename, content)
    print(f"Checkpoint saved for issue {issue_id}")


def load_checkpoint(repo, token, issue_id):
    """Load previously saved agent state from the state branch."""
    filename = f"state/issue_{issue_id}.json"
    data = load_state_from_branch(repo, token, STATE_BRANCH, filename)
    if data:
        print(f"Checkpoint loaded for issue {issue_id}")
    else:
        print(f"No checkpoint found for issue {issue_id}")
    return data
