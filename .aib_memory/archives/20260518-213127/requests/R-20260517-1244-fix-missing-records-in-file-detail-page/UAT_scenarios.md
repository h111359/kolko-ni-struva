# UAT Scenarios — R-20260517-1244

## UAT-01: Re-loading the same file (idempotency)

**Type:** Manual — requires live browser interaction with the deployed React app.

**Precondition:** A file with more than 1 000 records is visible in the Файлове page for the currently selected date (D).

**Steps:**
1. Open the Файлове page in the React app.
2. Note the "Записи" count shown in the file summary table for any large file (e.g., one showing 3 000+ records).
3. Click the file row to open `FileRowsPanel`.
4. Verify that the total row count displayed in `FileRowsPanel` matches the count from the summary table.
5. Use the "Назад" (Back) button to return to the summary table.
6. Click the same file row again.
7. Verify that `FileRowsPanel` reloads and displays the same correct row count as in step 4.

**Expected outcome:** Row count shown in `FileRowsPanel` equals the count from the summary table on both the first and the second load. No stale data from the previous load is visible.

**Pass/fail:** Fail if the panel shows fewer rows than the summary count, or if stale rows from a previous file load appear.
