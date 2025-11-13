from dotenv import load_dotenv
from helper_final import generate_metadata, create_branch_commit_push_pr

if __name__ == "__main__":
    load_dotenv()
    print(" Starting metadata + PR automation pipeline...")

    updated_json = generate_metadata()
    create_branch_commit_push_pr(updated_json)

    print(" Pipeline completed successfully!")
