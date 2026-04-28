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
