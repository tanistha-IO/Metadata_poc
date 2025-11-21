from github import Github, Auth
from dotenv import load_dotenv
from git import Repo
import os

load_dotenv()

def handle_pull_request(repo_name, branch_name, base_branch="main"):
    """
    Check for existing PRs for the branch.
    Create a new PR if none exists. Push branch if missing remotely.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GitHub token not found! Please set GITHUB_TOKEN in your .env file.")

    g = Github(auth=Auth.Token(token))
    repo = g.get_repo(repo_name)
    print(f"\n Connected to repo: {repo.full_name}")

    local_repo_path = "/home/user/project-1"
    local_repo = Repo(local_repo_path)
    branch = branch_name.strip()

    local_branches = [b.name for b in local_repo.branches]
    remote_branches = [r.name.split('/')[-1] for r in local_repo.remotes.origin.refs]

    if branch not in remote_branches:
        if branch not in local_branches:
            raise ValueError(f"Local branch '{branch}' does not exist.")
        print(f"Pushing local branch '{branch}' to remote...")
        local_repo.git.push('--set-upstream', 'origin', branch)
        print(f"Branch '{branch}' pushed successfully.")

    open_prs = repo.get_pulls(state="open", base=base_branch)
    existing_pr = next((pr for pr in open_prs if pr.head.ref == branch), None)

    if existing_pr:
        print(f" Existing PR found for branch '{branch}': {existing_pr.html_url}")
    else:
        title = f"Auto PR from {branch}"
        body = "This pull request was automatically created via script."
        new_pr = repo.create_pull(title=title, body=body, head=branch, base=base_branch)
        print(f" Created new PR: {new_pr.html_url}")

if __name__ == "__main__":
    handle_pull_request(
        repo_name="tanistha-IO/Metadata_poc",
        branch_name="A",     
        base_branch="main"
    )
