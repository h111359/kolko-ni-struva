#!/usr/bin/env python3
import sys
import os
import shutil
from datetime import datetime

TEMPLATE_PATH = ".rdd-docs/templates/task.md"
TASKS_DIR = ".rdd-docs/tasks"


def generate_task_id():
    # This function is now unused, but kept for backward compatibility
    return "t-" + datetime.now().strftime("%Y%m%d-%H%M")


def create_standalone_task(task_name, requirements, technical_details):
    # This function is now updated to require task_id as parameter
    raise NotImplementedError("Use create_standalone_task_with_time instead.")

def create_standalone_task_with_time(task_id, task_name, requirements, technical_details):
    if not os.path.exists(TASKS_DIR):
        os.makedirs(TASKS_DIR)
    target_file = os.path.join(TASKS_DIR, f"{task_id}.task.md")
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("<task-name>", task_name)
    content = content.replace("<requirements>", requirements)
    content = content.replace("<technical-details>", technical_details)
    content = content.replace("<task-id>", task_id)
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Task created: {target_file}")
    return task_id


def add_implementation_log_entry(task_id, log_entry):
    task_file = os.path.join(TASKS_DIR, f"{task_id}.task.md")
    if not os.path.exists(task_file):
        print(f"Task file not found: {task_file}")
        sys.exit(1)
    with open(task_file, "r", encoding="utf-8") as f:
        content = f.read()
    if "<implementation-log-end>" in content:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_block = f"[{timestamp}] {log_entry}\n---\n\n"
        content = content.replace("<implementation-log-end>", log_block + "<implementation-log-end>", 1)
    else:
        print("<implementation-log-end> placeholder not found.")
        sys.exit(1)
    with open(task_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Log entry added to: {task_file}")


def print_usage():
    print("Usage:")
    print("  task.py create --time YYYYMMDD-HHmm --task-name NAME --requirements REQ --technical-details DETAILS")
    print("  task.py log --task-id ID --log-entry ENTRY")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    mode = sys.argv[1]
    if mode == "create":
        args = sys.argv[2:]
        try:
            time_idx = args.index("--time")
            tn_idx = args.index("--task-name")
            rq_idx = args.index("--requirements")
            td_idx = args.index("--technical-details")
        except ValueError:
            print_usage()
            sys.exit(1)
        time_str = args[time_idx + 1]
        # Validate time format
        try:
            datetime.strptime(time_str, "%Y%m%d-%H%M")
        except ValueError:
            print("Invalid time format. Use YYYYMMDD-HHmm.")
            sys.exit(1)
        task_id = f"t-{time_str}"
        task_name = args[tn_idx + 1]
        requirements = args[rq_idx + 1]
        technical_details = args[td_idx + 1]
        create_standalone_task_with_time(task_id, task_name, requirements, technical_details)
    elif mode == "log":
        args = sys.argv[2:]
        try:
            id_idx = args.index("--task-id")
            le_idx = args.index("--log-entry")
        except ValueError:
            print_usage()
            sys.exit(1)
        task_id = args[id_idx + 1]
        log_entry = args[le_idx + 1]
        add_implementation_log_entry(task_id, log_entry)
    else:
        print_usage()
        sys.exit(1)

if __name__ == "__main__":
    main()
