from git import Repo
from github import Github, Auth
import os

REPO_PATH = "/home/user/project-1"      
GITHUB_REPO = "tanistha-IO/Metadata_poc" 
NEW_BRANCH = "D"
COMMIT_MESSAGE = "Added update in branch D"
FILE_TO_UPDATE = "new.txt"              

def create_and_commit_branch():
    repo = Repo(REPO_PATH)
    current_branch = repo.active_branch.name
    print(f" Active branch: {current_branch}")

    if NEW_BRANCH in [b.name for b in repo.branches]:
        repo.git.checkout(NEW_BRANCH)
        print(f" Switched to existing branch '{NEW_BRANCH}'")
    else:
        new_branch = repo.create_head(NEW_BRANCH)
        new_branch.checkout()
        print(f" Created and checked out new branch '{NEW_BRANCH}'")

    file_path = os.path.join(REPO_PATH, FILE_TO_UPDATE)
    with open(file_path, "a") as f:
        f.write("\nUpdated in new branch D")

    repo.git.add(FILE_TO_UPDATE)
    repo.index.commit(COMMIT_MESSAGE)
    print(f" Commit created: '{COMMIT_MESSAGE}'")

    return repo

def push_branch_to_github(repo):
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError(" GitHub token not found! Please set GITHUB_TOKEN in environment variables.")
    
    g = Github(auth=Auth.Token(token))
    github_repo = g.get_repo(GITHUB_REPO)

    origin = repo.remote(name="origin")
    origin.push(refspec=f"{NEW_BRANCH}:{NEW_BRANCH}")
    print(f" Pushed branch '{NEW_BRANCH}' to remote GitHub repository.")

    remote_branches = [b.name for b in github_repo.get_branches()]
    if NEW_BRANCH in remote_branches:
        print(f"Verified: Branch '{NEW_BRANCH}' now exists on GitHub.")
    else:
        print("Branch not found on GitHub — push may have failed.")


if __name__ == "__main__":
    repo = create_and_commit_branch()
    push_branch_to_github(repo)
