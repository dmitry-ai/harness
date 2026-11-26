<!-- 2026-11-24 "Add /df--harness--improvement--performance skill and update platform adapters": https://github.com/dmitry-ai/harness/issues/193 -->  
# Performance Audit Report Template and Checklist

Every performance audit produced under [SKILL.md](../SKILL.md) conforms strictly to [df-analysis](../../df-analysis/SKILL.md) ([DOC-2](../../../rules/04-statement-structure.md#doc-2), [DOC-3](../../../rules/04-statement-structure.md#doc-3), [DOC-4](../../../rules/04-statement-structure.md#doc-4), [DOC-5](../../../rules/04-statement-structure.md#doc-5)) and [LINK-5](../../../rules/02-link-standards.md#link-5).  

## 1. Mandatory Formatting Rules

1. **No Markdown tables:** Markdown tables are strictly forbidden by [DOC-4](../../../rules/04-statement-structure.md#doc-4); present timesheets, top slow files, and method comparisons as structured numbered lists or prose.  
1. **One sentence per line:** Start every sentence on a new line and terminate continuing lines inside the same paragraph or list item with two trailing spaces (`  \n`).  
1. **Readable links and exact anchors:** Preserve spaces and Unicode in authored paths (`<...>` wrapper for spaces, zero `%20` / `%EA...` encoding per [LINK-5](../../../rules/02-link-standards.md#link-5)), and cite every external documentation URL down to a verified `#anchor` or documented `anchor_exception` ([LINK-2](../../../rules/02-link-standards.md#link-2)).  
1. **Response language:** Write the final report in the user's request language ([TEXT-1](../../../rules/03-language-lexicon.md#text-1)), adapting headings to that language while preserving exact top-level numbers `# 0` through `# 4` and exact JSON metadata keys.  
1. **Verified arithmetic:** State explicit operands for every derived sum, difference, percentage share, and speedup multiplier (`A + B = C`, `A / B ≈ X%`) so deterministic inline arithmetic checks verify every figure directly against primary JSON telemetry.  

## 2. Five-Section Report Structure (`DOC-5`)

<!-- 2026-11-25 "Require separate companion /df-analysis tracks for every complex problem analysis": https://github.com/dmitry-ai/harness/issues/249 -->  
Use this exact top-level `# 0`..`# 4` structure for the primary performance problem analysis (optionally preceded by a brief executive summary pointing to verified telemetry totals), followed by the three mandatory separate `# 0`..`# 4` companion analyses required by [df-analysis](../../df-analysis/SKILL.md#21-mandatory-four-separate-analyses) (`§2` Culprit and Provenance Attribution, `§3` Test and Verification Escape, and `§4` Journal, Reporting, and Observability Integrity):  

### `# 0` Problem Metadata

Generate the tab-indented fenced `json` metadata block deterministically via:  

```text
python <scripts>/harness.py problem-metadata <project> --issue https://github.com/<owner>/<repo>/issues/<N> [--source-project <owning-project>] --format markdown
```

Ensure the `"Issue"` key holds the verified open parent GitHub issue URL filed via [df-github-issue](../../df-github-issue/SKILL.md) (or `null` via `--no-issue` only in non-GitHub workspaces).  

### `# 1` Problem Description and Primary Telemetry

1. State the exact audited conversation UUID, journal step, workspace root, model/instance, date/timezone, and test/runtime target.  
1. Quote verbatim any relevant failure, timeout, truncation notice, or runner summary line (`Ran N tests in X.XXXs`, `CHECKPOINT`, `The tool's output was truncated`, etc.).  
1. Link all saved primary JSON telemetry artifacts under `ꘖ/KB/Evidence/<Audit-Slug>/` (`timesheet.json`, `suite-profile.json`, `microbenchmarks.json`).  
1. Present the continuous phase-by-phase timesheet (`P1..PN`, Track A) and/or top slow files, slow tests, `Popen` breakdown, and `cProfile` hotspots (Track B), stating measurement scope and caveats explicitly.  

### `# 2` Root Cause Analysis

Evaluate at least two competing or orthogonal root-cause hypotheses (`H-1` / `C-1`, `H-2` / `C-2`, …) per [DOC-2](../../../rules/04-statement-structure.md#doc-2).  
For each hypothesis, include all four mandatory elements:  

1. **Essence:** Concrete code or orchestration mechanism with clickable primary links to exact file/line ranges and saved telemetry JSON.  
1. **Arguments for:** Verbatim code/log excerpts, measured seconds, call counts, syscall counts, and percentage share of total latency.  
1. **Arguments against:** Alternative explanations, measurement noise or confounding variables, partial overlap between bottlenecks, or documented unavailability of verification (capping unverified hypotheses without counterevidence at `<= 75%`).  
1. **Plausibility score in `%`:** Explicit expert basis grounded in the observed measurements.  

### `# 3` Source Project Attribution

Explicitly identify which project owns each bottleneck verified in `# 2` against `paths.json` and repository roots (for example, `dmitry-ai/harness` core runtime vs Harness test fixtures vs `dmitry-ai/antigravity-addons` / `dmitry-ai/chatgpt-desktop-addons` vs the audited target project).  
Do not assume the workspace where the slow turn occurred owns the defect; when ownership is uncertain, evaluate candidate source projects as competing hypotheses per `# 2`.  

### `# 4` Permanent Systemic Solutions and Implementation Queue

State the single unified scoring criterion at the top of `# 4` per [methodology.md](methodology.md#5-evidence-grounding-scoring-rubric-and-deduplication).  
Evaluate at least two ranked candidate solution methods (`M-1`, `M-2`, …) targeting the `# 3` source project without one-off hacks (clearly marked as proposed in Audit-Only Mode, or reported with commit SHAs and measured before/after metrics in Implementation Mode):  

1. **Essence:** Concrete systemic change linked to `# 2` cause IDs, explicit applicability conditions, and an observable quantitative verification criterion.  
1. **Arguments for:** Telemetry savings, controlled microbenchmark ratios (`microbenchmarks.json`), and verbatim official documentation quotes with `#anchor` links.  
1. **Arguments against:** Trade-offs, cache invalidation or concurrency hazards, maintenance cost under `CODE-4`, and explicit safeguards preserving all verification invariants.  
1. **Analyst score in `%`:** Basis under the declared criterion without artificial normalization to `100%`.  

End `# 4` with a concise ordered implementation queue (Phase 1 highest-ROI runtime/shared fixes, Phase 2 fixture/subprocess reductions, Phase 3 runner/workflow discipline) and links to `ꘖ/KB/<Audit-Slug>.md` and `ꘖ/KB/Progress.md`.  

## 3. Pre-Flight Verification Checklist

Before running `harness.py answer-prepare`, confirm every gate passes:  

1. Primary telemetry JSON files and `ꘖ/KB/<Audit-Slug>.md` (listing every cited external `http(s)://` URL) are saved, and `ꘖ/KB/Progress.md` links the audit module.  
1. Parent GitHub issue is created and verified via `df_github_issue.py` with saved read-back Evidence JSON (and in Implementation Mode, all child issues are committed in separate commits, pushed, verified by full parallel test suite, and closed).  
1. `harness.py analysis-check <project> --response-file <candidate.md> --mode problem` exits `0` (`valid: true`).  
1. `harness.py answer-check <project> --response-file <candidate.md> --conversation <uuid>` exits `0` (`valid: true`).  
1. `harness.py answer-prepare <project> --response-file <candidate.md> --consume-input --conversation <uuid>` exits `0` (`ready: true`), and the clean body (matching `body_sha256`) is published verbatim.  
