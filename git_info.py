from git_info import Repo
repo_path = "."
repo = Repo(repo_path)
active_branch = repo.active_branch.name
print(f"Active Branch: {active_branch}")
branches = [b.name for b in repo.branches]
print("All Branches:")
for branch in branches:
    print(f" - {branch}")


