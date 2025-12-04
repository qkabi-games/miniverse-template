#!/usr/bin/env python3

import os
import sys


def to_pascal_case(snake_str):
    return "".join(x.title() for x in snake_str.split("_"))


def replace_in_file(file_path, replacements):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        new_content = content
        for old, new in replacements.items():
            new_content = new_content.replace(old, new)

        if new_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated content in: {file_path}")

    except UnicodeDecodeError:
        print(f"Skipped binary file: {file_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")


def rename_fs_item(root, name, replacements):
    new_name = name
    for old, new in replacements.items():
        new_name = new_name.replace(old, new)

    if new_name != name:
        old_path = os.path.join(root, name)
        new_path = os.path.join(root, new_name)
        try:
            os.rename(old_path, new_path)
            print(f"Renamed: {name} -> {new_name}")
        except OSError as e:
            print(f"Error renaming {name}: {e}")


def main():
    print("--- Rename Miniverse project template ---")
    print(
        "This script will replace '__project__' and '__Project__' in filenames, folders, and content."
    )

    project_name = input(
        "Enter the new project name in snake_case (e.g., my_game): "
    ).strip()

    if not project_name:
        print("Error: No project name entered.")
        return

    pascal_name = to_pascal_case(project_name)

    print(f"\nConfiguration:")
    print(f"  '__project__' -> '{project_name}'")
    print(f"  '__Project__' -> '{pascal_name}'")

    confirm = input("\nProceed with renaming? (y/n): ").lower()
    if confirm != "y":
        print("Operation cancelled.")
        return

    replacements = {"__project__": project_name, "__Project__": pascal_name}
    script_name = os.path.basename(__file__)
    for root, dirs, files in os.walk(".", topdown=False):
        if ".git" in root.split(os.sep):
            continue

        for filename in files:
            if filename == script_name:
                continue

            file_path = os.path.join(root, filename)
            replace_in_file(file_path, replacements)
            rename_fs_item(root, filename, replacements)

        for dirname in dirs:
            if dirname == ".git":
                continue
            rename_fs_item(root, dirname, replacements)

    print("\n--- Renaming Complete ---")

    delete_script = input(
        "Do you want to delete this rename script now? (y/n): "
    ).lower()
    if delete_script == "y":
        try:
            os.remove(__file__)
            print("Script deleted.")
        except Exception as e:
            print(f"Could not delete script: {e}")


if __name__ == "__main__":
    main()
