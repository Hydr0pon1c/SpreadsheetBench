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

### Hybrid Tool Selection Strategy

- Lesson: Use pandas for bulk data aggregation/logic; switch to openpyxl for writing, formulas, or structural modifications requiring formatting preservation

- Generalization: Leverage pandas efficiency for calculations but rely on openpyxl Workbook objects when preserving formulas, styles, merged cells, or exact cell positioning

### Workbook Isolation Protocol

- Lesson: Copy source workbook to output path before modifications to preserve original file integrity

- Generalization: Always write changes to isolated output copy rather than modifying source directly

### Reverse-Order Batch Deletion

- Lesson: When deleting multiple rows/columns, collect indices first, sort descending, process from highest to lowest

- Generalization: Buffer modification requests and execute bottom-up to prevent index shifting errors during structural operations

### Formula Storage Pattern

- Lesson: Assign Excel formulas as strings starting with '=' via cell.value assignment using openpyxl

- Generalization: Never use pandas.to_excel() for formula workbooks; direct string assignment preserves editable formula syntax

### Pre-Modification Inspection

- Lesson: Query workbook metadata (sheet names, dimensions, headers, data types) before implementing transformations

- Generalization: Diagnostic exploration reveals actual data boundaries, missing sheets, edge cases like formulas or mixed types before coding

### Post-Save Verification Protocol

- Lesson: Reload saved file immediately after writing to confirm data integrity, formulas, and structural changes persisted correctly

- Generalization: Never assume write operations succeeded; independent read-back validation confirms critical cells match expectations
