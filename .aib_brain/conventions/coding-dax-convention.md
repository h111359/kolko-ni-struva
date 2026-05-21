# Coding DAX Convention

**Scope:** Normative  
**Applies to:** All DAX formula files and DAX measure definitions (`.dax`) created or edited by the AI Automation Agent during any `implement` workflow run, as well as DAX embedded in Power BI report definitions.  
**Extends:** `coding-general-convention.md` — all rules defined there MUST be applied in addition to the rules below.

---

## 1. Purpose

This convention defines DAX-specific commenting and code-quality rules to ensure that AI-generated DAX measures, calculated columns, and tables are legible, maintainable, and self-documenting in Power BI / SSAS Tabular environments.

---

## 2. Scope & Normative Language

This convention applies to:

- All standalone DAX formula files (`.dax`) created or modified by the AI Automation Agent.
- DAX measure definitions embedded in tabular model definitions or Power BI Desktop files when generated as text.

Out of scope:
- Power Query (M language) formulas — apply Python or SQL conventions as closest analogue when generating M code.

Normative keywords **MUST**, **MUST NOT**, **SHALL**, **SHOULD**, and **MAY** are interpreted per BCP 14 (RFC 2119 / RFC 8174).

---

## 3. File-Level Header

Every standalone DAX file MUST begin with a block comment header.

DAX does not have a native multi-line comment syntax; therefore, the header MUST be written as a series of `//` line comments.

The header MUST contain:

- The file or measure name.
- A one-sentence description of the file's purpose or the measure's business meaning.
- The table or model context in which the measure is used.

Example:

```dax
// Sales YTD.dax
// Purpose: Year-to-date sales amount calculated against the fiscal calendar.
// Context: Sales table, Date table (fiscal calendar relationship).
```

---

## 4. Measure-Level Description Comment

Every DAX measure MUST be preceded by a comment block that describes:

- The business meaning of the measure (what business question it answers).
- The calculation logic at a high level (not a line-by-line restatement).
- Any filter context modifications (e.g., use of CALCULATE, ALL, REMOVEFILTERS).

Example:

```dax
// Sales Amount YTD
// Business meaning: Total sales revenue from the start of the fiscal year to the selected date.
// Logic: Uses DATESYTD over the fiscal year end date (June 30) with a CALCULATE modifier.
Sales Amount YTD =
CALCULATE(
    [Sales Amount],
    DATESYTD('Date'[Date], "6/30")
)
```

---

## 5. Inline Comments for Complex Logic

Inline `//` comments MUST be placed on the line above any DAX function whose behavior is non-obvious (e.g., `USERELATIONSHIP`, `CROSSFILTER`, `TREATAS`, `RANKX`, `TOPN`).

The comment MUST explain why the function is needed, not just what it does.

---

## 6. Constants and Variables (VAR)

Every `VAR` declaration MUST be accompanied by an inline `//` comment that explains what value the variable holds and why it is isolated as a variable.

Example:

```dax
// Calendar days elapsed since fiscal year start
VAR FiscalYearStart = DATE(YEAR(TODAY()) - 1, 7, 1)
RETURN
    DATEDIFF(FiscalYearStart, TODAY(), DAY)
```

---

## 7. Naming Conventions

- Measure names MUST be descriptive noun phrases in Title Case.
- Calculated column names MUST clearly indicate the column's content.
- Variable names within DAX expressions MUST be in PascalCase and describe the value they hold.
- PROHIBITED: single-letter variable names (e.g., `VAR x`), abbreviations that are not universally understood in the business domain.

---

## 8. Code Quality Rules

- CALCULATE filters MUST be commented when using context-transition or multiple filter arguments.
- Empty RETURN statements or measures that always return BLANK() without a comment explaining why are PROHIBITED.
- Measures that depend on another measure MUST reference the dependency explicitly in their description comment.
