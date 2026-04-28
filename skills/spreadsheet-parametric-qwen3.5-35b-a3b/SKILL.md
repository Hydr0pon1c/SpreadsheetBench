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
