import subprocess
import sys
import os

TEMPLATE_REPO_URL = "https://github.com/qkabi-games/miniverse-template"
TEMPLATE_REMOTE_NAME = "miniverse-template"
TEMPLATE_BRANCH = "master"

# ANSI colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


def run_command(command, check=True, capture_output=False):
    """Runs a shell command."""
    try:
        result = subprocess.run(
            command,
            check=check,
            shell=True,
            text=True,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
        )
        return result
    except subprocess.CalledProcessError as e:
        if not check:
            return e
        print(f"{RED}Error running command: {command}{RESET}")
        if e.stderr:
            print(e.stderr)
        sys.exit(1)


def check_clean_work_tree():
    """Ensures there are no uncommitted changes before starting."""
    res = run_command("git status --porcelain", capture_output=True)
    if res.stdout.strip():
        print(f"{RED}Error: Your working tree is dirty.{RESET}")
        print("Please commit or stash your changes before running the rebase script.")
        sys.exit(1)


def setup_remote():
    """Checks if remote exists, adds it if not."""
    print(f"{YELLOW}Checking remotes...{RESET}")
    res = run_command("git remote -v", capture_output=True)

    if TEMPLATE_REMOTE_NAME not in res.stdout:
        print(
            f"Adding remote '{TEMPLATE_REMOTE_NAME}' pointing to {TEMPLATE_REPO_URL}..."
        )
        run_command(f"git remote add {TEMPLATE_REMOTE_NAME} {TEMPLATE_REPO_URL}")
    else:
        # Optional: Ensure the URL is correct
        run_command(f"git remote set-url {TEMPLATE_REMOTE_NAME} {TEMPLATE_REPO_URL}")


def handle_conflicts():
    """Interactive loop to handle rebase conflicts."""
    while True:
        print(f"\n{RED}!!! CONFLICTS DETECTED !!!{RESET}")
        print(f"The rebase has stopped because of conflicts.")
        print("-" * 40)
        print(f"1. Open your files/IDE and resolve the conflicts.")
        print(f"2. Add the resolved files using: {GREEN}git add <file>{RESET}")
        print(f"3. Come back here and press 'c'.")
        print("-" * 40)

        choice = (
            input(
                f"Select action: [{GREEN}c{RESET}]ontinue rebase, [{RED}a{RESET}]bort rebase: "
            )
            .lower()
            .strip()
        )

        if choice == "a":
            print(f"{YELLOW}Aborting rebase...{RESET}")
            run_command("git rebase --abort", check=False)
            sys.exit(1)

        elif choice == "c":
            print(f"{YELLOW}Attempting to continue rebase...{RESET}")
            # Try to continue
            result = run_command("git rebase --continue", check=False)

            if result.returncode == 0:
                print(f"{GREEN}Rebase continue successful!{RESET}")
                return  # Exit the conflict loop
            else:
                print(
                    f"{RED}It seems conflicts are not fully resolved or files weren't added.{RESET}"
                )
                # Loop continues
        else:
            print("Invalid input.")


def main():
    print(f"{GREEN}=== Starting Template Rebase Workflow ==={RESET}")

    # 1. Check for uncommitted changes
    check_clean_work_tree()

    # 2. Setup Remote
    setup_remote()

    # 3. Fetch latest changes
    print(f"{YELLOW}Fetching changes from {TEMPLATE_REMOTE_NAME}...{RESET}")
    run_command(f"git fetch {TEMPLATE_REMOTE_NAME}")

    # 4. Start Rebase
    print(
        f"{YELLOW}Starting rebase of current branch onto {TEMPLATE_REMOTE_NAME}/{TEMPLATE_BRANCH}...{RESET}"
    )

    # We use check=False because we expect a non-zero exit code if conflicts occur
    rebase_cmd = f"git rebase {TEMPLATE_REMOTE_NAME}/{TEMPLATE_BRANCH}"
    result = run_command(rebase_cmd, check=False)

    if result.returncode == 0:
        print(
            f"{GREEN}Success! Your repository is now up to date with the template.{RESET}"
        )
    else:
        # 5. Enter Conflict Resolution Mode
        handle_conflicts()
        print(f"{GREEN}Success! Rebase finished.{RESET}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RED}Script interrupted by user.{RESET}")
        sys.exit(1)
