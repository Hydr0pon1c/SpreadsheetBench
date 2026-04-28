# Spreadsheet Manipulation Skill Guide

## 1. Task Analysis
- **Clarify Scope**: Identify the target sheet name, specific cell ranges, and required operations (read, append, overwrite, delete) before coding.
- **File Integrity**: Confirm the file path exists and permissions allow read/write access. Never modify the source file in-place; save changes to a new filename unless specified otherwise.

## 2. Library Selection & Loading
- **Data Processing**: Use `pandas` for heavy data transformation, aggregation, or filtering.
- **Structure & Formatting**: Use `openpyxl` for tasks requiring style preservation, complex layouts, charts, or formula manipulation.
- **Mixed Usage**: If using both, load from Excel into `pandas` for processing, then write back using `openpyxl` to retain non-data elements where possible.
- **Sheet Inspection**: Always list available sheet names programmatically (`wb.sheetnames`) before attempting access.

## 3. Editing & Writing
- **Addressing**: Use standard A1 notation (e.g., `cell['A1']`) for precise updates. Use `iter_rows()` or `iter_cols()` for range iterations.
- **Formulas**: Write formulas as raw strings (e.g., `'=SUM(A1:A10)'`) rather than evaluated values unless explicitly requested. Do not remove existing formulas unless overwriting logic.
- **Data Types**: Respect native Excel data types (dates, numbers, booleans). Avoid forcing all data to string format.
- **Styles**: When applying new data, inherit existing column widths and row heights. Apply basic styles (bold header, currency format) only when necessary for readability.

## 4. Preservation Rules
- **Hidden Content**: Do not unhide rows/columns or reveal hidden sheets unless explicitly instructed.
- **Merged Cells**: Minimize merging or unmerging cells as it disrupts grid alignment.
- **Backup**: Always ensure the original workbook remains untouched by creating a copy before execution.

## 5. Validation & Output
- **Row/Col Counts**: Verify the output matches expected dimensions after manipulation.
- **Formula Check**: Spot-check formula cells to ensure they reference correct ranges post-move.
- **File Health**: Open the generated file in a viewer to confirm no corruption or missing styles occurred.
- **Logging**: Report success status, rows affected, and any skipped entries (e.g., due to duplicates or errors) in the final response.

## Trace-Derived Lessons

### Dynamic Formula Construction

- Lesson: Generate unique formula strings per target cell using template interpolation rather than reusing static formulas; always prefix with '=' and validate Excel syntax.

- Generalization: Use f-strings to embed current row/column indices; avoid extraneous operators in formula strings; lock absolute references ($A$1) while keeping keys relative.

### Explicit Range Specification

- Lesson: Determine actual data boundaries programmatically and use bounded ranges instead of entire-column references.

- Generalization: Query max_row/max_column; exclude headers; prevent performance issues and calculation errors from empty cells.

### Structural Discovery Protocol

- Lesson: Inspect workbook structure before implementing changes to validate assumptions about layout, headers, and data types.

- Generalization: Check wb.sheetnames, detect headers via content scan, verify sheet existence, query merged cell ranges.

### File Integrity Protection

- Lesson: Never overwrite original workbooks; save all modifications to distinct output paths with created directories.

- Generalization: Create backups before editing; use os.makedirs(exist_ok=True); preserve source files for recovery.

### Multi-Stage Verification

- Lesson: Validate at three checkpoints: pre-modification state, post-modification content, and post-save persistence.

- Generalization: Reload saved workbooks; read computed VALUES not formula strings; spot-check edge cases and typical rows.

### Index Management Consistency

- Lesson: Account for offset between Excel 1-based indexing and Python/pandas 0-based indexing when mapping rows.

- Generalization: Document mappings explicitly; validate bounds before iteration; adjust for header row offsets.
