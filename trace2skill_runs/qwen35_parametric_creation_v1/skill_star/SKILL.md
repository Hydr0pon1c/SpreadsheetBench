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

### Pure Code Submission Protocol

- Lesson: Execution parameters must contain only valid programming syntax without embedded tool markers, XML tags, or markdown artifacts.

- Generalization: Validate payloads for invisible characters or control syntax before submission to prevent parser failures.

### Formula vs. Static Value Recognition

- Lesson: Explicit requests for formulas require Excel-formatted strings ('=...'); compute results only if static values are requested or environment lacks calculation engines.

- Generalization: Check task intent keywords to distinguish between writing formula logic or pre-calculated results.

### Library-Specific Data Integrity

- Lesson: OpenPyXL preserves formatting and formulas; Pandas loses styling and does not evaluate formulas. Align library choice with task requirements.

- Generalization: Select data processing tools based on structural preservation needs rather than convenience alone.

### Indexing & Row Manipulation Safety

- Lesson: Account for indexing offsets between libraries (0-based pandas vs. 1-based openpyxl) and iterate backwards when deleting rows to avoid index shifting.

- Generalization: Standardize coordinate systems before operations and modify data structures from end to start.

### Output Compliance & Scope Verification

- Lesson: Verify target ranges match instructions exactly, including column letters and row numbers. Distinguish illustrative examples from actual working ranges.

- Generalization: Parse specification constraints literally to prevent off-target modifications or scope creep.
