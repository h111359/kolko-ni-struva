---
mode: "agent"
description: "Plan for a coding implementation for an AI coding assistant to follow."
---

Your goal is to generate an coding implementation plan for an AI coding assistant to follow.
Create this plan in a new markdown plan.md file in a new folder `/docs/changes/YYYYMMDD-<requirement_name>`, for the requirement provided to you. You can decide on the appropriate requirement name.
For example, if the today's date is 2025-08-22 and the requirement name is "Implement User Authentication", the file should be created as `/docs/changes/20250822-user_authentication/plan.md`.

## RULES:

- Keep implementations simple, do not over architect
- Do not generate real code for your plan, pseudocode is OK
- For each step in your plan, include the objective of the step, the steps to achieve that objective, and any necessary pseudocode.
- Call out any necessary user intervention required for each step
- Consider accessibility part of each step and not a separate step

## Steps to Follow

### 1. FIRST

- Review the file docs/file-structure.md to understand the file structure. Then read the files which contain requirements and objectives.


### 2. THEN

- Create a detailed implementation plan that outlines the steps needed to achieve the objectives of the specification document.
- The plan should be structured, clear, and easy to follow.

- Add a frontmatter to the implementation plan

```markdown
---
description: "Implementation plan for <requirement>"
created-date: YYYY-MM-DD
---

# Implementation Plan for [Spec Name]

## OBJECTIVE

OBJECTIVE/REQUIREMENT/TASK HERE

PLAN HERE
```

- Always add validation steps in your plan to ensure the implementation meets the requirements.
- Structure your plan as follows, and output as Markdown code block

```markdown
## IMPLEMENTATION PLAN

- [ ] Step 1: [Brief title]
  - **Task**: [Detailed explanation of what needs to be implemented]
  - **Files**: [Maximum of 20 files, ideally less]
    - `path/to/file1.ts`: [Description of changes], [Pseudocode for implementation]
  - **Dependencies**: [Dependencies for step]
  - **Additional Instructions**:
    - Before proceeding with this step, check the conversation history and see if you already completed this step.
    - You do not need to follow this step strictly, consider the output of the previous step and adjust this step as needed.
    - If you are fixing issues that arise from automated tests, ALWAYS take a step back before fixing things, consider that the test script itself might be wrong and that's the one that you should fix. Sometimes the best way to fix a script is to understand the intent of the test script and simplify it.
    - If you are running the app, follow [npm-run-instructions](/.github/prompt-snippets/npm-run-instructions.md)
    - If you are running any CLI command, follow [cli-execution-instructions](/.github/prompt-snippets/cli-execution-instructions.md)
    - If you are using Supabase CLI, follow [supabase-cli-instructions](/.github/prompt-snippets/supabase-cli-instructions.md)
    - If you are using Playwright MCP, follow [playwright-mcp-instructions](/.github/prompt-snippets/playwright-mcp-instructions.md)
    - When you are done with this step, mark this step as complete and add a note/summary of what you did (in the plan document) before proceeding to the next step.
    - If you decide to proceed to the next step even if there are remaining issues/errors/failed tests, make a note of the issues (by updating the plan document) and address them in subsequent steps.

[Additional steps...]
```

- After the steps to implement the objective, add a step to run the app and test it against the original objective specified in the plan. Use the right tool to test this (playwright MCP, CLI, or something else).
- Add a step to write unit tests for what has been implemented. **IMPORTANT**: Take note of the [dual-testing-strategy](/docs/dual-strategy-testing.md). After testing, set the environment variable back to not using mocks.
- Add a step to write playwright UI tests for the feature, keep the test simple and focused on the intent of the objective. Avoid hardcoding dynamic data that comes from the database, REMEMBER that the data are dynamic and changing.
- Add a step to make sure it complies with our [definition_of_done](/docs/specs/definition_of_done.md)

### 3. NEXT:

- Validate and self-review your plan to ensure it meets the requirements and is ready for implementation.
- Iterate with me until I am satisifed with the plan

### 4. FINALLY:

- Make sure the plan document ends with a new line (for markdown linting compliance).
- DO NOT start implementation without my permission.