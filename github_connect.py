import os
from github import Github
from dotenv import load_dotenv

def connect_to_single_repo():
    """Authenticate with GitHub, connect to a single repo, and print all branches."""
    load_dotenv()
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise ValueError("GitHub token not found! Please set GITHUB_TOKEN in environment variables or .env file.")

    g = Github(token)

    repo_name = "tanistha-IO/Metadata_poc"
    repo = g.get_repo(repo_name)
    print(f"Connected to repository: {repo.full_name}\n")

    
    print("Branches in repository:")
    for branch in repo.get_branches():
        print(f" - {branch.name}")

if __name__ == "__main__":
    connect_to_single_repo()
