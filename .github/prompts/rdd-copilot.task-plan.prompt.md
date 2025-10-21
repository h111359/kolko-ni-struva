# Role:

You are here to plan a Task.

# Context:

C01: This prompt leverages GitHub Copilot to guide the planning of a Task file, focusing on actionable steps, deliverables, and milestones based on business requirements.

C02: The plan should be documented in a file named `t-<timestamp>-<task-name>.plan.md`, where `<timestamp>` is date and time in `YYYYMMDD-HHmm` format, and `<task-name>` is the task name. These should be found from the active git branch, which should follow the format `task/<timestamp>-<task-name>`.

# Rules:

R01: Do NOT include implementation or technical details in the planning section.

R02: Always use the script `.github/scripts/task.py` for plan creation.

R04: Follow the Instructions section step-by-step without skipping any part.

# Steps:

S01: Display the following banner to the user:

```
─── RDD-COPILOT ───
 Prompt: Task Plan  
 Description: 
 > Plan a Task according to the provided requirements.
 > Document the plan using timestamped naming.

 User Action: 
 > Answer to questions if any.
───────────────
```

S02: Find the current active git branch name. Extract the task name and the timestampt from the branch name.

S03: Generate a plan for fulfilling the requirements. The plan should be very detailed with exact names of files and folders changed. Keep the text of the plan as `<planning-details>`. In case of any ambiguities or missing information, ask clarifying questions to the user before proceeding. But before asking, re-check the requirements in the file .rdd-docs/requirements.md to ensure the information is indeed missing. Also read the file .rdd-docs/technical-specification to get more technical context about the task.

S06: Get the current local time using `.github/scripts/get-local-time.py` and store it for use in the next steps.

S08: Use `.github/scripts/task.py plan --timestamp <timestamp> --task-name <task-name> --planning-details <planning-details>` to create the new plan file. Populate:
   - `<task-name>`: sanitized name from S02
   - `<planning-details>`: answers from S03
   - `<timestamp>`: local time from S06

S09: Confirm plan creation and display the path to the new plan file.