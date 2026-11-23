# INI Formatting Standard

Inherits all general rules from [CODE-1](../../../rules/11-code-formatting.md#code-1) (zero blank lines, alphabetical ordering, single quotes only when quoting is required, no unrequested comments).  
Derived from `.editorconfig` and `.ini` configuration files in Harness, `mage2pro/core`, and the Arturo Navarro Python pipeline.  

## Key-Value Layout and Ordering

1. Use UTF-8 encoding without BOM, LF line endings, and zero blank lines.  
1. Format every assignment with single spaces around `=` (`key = value`).  
1. Order keys alphabetically within each section where semantics do not require a specific order (`client_id`, `client_secret`, `refresh_token`, `seller_id`; `indent_size`, `indent_style`).  
1. Omit quotes around plain scalar values; use single quotes (`'...'`) only when the target parser requires explicit quoting for whitespace or special characters.  
1. When a comment is explicitly required or already present, use `#` rather than `;` unless the target parser requires `;`.  

## Illustrative Example

This example illustrates formatting only and is not part of any target program; never copy it into answers or target files.  

```ini
root = true
[*]
indent_size = 4
indent_style = tab
```
<!-- https://github.com/dmitry-ai/harness/issues/156 -->  
