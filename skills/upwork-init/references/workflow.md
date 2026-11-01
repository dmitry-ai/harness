# Internal Analysis Protocol

All commands are executed by the agent from the active chat via `scripts/upwork_project.py`; they do not launch LLMs.  
Pass `--platform codex` or `--platform antigravity`; in Codex, the profile is resolved from `CODEX_HOME` or passed explicitly via `--codex-profile`.  
`<project>` is the exact existing root of the active job post, never the shared `code`/`daily` parent folder or a neighboring project.  
Pass `candidate`/`spec`/`plan`/`answer` payloads in UTF-8 via stdin (`-`) or—on Windows PowerShell where pipes corrupt non-ASCII—write a UTF-8-no-BOM file inside `ꘖ/data/scratch` and pass `--consume-input`: a verified write deletes an unchanged scratch input while any error or conflict preserves it, and no one-off scripts are created in the project.  
The `collect` plan is retained in full inside publication provenance.  
When a command accepts both `--spec` and `--response-file`, stdin (`-`) may be used for at most one of them; write the other exact input to `ꘖ/data/scratch` with `--consume-input`.  
All evidence records belong in `ꘖ/KB/Evidence` and service state in `ꘖ/data`; manual `KB/` files are preserved.  

## Continuation

```text
python <tool> status <project>
python <tool> configure <project>
python <tool> configure <project> --check
python <tool> register <project>
python <tool> resume <project> --reason "quota/power failure/Windows hang"
python <tool> adopt-requests <project> --conversation <UUID of current parent chat>
```

`resume` verifies the saved snapshot and updates `ꘖ/KB/Progress.md`.  
`adopt-requests` reads the exact user messages for the job through the active platform adapter, records native message IDs, and never reconstructs text from collapsed summaries.  
Codex reads the selected profile's native SQLite/session JSONL in read-only mode; Antigravity reads native `USER_INPUT` steps.  
In a new chat without `/upwork-init`, the adapter requires the exact native project `cwd`/`workspace_uri` or an explicit `"Project root: `<absolute path>`"` in the user request.  
A shared repository root or multi-folder workspace does not identify a specific project; explicitly switching to another job post closes the prior request scope.  
Importing requests from the second platform appends to prior exact requests while preserving already prepared responses.  
If the native database format is unavailable, preserve verified exact requests of the current chat and pass `resume --request-file <file>` to record the current request in service state.  
Never fabricate historical requests or intermediate responses.  
New projects use these same mechanisms right after `init` to record the initial request and snapshot without asking the user to repeat the command.  

`status` reports stage states and KB hashes; completion is never inferred merely from the existence of `Analysis.json`.  
Active registration is mandatory for working `daily` projects; a `pending` status or missing receipt for the active platform prevents completing `identity_init`.  
When switching platforms, run `configure` and `register` on the existing project root without re-running `init`.  
By default, `register` services both platforms; `--target` repairs a single platform registration.  
A new initial-analysis request without a recorded response clears `finalize` completion.  
`resume` does not run `inspect`/`init`, does not spawn workers, and does not read `Context.md`.  
When resuming a legacy project, all stages beyond a mechanically verified `capture` require verification; read what was already created rather than starting over from scratch.  
If workspace creation itself was interrupted before `ꘖ/project.json` was written, finish `init` from the saved snapshot of the current chat and then continue the protocol.  

Once initial analysis is finalized, any specific instruction to draft or edit a proposal is executed semi-manually using the same KB, exact journal, `continuation.md`, and existing `result/**/draft.md` or `final.md`.  
The stages below track initial analysis; they do not declare a proposal ready and do not require re-running all five stages when switching platforms.  
Snapshot any existing `draft.md` per FILE-2 before editing, and record the current task and next step in `ꘖ/data/continuation.md`.  
After initial analysis is finalized, record a proposal-only request via `answer-prepare` without adding it as an unfinished initial-analysis request.  

## Stages

`capture → identity_init → research → analysis → review → kb_review → finalize`.  
Stage completion is recorded only after producing a verifiable output; unchanged outputs are reused.  
Inputs and outputs are exact paths relative to the project root, and their SHA-256 digests are re-verified on continuation.  
Never list `workflow.json`, `rendered.json`, or `Progress.md` as proof of their own stage.  

```text
python <tool> stage <project> identity_init --input "ꘖ/project.json" --output "ꘖ/data/registration-check.json" --note "Verified project cards, manifests, and actual UI folder branch"
```

Write the actual verification artifact to the declared `--output` path; never fabricate a placeholder file just to obtain a stage receipt.  
`research` requires closed questions or documented gaps; `analysis` requires current KB modules and evidence; subsequent stages require a current A.A substantive review.  
In a justified routine case, the primary A.A records a `schema_version: 2` report with `review_kind: self_review` covering the response and every mapped claim, passing identical `--parent` and `--reviewer` UUIDs of the current chat to `record-review`.  
Self-review is not an independent audit; `significant` work requires two independent A.A reviewers.  
If any input or output digest changes, the stage becomes `stale` while prior files and receipts remain preserved in history.  
An interruption between publications does not mark a stage complete; atomic writes and digest checks allow retrying only the unfinished operation.  

## Question Registry and Ownership

A question specification is a JSON object with `id`, `question`, `impact`, `done_when`, `inputs`, `outputs`, and `requirements` per the [experiment contract](evidence-contract.md#plan-before-result).  
All declared `inputs` must exist, and `outputs` must be exact permitted file paths inside `ꘖ`.  
See [question.example.json](question.example.json) and adapt the paths and question to the specific project.  

```text
python <tool> question-add <project> --spec -
python <tool> question-claim <project> Q-SITE --owner <observed-worker-ID>
python <tool> question-search <project> Q-SITE --owner <ID> --query "exact query" --useful
python <tool> prepare-experiment <project> --spec <single-requirement-JSON>
python <tool> record-experiment <project> --spec <actual-experiment-JSON>
python <tool> question-finish <project> Q-SITE --owner <ID> --output "ꘖ/KB/Evidence/site-report.json" --results <results-JSON>
```

Ownership is verified against live native UI progress; the `owner` string is a coordination key rather than OS authentication.  
After three empty searches, return the gap or justify `--method-change`; the search log does not hook built-in `search_web`, so the agent enforces this discipline directly.  
Close a gap with a saved report and `--gap "what remains unverified and why"`, never with a fabricated confirmation.  
Provide one result entry per requirement: `requirement_id`, `status`, `experiment` (path to the immutable run), plus `limitation` whenever the status is `unverified` or `unavailable`.  
Freeze the plan via `prepare-experiment` before capturing new observations; `record-experiment` binds `plan`/`plan_sha256`, the requirement, and primary artifacts, comparing the outcome against the pre-registered criteria.  
Register any modified test via `prepare-experiment` with `--amendment-of` and `--amendment-reason`; a new verdict requires fresh observations while preserving the prior run.  
Steps, raw output, and verdict are kept distinct; a disconfirmed or inconclusive raw outcome can never be overridden into `verified`.  
If a worker stops, run `question-handoff` with the old and new owner IDs and the verified reason after checking the UI; never silently hijack a live worker's question.  
A worker writes only its assigned report file; the shared HTTP observation store is managed by the tool under dedicated locks.  

## Saved Sources

```text
python <tool> collect <project> --plan - --output "ꘖ/KB/Evidence/site-report.json"
python <tool> extract <project> <observation-from-result> --profile tracking
python <tool> extract-file <project> "ꘖ/KB/Evidence/Attachments/.../audit.pdf" --profile document
python <tool> sync-attachments <project> --media-descriptions -
python <tool> source-ref <project> "Evidence/data.json" --part related_descriptions --part "~022..." --part description
```

[collection.example.json](collection.example.json) defines `requests`: URL, profile (`html`, `shopify`, `tracking`, `document`), `scope`, and optional `headers`/`max_age`/`refresh_reason`.  
A URL `#fragment` belongs to the citation locator rather than a separate HTTP request.  
Distinct URLs, headers, scopes, and contexts produce separate observations; `context` records the session/state fingerprint, selected market, and connection conditions without storing cookies or secrets.  
Passing a `context` label does not prove Incognito mode or egress country; those require actual measurements within that same context.  
By default, successful responses are reused for up to 24 hours and error observations for up to 5 minutes; always check `observed_at` and required freshness.  
Specifying `refresh_reason` records a new measurement without overwriting the prior capture.  
A saved HTTP 403/404 is an observed outcome; do not retry it blindly.  
A JS challenge page is a prompt to choose an appropriate browser check, not proof that verified search crawlers are blocked.  
HTML and bundle captures show static source rather than runtime execution (including the extracted `links` array with all `<a href>` targets and visible anchor text); JSON extraction computes a deterministic `summary` across object arrays (`record_count`, `timestamp_ranges` with `min`, `max`, `by_date`, `earliest_record`, `latest_record`, and `field_counts`); DOCX/PDF extraction preserves hyperlinks and Markdown formatting.  
Re-running `collect --output` into an existing `ꘖ/KB/Evidence/*.json` report merges prior `results` without losing earlier observations.  
All client-attached files are saved simultaneously in the root `source/` folder and in `ꘖ/KB/Evidence/Attachments/<sha256>/`, and their full text, video transcripts (`# Video:`, `# Key Spoken Commentary Points (Additions to Document Text):`, `# Full Audio Transcript:` with `[MM:SS]`), and image descriptions (verbatim text in `«»`, UI description, confirmations and contradictions against client statements with `%` scores) are synchronized into both KBs (`KB/Project.md` and `ꘖ/KB/{Project,Projects,Evidence}.md`) during `init` and via `sync-attachments`.  

For post-JavaScript DOM inspection, only read-only capture of an explicitly selected tab at an exact URL is permitted:  

```text
python <tool> capture-dom <project> --url <exact-URL> --tab-id <explicit-ID> --session-id <permitted-runtime-session>
```

The command never opens, switches, reloads, or closes tabs; any URL or tab ID mismatch is reported as an error.  
A DOM observation is stored separately and never fabricates an HTTP 200 status code when the HTTP status is unknown.  
When an authenticated test tab is needed, the agent opens it via the native browser tool in its own session per EXEC-3.  

## Analysis and Validation

The canonical `schema_version: 3` contract is enforced by `analysis.py`, `claims.py`, and `evidence.py`; schema versions 1 and 2 remain readable for diagnostics and recovery.  
New `save-analysis`/`render-analysis` runs require v3 and primary grounds; legacy claims are never automatically promoted to `verified`.  
Structure, source rules, and qualified statuses are defined in the [evidence contract](evidence-contract.md), with a verifiable fixture in [analysis.example.json](analysis.example.json).  
Each `for` entry contains `argument` plus a versioned `claim_id` or its own `evidence_id`; `against` contains counter-arguments or documented `counterevidence`.  
`counterevidence` specifies `status` (`not_found|unavailable`), `reviewed_sources`, and `limitations`; when `against` is empty on an unverified hypothesis (`verification_status != verified`), `probability_percent` cannot exceed `75`.  
Reporting `not_found` when a source was actually unreachable is invalid; use `unavailable`.  
Hypotheses in `causes` and `misconceptions` must include `alternative_explanations` and `discriminating_check`.  
Every standalone numeric figure in `essence` of a verified claim (`observation` or `client_report` with `verification_status: verified`) must appear in the primary quotes/locators of `evidence` or follow from `calculation`/`derived_from`.  
Primary `source`/`quote`/`source_sha256`/`locator` fields reside in `evidence`; a link to an agent-authored Markdown module never substitutes for a primary source.  
Legacy `sources`/`source_id` fields remain readable for older files; in v3, reuse `facts` (`F-*`) and `derived_from` with exact `claim_digest` values.  
Use `source-ref` to escape JSON pointers; the quote is verified against the exact resolved fragment.  
Exact quote matching is the default; `quote_match: whitespace` permits normalizing whitespace runs only, never words, numbers, or punctuation.  
Citing documentation without an `#anchor` requires `anchor_exception` (`section` + `observation`), which verifies that the section exists, lacks a suitable anchor, and contains the quote.  

```text
python <tool> save-analysis <project> --candidate - --expected-sha256 <current-hash-from-status>
python <tool> render-analysis <project>/ꘖ/KB/Analysis.json
python <tool> validate-analysis <project>/ꘖ/KB/Analysis.json --format json --evidence
python <tool> check-project <project>
```

Omit `--expected-sha256` only when creating `Analysis.json` for the first time; updating an existing file requires its current hash.  
History of both JSON and rendered Markdown versions is preserved; external edits produce a saved candidate and conflict rather than an unconditional overwrite.  
Keep incomplete working notes in `ꘖ/data` with an explicit status; they never substitute for a finalized analysis.  
One-off scripts (`*.py`, `*.ps1`, `*.sh`, `*.bat`, `*.cmd`) inside `ꘖ/data` or `.agents` of a project are prohibited and fail `check-project`.  
Validation errors are returned as a single list containing `code`/`field`/`claim_id`/`message`/`hint`; fix the specific defect and re-evaluate any dependent conclusions.  
Passing formal validation does not prove substantive truth or completion of the A.A audit.  

Format all authored links across intermediate and final texts per [LINK-5](../../../rules/02-link-standards.md#link-5): preserve spaces and Unicode without URL encoding.  
`links.markdown_link(label, target)` formats Markdown links (wrapping in `<...>` when needed), and `readable_reference` decodes unnecessary percent-encoding in paths/fragments while preserving significant query parameters and delimiters.  
`validate_links.py --readable <files>` inspects authored source links rather than percent-encoded `href` attributes produced by a HTML renderer.  
This check also covers authored links in plain text and HTML; verbatim quotes, code blocks, and imported source copies retain their original bytes.  
`check-project` validates the agent KB, root project card, and text deliverables under `result/`; `record-answer`, `answer-prepare`, and `finalize` validate the new final response before writing or completing the stage.  
Shared publication helpers reject new percent-encoded authored links before modifying an existing file; historical entries and raw JSON captures are not reformatted.  

## Red Flags

Before diving into technical debugging, evaluate whether the client is acting as an intermediary on this job and whether the target website can be identified.  
Store the underlying grounds in standard `identity` claims backed by primary evidence and limitations; `red_flags` entries reference those claim IDs rather than duplicating evidence.  
In new analyses, populate `red_flags` explicitly: either the list of active risks or `[]` once both risks have been evaluated and ruled out.  
A missing `red_flags` key in a legacy file means `"not evaluated"` rather than `"no risks"`, and any existing warning block is preserved.  

```json
"red_flags": [
  {
    "id": "RF-CLIENT-INTERMEDIARY",
    "status": "confirmed",
    "summary": "The client is managing an end client's project through their agency.",
    "basis_ids": ["H-IDENTITY-CLIENT"]
  },
  {
    "id": "RF-WEBSITE-UNIDENTIFIED",
    "status": "unresolved",
    "summary": "After inspecting the job post, available history, and targeted search, the domain remains unidentified; a link must be requested from the client.",
    "basis_ids": ["H-SITE-1"]
  }
]
```

Replace the example claim IDs with actual IDs from `identity`; when intermediation is a hypothesis rather than a confirmed fact, use `suspected` instead of `confirmed`.  
Each active flag is rendered independently; when both flags are present simultaneously, a separate bold warning highlights the high likelihood of declining the project.  
`render-analysis` and `validate-analysis --render` output the block ahead of the five stages and, for the canonical `ꘖ/KB/Analysis.json`, also synchronize it at the end of the root `.md` inside a dedicated level-1 section.  
Links in the root project card point to `identity` claims in `Analysis.json`, whereas links in the chat report point to the corresponding report headings.  
The renderer preserves all card bytes outside the managed block and archives prior block versions in `ꘖ/data/red-flags-history`.  
At the end of the root `.md`, the level-1 heading `# Red Flags — N` appears first, followed inside that section by `<!-- upwork-init:red-flags:start -->`, the flag items, and `<!-- upwork-init:red-flags:end -->`.  
A legacy unmodified block at the top of the card is automatically migrated to the end; re-running the renderer does not create duplicates or empty sections.  
Manual edits inside the managed block or its heading—or corrupted markers—raise a conflict and preserve the file for explicit reconciliation.  
An early warning block may be added manually once backed by verified data; if a conflict arises later, reconcile it with the rendered block rather than overwriting the entire card.  
An explicit verified `red_flags: []` removes a prior managed block while preserving the historical grounds in the KB.  
Before publishing the final response, reproduce the exact same set and statuses of active Red Flags at the very beginning of the response with chat-adapted links; never rewrite prior journal responses.  

In `websites`, explicitly list each client or target project URL (or `null`), its role (`client|target`), and its `basis_id` from `identity`.  
The root `.md` displays these addresses, their score, and the link to the proof; the folder name is never used as confirmation.  
`Progress.md` is updated in place without accumulating historical copies, whereas primary evidence, analysis versions, and review packages are archived.  

## Independent Review

```text
python <tool> prepare-review <project> --parent <parent-UUID> --spec <review-JSON> --response-file <exact-candidate>
```

The specification contains `risk`, `basis`, `request_scope`, `task_flags`, `claim_ids`, and `claims`; see [review.example.json](review.example.json).  
Each entry in `claims` specifies `claim_id`, the exact `response_excerpt`, and `novelty` (`new|restatement`); every standalone numeric figure in `response_excerpt` must appear in the verified sources of the linked claim.  
For an analytical response, `claims` and `claim_ids` must be non-empty, and the auditor substantively verifies that the map covers all material claims in the response.  
A purely procedural status note is recorded via `record_step` and never receives analytical clearance through an empty claim map.  
Valid `task_flags`: `new_causal_analysis`, `architecture_change`, `pricing_change`, `admin_configuration`, `business_impact`, `material_analysis`; an empty list is permissible only for a justified routine task.  
The minimum risk category is recomputed from new typed claims; `routine` cannot bypass material causal conclusions, hidden settings, or architectural/pricing changes.  
A `restatement` requires a previously approved, unchanged version of the claim and its evidence; `significant` requires two independent A.A auditors.  
Delegate using the platform's native subagent tool: in Antigravity call `invoke_subagent` with `TypeName: self` and `Model: inherit`; in Codex call `spawn_agent` with role A.A and the parent-selected model/effort.  
Pass the exact project root and full `package` path returned by `prepare-review`; the v2 package binds the current requests, exact response bytes, claim map, KB, primary Evidence, and manual inputs.  
In both platforms, the auditor first runs `review-input <project> --package <path> --platform <platform>` to obtain the neutral `report_contract` listing all valid field values (`approved`/`needs_changes`, `supported`/`qualified`/`unsupported`, `direct`/`proxy`/`irrelevant`, and `findings` schema); in Codex, this receipt also binds an encrypted spawn assignment to the package.  
State a neutral goal: audit the five stages, primary evidence, alternatives, KB consistency, and the exact response candidate, including completeness of its claim map.  
Never pass a desired verdict, a one-sided JSON template (containing only `"approved"`, `"supported"`, `"direct"`, or `"findings": []`), or another reviewer's report to the auditor; the reviewer operates strictly read-only inside the current project root without calling write tools, generating JSON via external scripts, or reading neighboring `daily` folders.  
The independent auditor returns its `schema_version: 2` JSON report in its final native message: `package`, `package_sha256`, `scope` (five stages + `kb_consistency` + `response`), `result` (`approved|needs_changes`), `claim_reviews`, and `findings`.  
For each claim, `claim_reviews` records `claim_id`, `observed`, `inferred`, `method`, `alternatives`, `limits`, `falsification`, `raw_vs_criteria`, and `outcome` (`supported|qualified|unsupported`); when `outcome: supported`, every standalone number in the claim and `response_excerpt` must be explicitly confirmed in `observed` or `test_alignment.tested_claim`.  
The mandatory `test_alignment` object specifies `target_claim` (the exact `essence` of the claim), `tested_claim`, `relationship` (`direct|proxy|irrelevant`), `rationale`, and `counterexample`.  
A `proxy` alignment permits at most `qualified` with a visible qualification in the response; `irrelevant` requires `unsupported`, which blocks `approved`.  
Audit the alignment classification substantively: non-empty string fields do not prove that a test actually verified the full target claim.  
When `outcome` is `qualified`, the mandatory `response_qualification` string must appear verbatim in the candidate response.  
`falsification` evaluates whether the test could have refuted the claim; `raw_vs_criteria` compares raw artifacts against pre-registered criteria rather than a desired conclusion.  
Each finding in `findings` specifies `id`, `claim_ids`, `severity` (`minor|significant|critical`), `description`, and `status` (`open|resolved|rejected`); parent handling records `disposition` and `evidence`.  
`needs_changes` and `open` findings persist and block completion; a parent disposition never converts an auditor's `needs_changes` verdict into `approved`.  
After updating the KB, prepare a new package and review for the revised version; the reviewer audits the affected claims without requiring re-collection of unchanged evidence.  
To clear a prior `needs_changes` verdict from another auditor, a new independent `approved` report must include `addresses_reviews` (`review_id`, `basis`, and `evidence`); a parent-authored JSON file or renamed package never clears a prior rejection.  
Switching parent chats likewise does not clear a rejection covering the same requests, response, and grounds; native provenance of every new review is verified independently.  

```text
python <tool> native-review-proof <project> --parent <UUID> --reviewer <child-AA-UUID>
python <tool> record-review <project> --parent <UUID> --reviewer <child-AA-UUID> --report <auditor-JSON> --native-evidence <proof-from-previous-command>
python <tool> review-disposition <project> --parent <UUID> --review-id <review-ID> --finding-id <finding-ID> --status resolved --basis <basis> --evidence <primary-evidence>
```

The native proof receipt is generated after the child auditor finishes and is passed as a separate argument, since the auditor's final message cannot reference a future completion receipt.  
`record-review` verifies that the report file matches the child A.A's final native message; verdict and disposition records are immutable and never reuse an overwritable `self-review.json`.  
The proof is extracted from the active platform's native store: verified parent-to-child A.A link, absence of prompt bias (`prompt_bias_issues`), read-only reviewer isolation (`reviewer_isolation_issues`), model selection, and clean completion.  
An unfinished subagent or a run lacking a review package assignment never counts as an A.A audit.  
Codex verifies actual `model`/`effort` against the parent's native `spawn_agent` call; Antigravity reads available generation/executor metadata and configuration.  
Unknown model versions or effort levels remain `unverified`.  
`native-executor-metadata <project> --conversation <UUID> --role primary|AA|AF [--parent <UUID>] [--save]` inspects `requested`/`observed` metadata, sources, and verification status; `--save` writes an immutable snapshot.  
A.A evaluates the substantive meaning of reviews and sources; a programmatic receipt alone does not prove truth.  

## Journal, External Export, and Metrics

```text
python <tool> record-answer <project> --response-file -
python <tool> stage <project> finalize --input "ꘖ/KB/Analysis.json" --output "ꙮ/1 - Analysis/res/<N>.md"
```

`record-answer` (invoked directly or via `answer-prepare`) binds all adopted, unrecorded exact requests to a single actual final response, writing complete `req/res` pairs and an explicit shared-response group.  
Only the exact bytes of the approved candidate may be recorded; any edit to the response requires a new review package even if the KB is unchanged.  
UI message delivery is distinct from file recording; publish in chat the exact saved response bytes.  
After a publication crash, recover the response from the saved group without inventing intermediate messages.  
Build the full `Context.md` export after completing the A.A review, KB consistency check, and journal recording, for manual submission to an external agent.  
Pass specific topical KB modules and primary sources to internal subagents; they do not use `Context.md`.  

`metrics` parses explicitly selected complete JSONL traces without copying private reasoning or launching models.  
Optional `--project <project>` attaches registered cache hits, fresh fetches, searches, method changes, and finding dispositions; prior unregistered activity remains `unknown`.  
For per-stage breakdowns, optional `--bindings` maps `conversation UUID -> [{stage, first_step, last_step}]`; unmapped steps are grouped under `unassigned`.  
Duplicate exports of the same step are deduplicated; missing token fields remain `unknown`, and cache reads are tracked separately.  
Token counts do not equal quota percentages or billing currency; quality is judged by evidence completeness, reviewer findings, and their resolution.  
