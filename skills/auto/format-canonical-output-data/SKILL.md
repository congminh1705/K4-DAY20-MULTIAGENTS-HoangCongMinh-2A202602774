---
name: format-canonical-output-data
description: Use when exporting structured data or generating JSON/CSV files to ensure precise schema compliance, canonical names, and unit formatting.
---
1. **Money representation**: Always output monetary values in integer cents (e.g., multiply decimal amounts by 100) unless explicitly instructed otherwise.
2. **Canonical naming**: Normalize string identifiers and categories (such as region names or service identifiers) to their exact canonical spelling or format (e.g., lower-case with hyphens replaced by underscores).
3. **Metadata inclusion**: When required, populate metadata objects (like `meta`) accurately with source filenames, total input rows including duplicates, and processed valid rows.
4. **Schema verification**: Double-check all output keys, headers, types, and top-level schema properties against instructions before finalizing files.
