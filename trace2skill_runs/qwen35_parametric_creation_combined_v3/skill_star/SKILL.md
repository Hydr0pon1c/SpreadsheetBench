# Spreadsheet Manipulation Guidelines

## Objective
Modify `.xlsx` files accurately using Python while preserving data integrity, formulas, and formatting.

## Core Tools
- **pandas**: Primary engine for data loading, logic, calculations, and bulk transformations.
- **openpyxl**: Essential for accessing cell styles, preserving formulas, managing merged cells, and writing back to `.xlsx` specifically.

## Operational Procedures

### 1. Task Interpretation
- Confirm target sheets, rows, and columns from instructions before execution.
- Differentiate between manipulating *data values* vs. *formula references*.
- Identify dependencies: Does this change affect downstream calculated fields?

### 2. Reading Workbooks
- Load entire workbook or specific sheets based on scope.
- Verify schema: check headers, data types (dates, numbers), and delimiters.
- Detect edge cases: empty headers, trailing rows, or mixed data types in columns.
- **Warning:** `pandas.read_excel()` converts formulas to static values. Use `openpyxl` if formulas must be retained during load.

### 3. Editing Cells & Ranges
- Prefer named indexes or explicit column headers over hardcoded integer positions.
- Ensure row alignment remains intact; do not drop or duplicate rows unintentionally.
- Handle missing values (NaN) deterministically: fill, omit, or set to blank as required.
- Maintain existing sheet order unless reorganization is specified.

### 4. Handling Formulas
- **Preservation:** When updating a single value, ensure referenced formulas are recalculated or remain valid.
- **Modification:** Never replace a formula string with a pre-calculated value unless explicitly instructed.
- **Syntax:** New formulas written via `openpyxl` must use standard Excel notation (e.g., `=A1+B1`).
- **Circular Refs:** Avoid creating circular dependencies during logic implementation.

### 5. Preserving Formatting
- **Styles Lost:** `pandas.to_excel` does not retain fonts, colors, borders, or number formats.
- **Strategy:** If formatting matters, load into `openpyxl`, apply changes to `Workbook` objects, then save.
- **Merged Cells:** Use `worksheet.merge_cells()` to restore or maintain merges.

### 6. Validation & Output
- **Sanity Check:** Verify row count matches expected delta.
- **Data Integrity:** Spot-check critical cells to ensure updates applied correctly.
- **Safety:** Always write to a temporary filename first. Rename to final destination only after verification.
- **Cleanup:** Close workbook handles and release memory resources properly using context managers.

## Trace-Derived Lessons

### Clean Code Submission Protocol

- Lesson: Executable payloads must contain only valid Python syntax without embedded tool markers, XML tags, or markdown wrappers.

- Generalization: Line-1 SyntaxErrors indicate formatting contamination rather than logic issues; strip non-code artifacts before transmission.

### Tool Selection Heuristic

- Lesson: Use openpyxl for formula retention, formatting preservation, and structural modifications; use pandas for bulk data analysis where formats/formulas are irrelevant.

- Generalization: Match library to preservation requirements: formulas/styles/structure → openpyxl, pure computation → pandas.

### Dynamic Formula Construction

- Lesson: Write Excel formulas as strings with exactly one leading '=' to cell.formula or cell.value; do not pre-compute in Python when dynamic recalculation is required.

- Generalization: Keyword triggers ('formula', 'calculate') signal formula-string assignment; validate syntax including reference quoting for sheet names with spaces.

### Structural Modification Safety

- Lesson: Process row/column deletions in descending order after collecting all target indices to prevent index shifting during sequential removals.

- Generalization: Buffer targets before batch operations; identify all modifications before altering document state.

### Cross-Library Index Alignment

- Lesson: Pandas uses 0-based indexing (excluding header); openpyxl uses 1-based (including header). Apply +2 offset when converting DataFrame rows to Excel coordinates.

- Generalization: Document and consistently apply index conversions at every cross-tool access point to prevent off-by-one errors.

### Comprehensive Verification Workflow

- Lesson: Pre-scan workbook metadata, post-save reload via fresh instance, and spot-check critical cells for both content and formatting persistence.

- Generalization: Verify against saved file rather than in-memory object; log transformation metrics against expectations to detect scope errors early.
