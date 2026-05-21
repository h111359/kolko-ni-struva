## UAT Scenarios

### UAT-01: Report 1 Sofia selection is unambiguous and complete
Open the React app, navigate to "Цени по категория", and inspect the settlement selector for София on the latest available date after the fix is applied and data is refreshed. Select the Sofia option and confirm the resulting chart reflects the full category set expected from the corrected local/raw verification rather than the historical 2-category slice.

Expected result: the user can identify the correct Sofia choice without ambiguity, and the rendered category list/count matches the corrected analytical dataset.