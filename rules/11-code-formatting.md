---
trigger: model_decision
description: "Read before creating or editing source code, markup, or structured configuration files (CODE-1..CODE-4 formatting, style, and Python size ratchet standards)"
---
# Code Formatting
## CODE-1
Never add unrequested or explanatory comments of your own in code, and never delete or alter existing comments ([FILE-1](01-file-boundaries.md#file-1)).  
Never write completely blank lines in source code or structured markup/config files; indent new code with tab characters (`\t`, `indent_size = 4`) wherever syntax permits, preserving pre-existing indentation outside edit scope.  
Allow at most one single return point per function or method; name the accumulated return variable `r` (`$r` in PHP) and omit it when `return <expression>` directly suffices.  
Place the constant on the left in comparisons with variables (Yoda comparisons, e.g., `'Enter' === e.key`, `null === $v`, `None is x`, `200 != status`).  
In `if` / `else` branching, place the shorter block (fewer lines) above the longer block, never create an empty branch, and place `else` on a new line after `}` (`}\nelse {`) in brace-delimited languages.  
Use single quotes (`'...'`) for string literals by default, switching to double quotes (`"..."`) only for concrete syntax or interpolation advantages (such as JSON, Bash/PHP variables, escape sequences, or unescaped apostrophes).  
Keep imports, constants, XML/HTML attributes, CLI options, non-ordered maps, and same-scope functions/methods alphabetically ordered.  
Never rewrite an entire user file unnecessarily ([FILE-1](01-file-boundaries.md#file-1)); when presenting edits in chat, provide numbered targeted edits each headed by `#`.  
## CODE-2
Before creating or editing a file in a supported language, markup language, or structured format, read and apply its format-specific specification under `references/code-formatting/`:  
1. Programming languages:  
   - [Bash](../references/code-formatting/programming/bash.md)  
   - [Java](../references/code-formatting/programming/java.md)  
   - [JavaScript (ES6)](../references/code-formatting/programming/javascript.md)  
   - [PHP](../references/code-formatting/programming/php.md)  
   - [Python](../references/code-formatting/programming/python.md)  
1. Markup languages:  
   - [HTML](../references/code-formatting/markup/html.md)  
   - [XML](../references/code-formatting/markup/xml.md)  
1. Other file formats:  
   - [INI](../references/code-formatting/other/ini.md)  
   - [JSON](../references/code-formatting/other/json.md)  
   - [LESS](../references/code-formatting/other/less.md)  
1. Cross-language comments:  
   - [Issue Comments](../references/code-formatting/issue-comments.md)  
## CODE-3
[CODE-1](#code-1) applies across all code and structured files unless a format guide or language syntax requires an exception (e.g., double quotes in JSON or spaces in YAML).  
Prose Markdown documents (`.md`) follow [DOC-4](04-statement-structure.md#doc-4) rather than zero-blank-line code rules; required GitHub Issue URL references in issue-tracked `code` repositories follow [EXEC-5](08-execution-and-tools.md#exec-5) and [Issue Comments](../references/code-formatting/issue-comments.md) (author header once per file with creation date; issue comments placed right before the modified block or function/method/class header, never dumped into file headers on partial edits) and are exempt from the no-agent-comments rule in [CODE-1](#code-1).  
Navigable cross-reference annotations (`@used-by`, `@uses`, `@see`, `@override`) are mandatory in Python, JavaScript/ES6/TypeScript, and Java code per their language guides and are exempt from the no-agent-comments rule in [CODE-1](#code-1): every function/method must carry a complete `@used-by` list without exception, every overriding method must carry `@override` plus `@see` referencing the overridden method, direct/non-trivial/dynamic dependencies must carry `@uses`, and any code edit must keep cross-references synchronized (`harness.py xref-sync` / `harness.py xref-check`).  
## CODE-4
Decompose new and compact production Python code into small single-purpose functions and modules: keep functions at most `20` executable SLOC and McCabe complexity at most `8`, keep files at most `300` executable SLOC, and never join statements with `;` (test limits: `40` SLOC, McCabe `12`, `600` file SLOC).  
Pre-existing oversized legacy Python files and functions operate under a one-way size ratchet: never increase their executable SLOC or McCabe complexity, and extract new logic into separate compact helpers.  
Place tests for each new feature or gate in a dedicated `tests/test_<feature>.py` module rather than appending unrelated scenarios to monolithic test suites.  
