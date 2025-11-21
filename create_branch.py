from git_info import Repo

def create_or_checkout_branch(repo_path, branch_name):
    """
    Create a branch if it doesn't exist, or checkout if it does.
    :param repo_path: Path to your local Git repository
    :param branch_name: Name of the branch to switch/create
    """
    repo = Repo("/home/user/project-1")

    local_branches = [b.name for b in repo.branches]

    remote_branches = [ref.name.split('/')[-1] for ref in repo.remotes.origin.refs]

    if branch_name in local_branches:
        repo.git.checkout(branch_name)
        print(f" Switched to existing local branch '{branch_name}'")

    elif branch_name in remote_branches:
        repo.git.checkout('-b', branch_name, f'origin/{branch_name}')
        print(f"Created local branch '{branch_name}' from remote and checked out")

    else:
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()
        print(f"Created and checked out new branch '{branch_name}'")

        repo.git.push('--set-upstream', 'origin', branch_name)
        print(f" Pushed new branch '{branch_name}' to remote")

if __name__ == "__main__":
    repo_path = "/home/user/project-1"
    test_branch = "B"  
    create_or_checkout_branch(repo_path, test_branch)