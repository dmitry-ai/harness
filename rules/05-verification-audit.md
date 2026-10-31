---
trigger: always_on
description: "Provenance, verification method, completeness, and corrections"
---
# Verification
## VERIFY-1
For every material claim, record the source, date, conditions, and status: observation, client report, hypothesis, verified, refuted, or unverified.  
A model response, prior report, or KB entry is not evidence by itself.  
Trace derived claims back to a primary observation or documented client intake: a file's placement inside Evidence does not establish provenance.  
Every external link in a response (outside client intake URLs) must correspond to a valid saved primary observation in `ꘖ/KB/Evidence` (excluding anti-bot/JS challenge shells and empty `word_count: 0` pages), with verified `<title>`/`<h1>`/topic title, `#fragment` anchor, and verbatim quotes; unverified URLs, anchors, titles, or quotes contradicting the observation are blocked during answer preparation.  
Search engine snippets (`search_web`) are discovery indices only and must never be used as a primary source for verbatim quotes, dates, authors, or `#anchor` targets in place of a primary page or browser DOM observation.  
Do not replace unknown values with zeros; do not present a stale check as current.  
## VERIFY-2
Test the claimed property with a matching method: HTTP/DNS/source via a network tool; JavaScript, DOM, authentication, and UI via an executed browser scenario.  
When an HTTP request returns `401`/`403`/`429`, an anti-bot challenge (`js_challenge`/Cloudflare), or an empty JS shell (`word_count: 0`, `browser_check_required: true`), capture the rendered DOM via the user's configured browser CDP endpoint (`harness.py collect-browser` or `collect-http --browser auto` on `cdp_port: 9222`) rather than substituting search engine snippets.  
First compare the full target claim against what the test actually measures: a positive result on a weaker proxy indicator does not establish a strong status, cause, or generalization.  
Absence of a separate file-read tool call does not prove that the agent did not receive the rules: check automatic loading; a file on disk and an applicability receipt do not by themselves prove receipt, comprehension, or execution of instructions.  
Consider a plausible scenario in which the claim is false yet the test still passes; if such a case exists, retain a qualified conclusion or choose a discriminating check.  
A string in a bundle does not prove execution; spoofing `User-Agent` does not prove verified crawler behavior.  
A static DOM snapshot does not prove navigation or state persistence: that requires an action scenario with before/after state.  
A regional URL, browser locale, and verified connection country are distinct conditions; an HTTP client without cookies is not browser Incognito mode.  
Public markup does not establish hidden Admin configuration or actual search engine rankings; select the appropriate primary source or keep the claim as a hypothesis.  
Unavailability of a private admin interface does not transfer `limited` status or conditional `if` qualifiers onto the public storefront and open data: a proven storefront property remains a verified fact and cannot be treated as doubtful due to lacking admin access.  
Before proposing hypotheses about external systems, inspect the local artifact itself (HTTP status, presence of navigation/footer in extracted `links`, and non-empty body) and rule out trivial unavailability of the requested URL.  
Entries in `sitemap.xml` or `robots.txt` do not prove the HTTP status, content, or markup of the pages themselves: for each key site template (home, listing/catalog, product/work item page, blog post, contact page), perform a separate observation of the target URL or CMS JSON endpoint (including Squarespace `?format=json-pretty`).  
On HTTP failure, distinguish DNS resolution failure (`gaierror`/`NXDOMAIN`), TCP timeout, and connection refusal; do not attribute absence of a DNS record to a domain without a direct DNS check or an explicit resolution error.  
Absence of confirmation or a failed test does not equal refutation.  
## VERIFY-3
Prove completeness by listing the objects, time range, pagination, and per-object result; label a sample as a sample.  
All URLs listed in `scope.sample` of a verified claim must have their own primary observations; a single home-page snapshot does not confirm the absence of product or article schema (`Product`/`Offer`/`Article`) across the entire site.  
Take quantitative summaries, date bounds, and distributions over data arrays from the deterministic `summary` (`record_count`, `timestamp_ranges`, `field_counts`) produced by `extract` across the full collection, without judging an array by its first element (`[0]`) or overwriting prior observations during incremental collection.  
Distinguish users, events, sessions, sales, and their denominators; prove causation and business impact separately.  
Verify computed metrics programmatically from raw operands, units, formula, sources, and rounding rules; expert H/M percentages are not measured values.  
## VERIFY-4
Save minimal reproducible evidence: inputs, steps, expected and actual results, conclusion, and material limitations.  
Record the plan with alternatives, disconfirming outcome, and criteria before observation; changing criteria creates a new version and requires a new run while preserving prior outcomes.  
Compare criteria against raw results separately from interpretation; do not replace an unavailable or inconclusive result with a desired success.  
Do not fabricate command output; a zero exit code does not replace semantic verification.  
Propagate fact corrections to dependent permitted materials; flag protected discrepancies explicitly.  
Closing a question with a documented gap is permissible; an unavailable check does not allow assigning `verified` status to a claim.  
Formal compatibility between method and artifact is not a machine guarantee of logical entailment: A.A evaluates substantive entailment.  
