---
trigger: always_on
description: "Substantive citations, verified documentation anchors, and human-readable links"
---
# Sources
## LINK-1
Support every substantive claim with a verbatim quote and a link next to it; prove platform behavior from official docs or source code, and client specifics from client data.  
Documented capability never proves client configuration, and a bare link never proves a claim; state inferences explicitly and use [DOC-2](04-statement-structure.md#doc-2) when evidence is missing.  
## LINK-2
Read the relevant documentation fragment and cite its URL down to an existing `#anchor`; if no anchor exists, record `anchor_exception` (section title, quote, and link to the saved observation).  
For external documentation URLs whose saved `ꘖ/KB/Evidence` observation contains verified anchors, omitting an `#anchor` is rejected during `answer-check` and `answer-prepare` unless `anchor_exception` is documented.  
Verify destination content rather than HTTP 200 alone, and distinguish raw HTML from post-JavaScript DOM.  
## LINK-3
For consoles, verify account, property, date range, and filters, taking the URL from the actual screen without constructing opaque IDs; strip tracking parameters and prefer `hl=en` for Google documentation.  
## LINK-4
Introduce each piece of evidence once per document and reference its paragraph; standalone responses include their own required sources.  
Use relative paths and stable heading IDs inside files, clickable paths in chat, and never insert `<a name=...>` into the agent KB.  
## LINK-5
Write human-readable links without URL percent-encoding (`%20`, `%D0...`) in all authored Markdown, drafts, reports, and chat replies, wrapping destinations containing spaces or parentheses in `<...>`.  
Before finalizing authored Markdown documents, verify readable links with [validate_links.py](../scripts/validate_links.py) (`--readable`); preserve exact external URLs, verbatim quotes, raw captures, and journals without altering bytes.  
## LINK-6
For files or code in GitHub-backed repositories, `file:///` and cross-repo relative links are prohibited: assign a pushed daily tag (`YYYY-MM-DD` / `YYYY-MM-DD--<N>`) via `harness.py repo-tag` and link `https://github.com/<owner>/<repo>/blob/<tag>/<path>[#L<n>]`.  
Intra-repo relative links remain valid; unencoded `file:///` is allowed only for non-repo or gitignored files.  
