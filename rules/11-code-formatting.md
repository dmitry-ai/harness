---
trigger: always_on
description: "Unified code formatting standards and dispatch to format-specific specifications"
---
# Code Formatting
## CODE-1
Never add unrequested or explanatory comments of your own in code.  
Never delete or alter existing comments already present in the code ([FILE-1](01-file-boundaries.md#file-1)).  
Never write completely blank lines in source code or structured markup and configuration files.  
Always indent new code with tab characters (`\t`) instead of spaces whenever the language or format syntax permits (`indent_style = tab`, `indent_size = 4`).  
Never change the existing indentation of pre-existing code lines outside the scope of your edit.  
Allow at most one single return point per function or method.  
Name the variable storing the future return value of a function `r` (`$r` in PHP); omit that variable whenever `return <expression>` directly suffices.  
In comparisons between a variable and a constant or literal, always place the constant on the left whenever language syntax permits (Yoda comparisons, e.g., `'Enter' === e.key`, `null === $v`, `None is x`, `200 != status`).  
In `if` / `else` branching, always place the shorter conditional block (fewer lines of code) above the longer block: if `BLOCK_1` has more lines (`C1 > C2`) than `BLOCK_2`, invert the condition and move `BLOCK_1` into `else`.  
Never create an empty `if` or `else` block when `C1 = 0` or `C2 = 0`; in brace-delimited languages, place `else` on a new line after `}` (`}\nelse {`).  
Enclose string literals in single quotes (`'...'`) by default whenever language syntax permits; use double quotes (`"..."`) only when they provide a concrete advantage (such as variable interpolation in Bash or PHP, escape sequences, avoiding escaped apostrophes, or strict format requirements such as JSON).  
Maintain alphabetical order for functions and methods at the same visibility and scope level, inserting any newly added function in its alphabetical position; also keep imports, constants, XML/HTML attributes, CLI options, and non-ordered maps alphabetically ordered where semantics do not dictate another order.  
When modifying existing user code, never rewrite the entire file unnecessarily ([FILE-1](01-file-boundaries.md#file-1)); when presenting proposed edits in chat rather than editing workspace files directly, provide numbered targeted edits with each edit headed by a level-1 Markdown heading (`#`).  
## CODE-2
Before creating or editing a file in a supported language, markup language, or structured format, read and apply its format-specific specification under `references/code-formatting/`:  
1. Programming languages:  
   - [Bash](../references/code-formatting/programming/bash.md)  
   - [JavaScript (ES6)](../references/code-formatting/programming/javascript.md)  
   - [PHP](../references/code-formatting/programming/php.md)  
1. Markup languages:  
   - [HTML](../references/code-formatting/markup/html.md)  
   - [XML](../references/code-formatting/markup/xml.md)  
1. Other file formats:  
   - [JSON](../references/code-formatting/other/json.md)  
   - [LESS](../references/code-formatting/other/less.md)  
## CODE-3
General rules in [CODE-1](#code-1) apply across all code and structured files unless a format-specific guide or the target format's syntax requires an exception (for example, double quotes in strict JSON or spaces in YAML).  
Prose Markdown documents (`.md`) follow [DOC-4](04-statement-structure.md#doc-4) rather than source-code zero-blank-line rules.  
Required GitHub Issue URL references in issue-tracked `code` repositories follow [EXEC-5](08-execution-and-tools.md#exec-5) and are exempt from the no-agent-comments restriction in [CODE-1](#code-1).  
<!-- https://github.com/dmitry-ai/harness/issues/154 -->  
<!-- https://github.com/dmitry-ai/harness/issues/155 -->  
