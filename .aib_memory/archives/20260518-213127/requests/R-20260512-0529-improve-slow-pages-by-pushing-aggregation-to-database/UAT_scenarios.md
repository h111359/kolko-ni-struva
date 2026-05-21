## UAT Scenarios

- UAT-01 — Report 1 responsiveness: Open the React app, select each available date, then select at least one high-volume settlement on `Цени по категория`. Expected result: the chart loads perceptibly faster than before the refactor and still shows the full expected category set for the chosen settlement.

- UAT-02 — Report 2 interactive filtering: Open `Продукти по населено място и категория`, change settlement and category filters several times, and inspect at least one record-detail modal. Expected result: filter updates feel responsive, returned rows remain correct for the chosen filters, and modal data still matches the selected row.

- UAT-03 — Report 3 large-category behavior: Open `Населени места и продукти по категория` for a historically large category and compare the post-change behavior to the previous experience. Expected result: the page no longer relies on an opaque browser-safety cap as its primary behavior, and any remaining pagination or scoping is explicit and understandable.
