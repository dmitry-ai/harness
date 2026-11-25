---
trigger: always_on
description: "Primary evidence provenance, method alignment, completeness, and reproducible verification"
---
# Verification
## VERIFY-1
Record source, date, conditions, and status (`observation`, `client_report`, `hypothesis`, `verified`, `refuted`, `unverified`) for every material claim; prior model replies or KB entries are never evidence by themselves.  
Every external link in a response (outside client intake URLs) must match a valid saved primary observation in `ꘖ/KB/Evidence` (excluding anti-bot/JS challenges and `word_count: 0` shells) with verified title, `#anchor`, and verbatim quotes.  
Search engine snippets (`search_web`) are discovery indices only and never primary sources for quotes, dates, authors, or anchors; never replace unknowns with zeros or present stale checks as current.  
## VERIFY-2
Match verification method to the claimed property: network tools for HTTP/DNS/source, executed browser scenarios for JS/DOM/auth/UI, and `collect-browser` / `collect-http --browser auto` on `401`/`403`/`429`, anti-bot challenges, or empty JS shells.  
Compare the full target claim against what the test actually measures: a proxy indicator never establishes a strong unqualified claim, and absence of confirmation does not equal refutation.  
Absence of a separate file-read call does not prove rules were omitted (check automatic loading); static DOM snapshots do not prove state persistence; public markup does not prove hidden admin config; private console unavailability never makes proven public facts `limited` or conditional `if`.  
On HTTP failures, distinguish DNS resolution failure (`NXDOMAIN`/`gaierror`), TCP timeout, and connection refusal before blaming DNS records.  
## VERIFY-3
Prove completeness by listing objects, time range, pagination, and per-object results; label samples explicitly and back every URL in `scope.sample` with its own primary observation.  
Take array counts, date bounds, and distributions from deterministic `extract` `summary` across the full collection rather than element `[0]`; verify computed metrics programmatically from raw operands, units, formula, and rounding rules.  
## VERIFY-4
Save minimal reproducible evidence (inputs, steps, expected vs actual results, conclusion, limitations) and record experiment criteria before observation; never fabricate command output or treat exit code `0` as semantic proof.  
Propagate fact corrections to permitted dependent artifacts and flag protected discrepancies; unavailable checks never earn `verified` status.  
