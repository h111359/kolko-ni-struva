# Role:

You are here to create a new Task.

# Context:

C01: This prompt leverages GitHub Copilot to create a new Task file using the automation in `task.py`, capturing business requirements, and initializing a task record with timestamped naming.

C02: The file name of the task should follow the format `t-<timestamp>-<task-name>.task.md`, where `<timestamp>` is the current local time in `YYYYMMDD-HHmm` format, and `<task-name>` is a sanitized, hyphen-separated version of the user-provided short task name.

# Rules:

R01: Do NOT include implementation or technical details in the requirements section.

R02: Always use the script `.github/scripts/task.py` for task creation.

R03: The initial Task state must be `draft`.

R04: Requirements must be expressed from the requestor perspective (problem, motivation, business value, constraints) before clarification loop begins.

R05: Follow the Instructions section step-by-step without skipping any part.

# Steps:

S01: Display the following banner to the user:

```
─── RDD-COPILOT ───
 Prompt: Task Create  
 Description: 
 > Create a new Task capturing only 
 > business / functional requirements (problem, value,
 > constraints, acceptance criteria) and initialize draft
 > file using timestamped naming.

 User Action: 
 > Provide short task name & initial requirement details;
───────────────
```

S02: Ask the user to provide a short name of the task. Sanitize the name to create a concise, hyphen-separated summary (lowercase, remove unsupported characters, collapse spaces to single hyphen). Ensure the name is no longer than 30 characters after sanitization; if too long, request a shorter phrase. Remember this name as task name for use in the Task filename.

S03: Ask the user to answer the question "Provide the requirements?" Save the answer as `<requirements>`.

S04: Ask the user to answer the question "Provide the technical details?" Save the answer as `<technical-details>`.

S05: Check if the current folder is a git repository. If not, initialize a git repository and set the default branch to `main`.

S06: Get the current local time using `.github/scripts/get-local-time.py` and store it for use in the task filename timestamp.

S05: Create a new Git branch using the sanitized task name from S02 and the time stamp from S06. The name of the branch should be `task/<task-name>-<timestamp>`. Use `git checkout -b task/<task-name>-<timestamp>` where `<task-name>` is the sanitized name and `<timestamp>` is the local time found in S06. This ensures task work is isolated on a dedicated branch.

S05: Use `.github/scripts/task.py create --task-name <task-name> --requirements <requirements> --technical-details <technical-details> --timestamp <timestamp>` to create the new task file. Populate:
   - `<task-name>`: sanitized name from S02
   - `<requirements>`: answers from S03, formatted as a requirements block
   - `<technical-details>`: answers from S04, formatted as a technical details block
   - `<timestamp>`: local time from S04

S06: Confirm task creation and display the path to the new task file.

