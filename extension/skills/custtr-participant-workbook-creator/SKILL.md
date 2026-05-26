Here are the steps this skill executes:

Collect inputs — gather the folder path, confirm file order, extract section names from slide 1 of each module, get header text and output filename from the user.

Trim slides — remove the last 2 slides from every module except the last one (in-place, modifies source files).

Merge — combine all modules into a single .pptx using the pptx-merger script, preserving masters, layouts, and media from each source file.

Add sections — inject PowerPoint section markers into the merged deck, one per module, mapped to the correct slide ranges.

Export notes PDF — use PowerPoint COM automation to export the merged deck as a notes-page PDF (one page per slide, with speaker notes below each slide image). Falls back to the MCP pptx_to_pdf tool if COM is blocked.

Stamp header + inject bookmarks — make a single pass over the PDF to (a) stamp the header text at the top of every page via reportlab, and (b) add named bookmarks pointing to the first page of each section using proportional page mapping.

Verify — check slide count, section count, section names and ranges, PDF existence, page count, bookmark count, and bookmark page numbers, and report pass/fail for each.
