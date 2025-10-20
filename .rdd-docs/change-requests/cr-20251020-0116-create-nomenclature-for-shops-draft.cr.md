# 1. Header

cr-id = 20251020-0116
cr-name = create-nomenclature-for-shops

# 2. Who is the requester?
Hristo Hristov, Developer, --

# 3. What is needed?
To be created a nomenclature shops-nomenclature.json where during the merge to be updated the list with shops and the data.csv file to refer to it by ID, so the name of the shop to be excluded from data.csv

# 4. Why is this change needed?
To be reduced the size of data.csv

# 5. Acceptance Criteria
> List the conditions that must be met for the change to be considered completed and successful.

# 6. Additional Considerations
1. When update-kolko-ni-struva.py is executed, on each file red from download to be updated the nomenclature shops-nomenclature.json in data/ folder; 2. The structure of data.csv to be changed and the name of the shop to be replaced by the ID from the nomenclature shops-nomenclature.json; 3. html and java script files to be changed so to correctly read from the new data schema; 4. No changes to other algorithms, settings and styles.

# 7. Technical proposal
> Here should be entered the result of `rdd-copilot.cr-design.prompt.md` technical proposal.

# 8. Implementation plan
> Here should be entered the result of `rdd-copilot.cr-design.prompt.md` generated detail implementation plan.

# 9. Implementation

> Here during the implementation phase will be recorded the additional instructions from the user
