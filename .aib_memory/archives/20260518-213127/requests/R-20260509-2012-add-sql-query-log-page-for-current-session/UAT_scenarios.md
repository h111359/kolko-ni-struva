## UAT Scenarios

- UAT-01 — Session capture across pages: Start the React app, navigate through the existing report pages, then open the query-log page. Confirm that the page lists startup queries and the later report-triggered queries from the same session in a readable order.

- UAT-02 — Debugging usefulness of entry details: Trigger at least one dimension load and one report query, then verify that the query-log page shows enough detail to understand which Supabase table or RPC was hit, from which app surface, with what timing and result state.

- UAT-03 — Empty-state clarity: Open the app in a fresh session where no post-startup report interactions have been made and verify that the query-log page communicates the current state clearly rather than appearing broken or blank.