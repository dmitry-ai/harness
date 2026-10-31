# Evidence and Experiments

Read this contract when starting a new analysis, deepening a conclusion, planning an experiment, or preparing a review.  
The contract validates provenance, digests, and method-to-property alignment; A.A evaluates substantive meaning and classification integrity.  
Implementation resides in `scripts/agent_tools/{claims,experiments,review}.py` of the shared toolkit.  

## Typed Claims

New publications use `schema_version: 3` in `Analysis.json`.  
Legacy schema versions 1 and 2 remain readable for diagnostics; when preparing a new response, migrate required claims manually with source verification, as there is no automatic promotion to `verified`.  
`facts` stores first-class F claims, followed by the five analysis sections: `identity`, `concerns`, `misconceptions`, `causes`, and `methods`.  
Working candidates live in `ꘖ/data`; official publication renders from the canonical `ꘖ/KB/Analysis.json`.  

Every claim contains:  

1. `id`, `essence`, and `assessment_basis`.  
1. `knowledge_type`: `observation`, `client_report`, `hypothesis`, `recommendation`, or `calculation`.  
1. `verification_status`: `verified`, `limited`, `unverified`, `unavailable`, or `stale`.  
1. `scope`: `description`, `sample`, and `limitations`; never generalize a sample with words like `"all"` without full coverage, and for verified observations about page content or markup (`properties`: `content`/`markup`), every URL in `scope.sample` must be backed by its own page observation (not just `sitemap.xml`/`robots.txt`), while negative site-wide claims (`"absent across the entire website..."`) cannot rest solely on the home page.  
1. `properties`: tested property types — `content`, `markup`, `dom`, `interaction`, `currency_transition`, `ip_country`, `admin_configuration`, `serp`, `platform_capability`, `calculation`, `causality`, `business_impact`, `architecture_change`, `pricing_change`.  
1. `materiality`: `routine|significant`, `novelty`: `new|restatement`, and `category`: `descriptive|causal|architecture|pricing|interaction`.  
1. `derived_from`: list of `{claim_id, sha256}` referencing the canonical digest of each premise; digests are computed by `claims.claim_digest`.  
1. `evidence`: primary source links, or an empty list when backed by versioned `derived_from` premises; missing data is permitted with `unavailable` status and a specific documented gap.  
1. `missing_checks`: empty list `[]` for `verified`, non-empty for all other statuses.  
1. `impact`: `severity` (`unknown|low|medium|high|critical`), `basis`, and `evidence_claim_ids`; `high` and `critical` require versioned grounds in `derived_from`.  

A `hypothesis` can never have `verification_status: verified`, regardless of how high its `probability_percent` is.  
`for`/`against` entries reference a versioned `claim_id` or carry their own `evidence_id` and `argument`; an `against` entry must semantically weaken or bound the hypothesis and cannot reuse the same `evidence_id` as `for`.  
An empty `against` list requires `counterevidence` with `status` (`unavailable|not_found`), `reviewed_sources`, and `limitations`; an unverified hypothesis (`verification_status != verified`) with an empty `against` list—or a causal/misconception hypothesis (`causes`, `misconceptions`) lacking an `observation`/`experiment` counter-observation in `against`—cannot have `probability_percent > 75`.  
Every hypothesis in `causes` or `misconceptions` includes `alternative_explanations` and `discriminating_check`; every method in `methods` includes `applicability` and `validation` alongside `criterion`, `score_percent`, and `addresses`.  
In a verified `observation` or `client_report` (`verification_status: verified`), every standalone number in `essence` must appear in the primary quotes/locators of `evidence` or be computed via `calculation`/`derived_from`.  
See [analysis.example.json](analysis.example.json).  

## Primary Provenance

Every `evidence` entry contains `id`, `kind`, `source`, `source_sha256`, `quote`, and `locator` (`type` and `value`).  
Locator types: `text`, `json_pointer`, `anchor`, or `lines` (inclusive `<start>-<end>` range).  
`kind: observation` additionally specifies `observation` (the path to saved HTTP/DOM metadata), while `source` names the captured HTTP(S) URL; on network failure, `observation` records `error_kind` (`dns_error`, `tcp_timeout`, `connection_refused`, `tls_error`), and any claim that a domain fails DNS resolution requires an observation with `error_kind: dns_error`.  
`kind: intake` / `attachment` additionally specifies `manifest`—the registered snapshot or import receipt certifying those exact bytes and their origin.  
Validation checks the full receipt and links the registered snapshot to the initial capture; an arbitrary manifest pointing to an agent-authored file hash does not count as client intake.  
An agent-authored `site.json`, report, or note placed inside `Evidence` is never a primary client source.  
`kind: experiment` specifies `experiment` and `artifact_id`; the source path and hash must match an artifact of the immutable recorded experiment.  
Client-supplied Markdown is valid as a primary attachment, whereas agent-authored topical Markdown modules remain presentation/navigation.  
Circular dependencies and stale premise digests block publication clearance.  

HTTP proves the received server response; DOM proves a state snapshot; neither by itself proves a user click, currency switch, Incognito mode, or IP country.  
A browser action does not by itself establish causation, business harm, or authorized distributor status.  
Documentation of a platform capability does not establish a specific client's configuration.  
For `documentation` evidence, validation checks either the `#anchor` in the cited URL or an `anchor_exception` naming a unique section lacking a suitable anchor in that same observation; the quote must reside inside that section.  

## Plan Before Result

Recording a plan prior to execution does not by itself make a test substantively sufficient.  
First record both the full `target_claim` and the actual `tested_claim`, since a test may measure only a weaker proxy indicator.  
Evaluate a concrete counterexample `"target_claim is false, yet the test passes"`; whenever such a counterexample is plausible, the indicator's relationship is `proxy` rather than `direct` confirmation.  
Observing an indirect indicator in local state or a narrow sample does not establish legal/regulatory status, a hidden backend setting, or a population-wide aggregate.  
Design experiments that discriminate between competing explanations, or narrow the conclusion to what was actually observed.  
An independent A.A auditor verifies this alignment against the target claim and actual code/artifacts rather than trusting the author's `"test passed"` summary.  

See [question.example.json](question.example.json) for a complete question specification.  
Each entry in `requirements` specifies `id`, `claim`, `property`, `method`, `scope.objects`, `conditions`, `alternatives`, `expected`, `falsification`, `discriminating_test`, and `completion_criterion`.  
Supported methods: `http`, `dom`, `browser_scenario`, `admin`, `serp`, `geolocation`.  
Separate a direct observation from a causal hypothesis that the chosen experiment cannot establish on its own.  
A worker assignment states a neutral question, available inputs, and verifiable outcomes; it never instructs the worker to confirm a predetermined verdict.  
Before running a material or disputed experiment, verify that the test is capable of falsifying the claim and distinguishing it from alternatives; an independent A.A evaluates methodology.  

`prepare-experiment` writes an immutable plan prior to observation, including its disconfirming outcome.  
Its `path` and `sha256` are passed to `record-experiment`; observations and native actions must have timestamps later than that plan version.  
For `browser_scenario`, `native_trace` also captures the actual `prepare-experiment` call and its receipt alongside subsequent UI tool calls, verifying their chronological order in the native log.  
Changing criteria requires a new plan version with `--amendment-of` and `--amendment-reason` plus fresh observations; the prior run and its outcome remain preserved.  
Replaying an old file or saved JSON does not count as a newly executed browser experiment.  

For deterministic evaluation, the plan includes `assertions`.  
Each assertion selects a pre-declared `artifact_id` or `artifact_role`, `locator` (`json_pointer|text`), `operator`, and `expected` value, plus a `disconfirming` rule with `operator` and `expected`.  
Supported operators: `equals`, `not_equals`, `contains`, `gt`, `gte`, `lt`, `lte`; arbitrary code inside a plan is never executed.  
Values are extracted directly from saved raw artifacts rather than from the agent's prose `actual_result`.  
Matching expected criteria, matching a disconfirming outcome, and inconclusive results are distinguished; a read error or missing data never refutes a claim.  
An open-ended exploratory run without machine-verifiable assertions is recorded with `limited` status and requires substantive evaluation by A.A.  
Even a deterministically `verified` assertion applies only to the specific requirement of that experiment; it does not automatically promote a broader linked claim to a fact.  

A `browser_scenario` records native tool calls, steps, before/after state, URLs, selected country/locale, currency, artifacts, and limitations.  
States, actions, results, and egress checks must share the same verified `browser`/`tab` and available context/session IDs from native trace data.  
Author assertions cannot supply missing identity; unknown or mismatched identity leaves the experiment `unverified` without confirmed browser capabilities.  
In current `cua_repl.getAXState` output, the text `Browser tab: ...` appears without a structured `browser`/`tab` pair, so that response alone does not confer `verified` status.  
The native tool name and namespace are recorded separately; a bare `js` call without a browser namespace does not prove that a browser tool was used.  
The substring `.click()` inside code text does not prove execution: verification requires an explicit native action call or a supported unconditional `await` call with literal arguments.  
Branches, loops, helper functions, and ambiguous JavaScript require another verifiable action-recording mechanism.  
The `record-experiment` specification contains `plan`, `plan_sha256`, `status`, `conditions`, `actual_steps`, `actual_result`, `artifacts`, and `limitation` for gaps; `requirement` is read from the frozen plan.  
A collector artifact is referenced by `id` + `observation`, a native trace artifact by `id` + `native_event_id` from the selected `native_trace`, and an imported file by `id` + `path` (which remains static data without browser capability).  
`actual_result` is the author's interpretation; `assertions` evaluate raw artifacts independently of it.  
Session mode is `normal|incognito|isolated|unknown`; an `isolated` profile or empty cookie jar does not equal browser `incognito`.  
Egress country is verified by a measurement on that exact connection, separately from URL country codes or browser locale.  
`collect.context` incorporates condition/state fingerprints into the cache key, but passed context labels do not by themselves prove those conditions held.  
`capture-dom` remains a read-only snapshot of an explicitly chosen tab; after state changes, a new snapshot must be captured.  

## Calculations

`calculation` supports `operation: percent_change` using the formula `(new - old) / old * 100`.  
The `old` and `new` operands specify `claim_id`, `evidence_id`, an exact decimal string `value`, and an identical `unit`; both `claim_id` values must appear in `derived_from`.  
Units are verified against the primary quotes; computing a percentage change across different currencies requires a separate justified conversion step beforehand.  
The number and unit must form a single unambiguous pair in the quote or structured `amount`/`currency` (`value`/`unit`) field; finding a number and a currency symbol in unrelated parts of a page is insufficient.  
The sign is part of the quantity and is verified against the full primary context; never strip a minus sign by truncating a quote.  
Ambiguous raw HTML is not accepted as an automatic numeric pair: extract a verifiable visible text value or structured JSON field rather than attributing display meaning to arbitrary markup.  
Specify `result_unit: percent`, `result`, `rounding_places` (`0`–`12`), and `rounding: ROUND_HALF_UP`; `Decimal` recomputes the result and verifies the source numbers against the primary quote.  
`€63.95` vs. `€53.95` yields `18.5357%` at four decimal places.  
That calculation alone does not establish the presence or absence of a `+20%` backend markup rule prior to rounding.  
`probability_percent` and `score_percent` remain reasoned expert estimates rather than measured calculations.  

## Synthetic Fixtures

[example-source.json](example-source.json) and [example-observation.json](example-observation.json) are explicitly synthetic offline fixtures; no network request to `example.invalid` was made.  
For isolated validation of the example, copy `example-source.json` to `ꘖ/KB/Evidence/Examples/response.bin` and `example-observation.json` next to it as `observation.json`, preserving exact bytes.  
Never include fixture data in a real client project card.  
Command examples and the review contract are in [workflow.md](workflow.md).  
