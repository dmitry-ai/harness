---
trigger: always_on
description: "Claim, exact quote, and verified source address"
---
# Sources
## LINK-1
Support every substantive claim with an exact quote and a link next to it; prove platform behavior from its documentation or source code, and client specifics from client data.  
Documentation of a capability does not prove a client's configuration; the presence of a link does not prove a claim.  
State third-party sources and inferences explicitly; when evidence is absent, use [DOC-2](04-statement-structure.md#doc-2).  
## LINK-2
Documentation: read the fragment relevant to the claim and provide the URL down to an existing anchor.  
If no anchor exists, cite the section title and quote; do not invent an identifier.  
In structured analysis, record `anchor_exception`: the section title and a link to the observation where the section, quote, and absence of a suitable anchor were verified.  
Verify the content and destination rather than HTTP 200 alone; distinguish raw HTML from post-JavaScript DOM.  
## LINK-3
For a console, verify the account, property, date range, and filters; take the URL from the relevant screen and do not construct opaque IDs.  
Strip tracking parameters; other URL shortenings are permissible only after verifying identical content and anchor resolution.  
For Google documentation that supports `hl=en`, prefer the English version.  
## LINK-4
Introduce a piece of evidence once within a document and reference its paragraph; a standalone response must include its own required sources.  
Use relative paths and stable heading IDs inside files; in chat, use clickable paths as required by the environment.  
After moving files, re-verify paths and anchors; do not add `<a name=...>` into the agent KB.  
## LINK-5
All agents, including primary, A.A, and A.F, write human-readable links in all authored texts: intermediate Markdown/KB, drafts, reports, final documents, and materials for publication or client delivery.  
Do not apply URL encoding to authored text, link labels, or file paths: preserve spaces and Unicode instead of `%20`, `%D0...`, `%EA...`.  
In Markdown, wrap destinations containing spaces or parentheses in `<...>`: `[Source](<folder with spaces/ꘖ/file.json>)`; path scope follows LINK-4.  
Use `links.markdown_link`/`readable_reference` when generating links; verify authored documents with `validate_links.py --readable` before completion.  
Do not re-encode an obtained external URL or alter its significant parameters, signatures, or escaped delimiters; display a readable link label while preserving the exact target address.  
Source documents, primary evidence, verbatim quotes, code, and the exact journal are preserved without byte substitution; that is not a reason to copy percent-encoding into new authored links.  
URI serialization inside browsers, HTTP, SQLite, native APIs, and hidden hyperlinks of export formats belongs to programmatic transport rather than readable document formatting.  
