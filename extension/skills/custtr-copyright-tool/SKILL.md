---
name: custtr-copyright-tool
description: "Add or update AMD copyright and disclaimer headers in source files. Handles multiple file types with correct comment syntax. Use when the user says: 'add copyright', 'update copyright', 'add disclaimer', 'update disclaimer', 'copyright header', 'add AMD copyright', or asks to process a folder of files for copyright compliance."
---

# Copyright Disclaimer Adder Skill

## Overview

This skill adds or updates AMD copyright/disclaimer headers in source code files. It:
1. Asks for input directory (or file) and output directory
2. Recursively scans all supported file types
3. Detects whether a copyright header already exists and whether it's current
4. Adds the header (commented correctly for each file type) or updates it if outdated
5. Copies unsupported/binary files as-is to the output directory
6. Produces a summary report of every file processed

---

## Workflow

### Step 1 — Gather inputs

Ask the user for:
- **Input path**: directory (processed recursively) or single file
- **Output path**: where modified files will be written (mirrors the input directory structure)
- **Year override** (optional): defaults to the current year from `$CURRENT_DATE`

If either path is missing, prompt for it. Do NOT proceed until both are provided.

---

### Step 2 — Load the canonical copyright text

The current AMD copyright/disclaimer text is:

```
© 2026 Advanced Micro Devices, Inc. All rights reserved.
DISCLAIMER
The information contained herein is for informational purposes only, and is subject to change 
without notice. While every precaution has been taken in the preparation of this document, it 
may contain technical inaccuracies, omissions and typographical errors, and AMD is under no 
obligation to update or otherwise correct this information.  Advanced Micro Devices, Inc. makes 
no representations or warranties with respect to the accuracy or completeness of the contents of 
this document, and assumes no liability of any kind, including the implied warranties of noninfringement,
merchantability or fitness for particular purposes, with respect to the operation or use of AMD 
hardware, software or other products described herein.  No license, including implied or 
arising by estoppel, to any intellectual property rights is granted by this document.  Terms and 
limitations applicable to the purchase or use of AMD's products are as set forth in a signed agreement 
between the parties or in AMD's Standard Terms and Conditions of Sale. GD-18
```

Replace `2026` with the actual current year when processing.

**Detection keywords** (used to identify an existing copyright block in a file):
- `Advanced Micro Devices`
- `AMD`
- `Xilinx` (legacy — counts as an existing but outdated header needing replacement)
- `© Copyright`
- `Copyright (c)`
- `Copyright ©`

---

### Step 3 — Comment style mapping

Use this table to determine how to wrap the copyright text for each file type. Match by **file extension** (case-insensitive) or exact **filename** for special files.

| Extension / Filename         | Comment prefix   | Example output line                        |
|------------------------------|------------------|--------------------------------------------|
| `.c` `.cpp` `.h` `.v` `.vh` `.sv` `.dtsi` `.java` `.txt` | `//` | `// © 2026 Advanced Micro Devices...`  |
| `.vhd` `.vhdl`               | `--`             | `-- © 2026 Advanced Micro Devices...`     |
| `.tcl` `.py` `.sh` `.bash` `.bat` `.coe` `.xdc` `Makefile` `.csh` | `#`  | `# © 2026 Advanced Micro Devices...` |
| `Readme` `README` (any ext)  | `$`              | `$ © 2026 Advanced Micro Devices...`      |
| `GitKeep`                    | `#`              | `# © 2026 Advanced Micro Devices...`      |

**Files without a matching extension**: skip (copy as-is), log as "Files without Support from the Mapping File".

**Binary files** (`.jar`, `.class`, `.zip`, `.png`, `.jpg`, `.gif`, `.exe`, `.dll`, `.db`, `.vsdx`, `.docx`, `.pptx`, `.snag`): skip (copy as-is), log as "Binary Files".

---

### Step 4 — Build the commented header block

For each file, construct the header as follows:

1. Take each line of the copyright text
2. Prefix every line with the file's comment prefix + a space
3. Add a blank commented line before and after the copyright block as separators
4. For `.bat` files the prefix is `@Rem` (no trailing slash)

**Example for a `.v` (Verilog) file using `//`:**

```verilog
//
// © 2026 Advanced Micro Devices, Inc. All rights reserved.
// DISCLAIMER
// The information contained herein is for informational purposes only, and is subject to change 
// without notice. While every precaution has been taken in the preparation of this document, it 
// may contain technical inaccuracies, omissions and typographical errors, and AMD is under no 
// obligation to update or otherwise correct this information.  Advanced Micro Devices, Inc. makes 
// no representations or warranties with respect to the accuracy or completeness of the contents of 
// this document, and assumes no liability of any kind, including the implied warranties of noninfringement,
// merchantability or fitness for particular purposes, with respect to the operation or use of AMD 
// hardware, software or other products described herein.  No license, including implied or 
// arising by estoppel, to any intellectual property rights is granted by this document.  Terms and 
// limitations applicable to the purchase or use of AMD's products are as set forth in a signed agreement 
// between the parties or in AMD's Standard Terms and Conditions of Sale. GD-18
//
```

**Example for a `.py` (Python) file using `#`:**

```python
#
# © 2026 Advanced Micro Devices, Inc. All rights reserved.
# DISCLAIMER
# The information contained herein is for informational purposes only, and is subject to change 
# without notice. While every precaution has been taken in the preparation of this document, it 
# may contain technical inaccuracies, omissions and typographical errors, and AMD is under no 
# obligation to update or otherwise correct this information.  Advanced Micro Devices, Inc. makes 
# no representations or warranties with respect to the accuracy or completeness of the contents of 
# this document, and assumes no liability of any kind, including the implied warranties of noninfringement,
# merchantability or fitness for particular purposes, with respect to the operation or use of AMD 
# hardware, software or other products described herein.  No license, including implied or 
# arising by estoppel, to any intellectual property rights is granted by this document.  Terms and 
# limitations applicable to the purchase or use of AMD's products are as set forth in a signed agreement 
# between the parties or in AMD's Standard Terms and Conditions of Sale. GD-18
#
```

**Example for a `.vhd` (VHDL) file using `--`:**

```vhdl
--
-- © 2026 Advanced Micro Devices, Inc. All rights reserved.
-- DISCLAIMER
-- ...
--
```

---

### Step 5 — Process each file

For every file discovered:

#### 5a — Classify the file

| Condition | Action | Log Category |
|-----------|--------|--------------|
| Binary file extension | Copy as-is to output | Binary Files |
| Extension not in mapping table | Copy as-is to output | Files without Support from the Mapping File |
| File is read-only (cannot write) | Skip, do not copy | Read-only Files |

#### 5b — Check for existing copyright block

Read the file content (first ~50 lines is usually sufficient). Search for any detection keyword (case-insensitive):

- **No existing header found**: Insert the commented header at the top of the file. Log as "Files Missing Headers" AND "Successfully Processed Files".
- **Existing header found, already current** (contains `Advanced Micro Devices` AND `GD-18` AND current year): Skip. Log as "Files Not Requiring Processing Since the Copyright/Disclaimer are Up-To-Date".
- **Existing header found but outdated** (e.g., `Xilinx`, wrong year, missing `GD-18`): Replace the entire header block with the new one. Log as "Successfully Processed Files".

#### 5c — Special case: shebangs and encoding markers

If the very first line of a file starts with `#!` (shebang) or `# -*- coding` (Python encoding), preserve that line FIRST, then insert the copyright block immediately after.

#### 5d — Write the output file

Write the modified content to the output path, preserving the same relative directory structure as the input.

---

### Step 6 — Generate the summary report

After all files are processed, output a formatted summary. Use this exact format:

```
===> Results for Updating the Copyright and Disclaimer Statements <===

                    {DATE} at {TIME}

  ----- Chronological Activity (Summary Below)...

Processing: {file_path}...{status_message}
...

********************************************************************************
********************************************************************************
**                                                                            **
**                                   Summary                                  **
**                                                                            **
**                             Number of files: {N}                           **
**                                 Time {MM:SS}                               **
**                                                                            **
********************************************************************************
********************************************************************************

   ---------------Successfully Processed Files
       1: {path}
       ...

   ---------------Files Not Requiring Processing Since the Copyright/Disclaimer are Up-To-Date
       1: {path}
       ...

   ---------------Files Missing Headers
       1: {path}
       ...

   ---------------Failed to Process Files for an Unknown Reason

   ---------------Third-Party Files

   ---------------Files w/Existing Disclaimer/Copyright
       1: {path}
       ...

   ---------------Binary Files
       1: {path}
       ...

   ---------------Files without Support from the Mapping File
       1: {path}
       ...

   ---------------Read-only Files

************************************* DONE *************************************
```

Show only sections that have at least one entry (omit empty sections except the main headers). Always show every section header so the user can see what was checked.

---

## Implementation Notes

### Reading and writing files

Use the Bash tool with standard shell commands to:
- Recursively list files: `find "{input_path}" -type f`
- Read file content: `cat "{file_path}"`
- Write file content: use the Write tool (preferred) or `tee`
- Create output directory structure: `mkdir -p "{output_dir}"`
- Check if read-only: `[ -w "{file_path}" ]`

### Detecting header boundaries

When replacing an existing header:
1. Find the first line containing a detection keyword
2. Walk backward to find the start of the comment block (first line whose prefix matches the comment style)
3. Walk forward to find the end of the comment block (last consecutive commented line)
4. Replace that entire range with the new header

### Performance

Process files sequentially. For large directories (>500 files), notify the user of progress every 50 files.

---

## Error Handling

| Error | Behavior |
|-------|----------|
| Input path does not exist | Stop immediately, tell user |
| Output path cannot be created | Stop immediately, tell user |
| File cannot be read | Log as "Failed to Process Files for an Unknown Reason" |
| File is binary/encoding issue | Classify as Binary, copy as-is |

---

## Example Session

```
User: Add AMD copyright to all source files in C:/training/lab_files, output to C:/training/lab_files_updated
```

Claude responds:
1. Confirms input = `C:/training/lab_files`, output = `C:/training/lab_files_updated`
2. Scans recursively, processes each supported file
3. Outputs live processing log lines as it works
4. Prints the full summary report at the end
```
