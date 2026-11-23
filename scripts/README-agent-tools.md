# Environment and Interface

`/upwork-cleanup` is the shared skill for cleaning up empty auto-created projects across enabled environments and instances declared in `../runtime.json`.  
The internal command `upwork_project.py cleanup --platform codex` (or `antigravity`) shows a dry-run preview; `--apply` removes registrations across active enabled instances and emptied Folders branches while skipping disabled instances/environments.  
Criterion: strictly older than 72 hours and zero conversations across all enabled instances, including archived and child conversations, matched by project ID or working directory.  
Unknown conversation history blocks deletion of the corresponding project.  
Projects with confirmed conversations are excluded from legacy `/upwork-init` provenance warnings: they are counted in `preserved` and `discovery.excluded_with_conversations`, and reported to the user only in the total preserved count.  
A closed required Codex profile yields `pending` without queuing a deferred deletion; re-run the command after opening that profile.  
A partial deletion records a minimal `cleanupHold` until the next run, which finishes native cleanup and removes bindings from the shared catalog.  
All of `proposals/daily` remains untouched on disk; its `ꘖ/data/projects.json` serves as the historical job index.  
For new `init` runs, the exact creation timestamp is stored in `ꘖ/project.json:created_at`; re-running `init` preserves it.  
Before publishing the final `/upwork-cleanup` response, pass it via stdin to `cleanup-report --answer - --platform <platform>`.  
The command saves the full text to `AI/harness/Ⰿ/≺/Logs/Cleanup/☰/YYYY/MM/DD--HH-mm.md`, prepending a first line `YYYY-MM-DD HH:mm UTC+3` in `Europe/Istanbul`, and returns the verbatim `answer` field for chat publication.  
Multiple reports within the same minute receive suffixes `--2`, `--3`, etc.; prior logs are never overwritten.  

The user starts with `/upwork-init <URL>` and continues with ordinary messages in the same chat.  
Work on the same directory may be resumed in a new chat of the other platform, including semi-manual proposal preparation under a separate instruction.  
All commands below are executed by the agent; Python 3.12+ is required, with dependencies listed in `requirements-agent-tools.txt`.  
General entry point: `python <scripts>/harness.py <command> --help` (`upwork_project.py` remains a backward-compatible alias).  
A single shared library services declared agent environments and instances; workspace root, daily directory, environments, per-instance `enabled` toggles, `system_paths`, subagent selection policy, and time zone are defined in [runtime.json](../runtime.json) (schema v2), while filesystem roots, tool binaries, central stores, relocations, platform layouts, and project topology profiles live in [paths.json](../paths.json) (`R`, schema v1) using `${VAR}` and `%ENV%` template variables.  
Individual projects may override or extend variables, paths, tools, `code_repos`, `similar_projects`, and external `linked_roots` via a local overlay (`R+`) at `.agents/paths.json`, `_/ꘖ/paths.json`, or `ꘖ/paths.json` (in addition to named `similar_projects` groups and `affiliated_paths` declared centrally in `paths.json`), with versioned filesystem profiles (`fs_version: 1` for legacy `V1` layouts and `fs_version: 2` for `O` / `V2` layouts using `🕮/`, `ꙮ/{≻,≺}`, and `Ⰿ/{≻,≺}`) and independent journal versioning (`journal_version`: `1` legacy `req`/`res`, `2` flat `≻`/`≺`, `3` `O-ꙮ` 20-entry subfolders `1–20`, `21–40`, …); `paths [<project>] [--expand <template>] [--check]` inspects and validates `R` and all discovered `R+` overlays, and `journal-upgrade <project> [--journal <dir>] [--dry-run]` upgrades `ꙮ` to `O-ꙮ` (`journal_version: 3`, also executed automatically on the next project operation without altering `V1` paths outside `ꙮ`).  
<!-- https://github.com/dmitry-ai/harness/issues/96 -->  
<!-- https://github.com/dmitry-ai/harness/issues/109 -->  
Pass `--platform <env>` to every operation; omitting the flag preserves Antigravity compatibility.  
Codex resolves active instances from `CODEX_HOME`, or accepts an explicit `--codex-profile <id>` or `--instance <id>` (usable across platforms).  
`instances [--platform <env>] [--instance <id>] [--conversation <uuid>] [--only-enabled]` inspects configured environments, per-instance `enabled` status, and exact `system_paths` to support usage-limit handoffs and cross-instance audits (`metrics [--conversation <uuid>] [--instance <id>]`).  
On `extract`, `--profile` continues to select the extraction profile.  
The configured `platforms.codex.registration_profile` is used only when registering from an environment without `CODEX_HOME`; reading native evidence remains bound to an explicitly known profile.  
Platform adapters live in `agent_tools/platforms`, while domain logic, KB, journaling, stages, and context export are shared.  
`doctor` reports the version digest across all static tools, rules, and references, along with configured environments/instances and launch parameters.  
An unchanged static `doctor` result may be reused; the selected browser tab, active model, and actual rule loading are verified separately per session.  
`install-global` connects all enabled Antigravity and Codex instances declared in `runtime.json` to shared native sources (skipping disabled instances unless selected explicitly via `--target-profile`).  
Repeat `--target-profile A6 --target-profile C2` for a pilot; `--platform` and `--codex-profile` continue to identify the executing session.  
Antigravity profile manifests inherit `platforms/antigravity/{rules,skills,agents}.json`, global `hooks.json` synchronizes `platforms/antigravity/hooks.json` (including `PreToolUse` gates and `final-turn-gate` `PreInvocation` + `Stop` handlers), and only exact plain legacy Harness entries are retired.  
Codex profile skill directories link to the original skill folders; individual `agents/<name>.toml` file symlinks point at `platforms/codex/agents`, and a compact personal `AGENTS.md` block loads `platforms/codex/AGENTS.md`.  
The installer removes only its exact receipt-owned former role configuration block, preserving later personal settings and refusing edited same-name roles.  
Unrelated personal instructions, skill folders, TOML tables, manifest entries and hooks are preserved; unrecognized edits or wrong-target links return a conflict before mutation.  
`install-global --check` verifies shared sources and selected profile connections without creating locks, receipts or files (`valid: false`, exit code `2` when migration is needed).  
Its `verification: filesystem-only` does not establish model-context delivery or live hook execution; test a fresh chat separately.  
Profile backups and ownership live centrally under Harness `ꘖ/data/native-profiles`; repeated installation is idempotent and failed writes attempt a guarded rollback.  
The legacy Antigravity-only Python installation API remains available and `doctor` checks those global connections as `global_customizations`.  
Each Antigravity profile has its own `USERPROFILE` and thus its own global configuration: a manifest present in one profile does not load rules in another.  
`build-native [--root <root>] [--check]` builds or verifies the shared platform definitions and the selected project's instruction loader from canonical rules and `runtime.json`.  
Both `build-native` and `install-global` publish shared definitions through the same central ownership receipt and installation lock; project receipts own only project files.  
An existing project receipt relinquishes its former shared-definition entries without deleting the shared files.  
Python code is never copied into projects.  
The build retains the selected project's root `AGENTS.md` and compatible native `developer_instructions` while generating platform definitions once in the shared checkout.  
It never creates project `SKILL.md` wrappers or project role copies; owned legacy projections are retired only by exact receipt hash, with immutable backups.  
Other projects are not scanned or changed: their owned copies retire during their next explicit `configure` or `build-native` operation.  
The primary chat model and effort are chosen in the UI; `build-native` does not hardcode them.  
`AGENTS.md` is created when `build-native` runs prior to a new chat so the new session reads the ready file.  
`build-native --check` only verifies presence and currency without writing.  
Unrelated TOML sections are preserved.  
Managed files are guarded by SHA-256 digests in `ꘖ/data/native-config.json`; an unrecognized manual edit raises a conflict instead of being overwritten.  
Changing the set of rule paths, roles, or `runtime.json` requires running `build-native`, then `build-native --check`, and starting a new chat; edits to the body of existing rule files are read live from their canonical paths.  

Detailed command order, stages, and source rules are in [workflow.md](../skills/upwork-init/references/workflow.md).  
Exit codes of `harness.py` / `upwork_project.py`: `0` — operation succeeded; `1` — input, structure, or runtime failure; `2` — validation, browser-check requirement (`browser_check_required: true`), or publication requires action.  
JSON output always includes the full `diagnostics` list rather than stopping at the first error.  
File existence and a green validator do not prove substantive truth or a completed analysis.  

# Creation and Continuation

`inspect URL --output <new-dir>/source.json [--tab-id <ID>]` reads the explicitly selected browser tab once.  
The snapshot records `observed_at`, `coverage`, available client history, and errors; `history_complete=false` must never be interpreted as complete history.  
Attachments are saved alongside the snapshot subject to filename, host, and size guards and credential stripping across redirects.  
`init URL --from-json source.json --domain <domain-or-topic> --date YYYY-MM-DD` performs no browser requests.  
The date is the initial request date in `Europe/Istanbul`; website ownership is never established by the folder name.  
`--site-hypothesis site.json` supplies a separate DOC-2 hypothesis containing `id`, `essence`, `for`/`against`, `probability_percent`, and `assessment_basis`.  
Each argument entry contains `argument`/`source`/`quote`; absence of contrary evidence is documented via `counterevidence` per the contract below.  

`init` creates a `𑀣` (`fs_version: 2`, `journal_version: 3`) project by default (while preserving existing `fs_version: 1` projects), creating `readme.md` (legacy `.md`), `🕮/Project.md` (legacy `KB/Project.md`), `Ⰿ/{≻,≺}`, `ꘖ/KB`, `ꙮ/{≻,≺}`, an immutable SHA-256 snapshot, hash-verified attachment copies, and the shared native manifest.  
Re-running the internal operation preserves the sequence number, manual documents, and IDs; normal continuation never re-runs `init`.  
An active daily project is registered under `Upwork / Proposals / YYYY / MM / DD`, verifying `project_id`, `folder_id`, and `folder_path`.  
In Codex, registration uses Shared-Projects via the UI helper: `shared_id`, the shared catalog/assignment, and `profiles` with distinct native C1/C2 IDs.  
No direct writes are made to `catalog.json`, legacy `ui-folders.json`, or Codex SQLite stores.  
Initial native creation may wait for source-profile folder trust: `complete=false`/`status=pending` is saved in `ꘖ/data/registrations.json`, and `register` is retried until confirmed.  
Secondary profiles are populated only after observing a genuine source registration.  
`register <project>` completes registration alone while preserving IDs, settings, and conversations.  
`configure <project>` merges manifest bindings and updates generator-owned projections while preserving user sources and settings.  
Standard `init`/`register` target enabled platforms in `runtime.registration.targets` and all enabled Antigravity instances; `--platform` marks the executing environment, while `--target` on `register` repairs a single platform registration.  
`complete` refers to the active environment and `all_registered` to all configured registration targets; a secondary error or pending state is saved for retry and does not block work in the active environment.  
Shared `registration.py` validates the name, root, folder, and native IDs, records `intent` prior to the call and the attempt/outcome afterward; `last_success` preserves prior confirmed IDs if a later retry fails.  
A manual mismatched title is never silently renamed: a conflict reports both the expected and actual values.  
`configure` merges mandatory Antigravity manifest entries with existing ones.  
The shared workspace loader directs the agent to read the project's local rules and `rules.json` path entries; a local `developer_instructions` key is written only when a manual override already exists, preserving its text, and otherwise parent instructions are inherited.  
All other TOML keys are preserved, and any verified tool-owned `CODEX.md` is retired.  
Duplicate rule paths are deduplicated; `inherits`/`include_only`/`exclude` selectors currently require explicit resolution and return a diagnostic error rather than an incomplete projection.  
`configure --check` validates bindings for all configured environments and project projection currency without writing.  
Legacy standard `context.json` files are upgraded to `draft-or-final` selection while archiving the original bytes in `config-history`; custom user configurations are left untouched.  
`--no-register` is reserved for isolated testing, never for real analysis.  

`status <project>` reads the agent KB, file hashes, registered questions, and workflow stages.  
`scope=initial_analysis` explicitly bounds the meaning of stage statuses; `proposal_artifacts` lists existing `draft`/`final`/previous snapshot files separately.  
`ꘖ/data/continuation.md` records the current instruction, working files, and next step for cross-platform handoff; its presence does not certify proposal readiness.  
During semi-manual proposal work, read the exact journal and user-indicated deliverables (`Ⰿ/≻/♕/🖂/Letters/**` or legacy `result/**`), snapshot any existing `draft.md` with `snapshot_draft.py`, and execute the specific instruction.  
No new automated proposal stages are added; switching UI platforms does not require re-running `inspect`/`init` or re-collecting evidence.  
`resume <project> --reason <reason> [--request-file <exact-text>]` verifies the prior snapshot, records continuation state, and updates `Progress.md` inside the agent KB without reading `Context.md`.  
`adopt-requests <project> --conversation <UUID>` imports the exact user messages for the job from the active platform's local native store (`USER_INPUT` in Antigravity or user messages in Codex).  
Unsupported store formats are diagnosed without reconstructing text from summaries; history from the other platform and prepared responses are preserved.  
`stage` accepts explicit `--input`/`--output` paths; any change to their hashes marks downstream stages stale.  
An unfinished legacy project is never declared complete merely because `Analysis.json` exists.  

# Research and Evidence

A question specification contains `id`/`question`/`impact`/`done_when`/`inputs`/`outputs`/`requirements`; see [question.example.json](../skills/upwork-init/references/question.example.json).  
`question-add`, `question-claim`, `question-finish`, `question-handoff`, and `question-search` enforce a single owner, record results or gaps, and require a method change after three empty searches.  
This is a coordination registry rather than a hook intercepting built-in `search_web`; the agent follows it in the UI.  
A.A/A.F invocations receive exact existing input paths, a bounded write scope, and an explicit completion criterion.  
Deterministic scripts compare bytes, hashes, and JSON pointers; A.A evaluates causation and meaning; A.F extracts and structures data where model judgment is needed.  

`collect <project> --plan <JSON> [--browser auto|always|never]` performs batch GET and browser DOM observations and extractions; when writing to an existing report in `ꘖ/KB/Evidence/*.json`, it merges prior `results` without losing earlier observations.  
`collect-http <project> [<URL> ...] [--url <URL> ...] [--profile|--extract-profile html|shopify|tracking|document|auto] [--browser auto|always|never] [--session-id <id>] [--cdp-port <port>]` performs single-URL or multi-URL batch observations (accepting both positional `<URL>` and repeatable `--url <URL>`) and, under `--browser auto` when HTML returns `401`/`403`/`429`, `word_count: 0`, or an anti-bot/JS challenge (`browser_check_required: true`), automatically falls back to a managed ephemeral `chrome-headless-shell` instance (`--remote-debugging-port=0`) for `scope="public"` (never touching the user's live Chrome without an explicit `--session-id`).  
`collect-browser <project> [<URL> ...] [--url <URL> ...] [--profile|--extract-profile html|shopify|tracking|document|auto] [--session-id <id>] [--cdp-port <port>]` captures post-JS DOM for one or more URLs in an isolated `chrome-headless-shell` context for `scope="public"`, or inside the verified primary Chrome profile (`Default` in `runtime.json → text.browser.sessions`, verified via the `M-2A` unpacked MV3 offscreen anchor in `browser_extension/` or the `M-2B` isolated `https://harness-profile.invalid` sentinel) when `--session-id` is supplied, opening a hidden/background session target without ever hijacking existing open user tabs; `browser-anchor` checks `M-2A`/`M-2B` verification status or initializes the `M-2B` sentinel on an explicit `Default` tab.  
`evidence-query <project> [<URL> ...] [--url <URL> ...] [--anchors] [--grep <pattern>] [--context-lines <N>] [--max-matches <N>]` inspects saved `ꘖ/KB/Evidence/HTTP` observations without loading full `extracted-*.json` files into model context, returning compact JSON per observation (`status`, exact `<title>`, `h1`, semantic `#anchor` list and heading-to-anchor index under `--anchors`, compact `#LC1..#LCN` range for GitHub source blobs, and multi-line verbatim paragraph/line windows with section or line anchors around `--grep` matches).  
[collection.example.json](../skills/upwork-init/references/collection.example.json) is illustrative: `example.invalid` is not a real source.  
Extraction profiles: `html` (title/meta/meta_all/canonical/text/sections/anchors/links/JSON-LD), `shopify` (public JSON plus a deterministic `summary` across object arrays: `record_count`, `timestamp_ranges`, `field_counts`), `tracking` (identifiers and literal JSON), and `document` (text/PDF/DOCX with Markdown formatting, plus `summary` for JSON).  
`extract <project> <observation> --profile <name>` re-extracts from a saved response without making a new HTTP request.  
`extract-file <project> <project-relative-path> --profile document` saves the extraction alongside the source file's SHA-256 digest.  
`sync-attachments <project> [--media-descriptions <JSON|->] [--no-fetch-videos]` synchronizes all client attachments into both the root `source/` folder and `ꘖ/KB/Evidence/Attachments/`, extracting verbatim Markdown of documents (PDF, DOCX, TXT, MD, etc.), video transcripts (including Loom), and image descriptions into both knowledge bases (`🕮/Project.md` / legacy `KB/Project.md` and `ꘖ/KB/{Project,Projects,Evidence}.md`).  
Complete raw responses and metadata stay in `Evidence`; selected excerpts may be passed to a model.  
Distinct URLs, headers, scopes, or contexts produce distinct cache keys; secret header values are redacted from saved metadata.  
By default, successful responses are cached for 24 hours and errors for up to 5 minutes; `refresh_reason` records the reason for forcing a fresh capture.  
HTTP 403/404 is a completed observation of unavailability, not a reason for blind retries.  
An extraction failure preserves the pointer to the saved raw response so another profile or validator can inspect it.  
Post-JS DOM is captured via the separate `capture-dom` command for an exact URL, explicitly chosen `tab-id`, and `--session-id` from `runtime.json → text.browser.sessions`, after verifying the browser profile and without navigating; an unknown HTTP status remains unknown.  
The GET collector does not execute JavaScript; static tracking markup does not prove runtime execution, and a product JSON endpoint is not a merchant feed.  

# Analysis Contract

New publications require `schema_version: 3`: first-class `facts`, knowledge type/status, observation scope, primary `evidence`, versioned `derived_from`, and `missing_checks`.  
The exact contract and method boundaries are defined in [evidence-contract.md](../skills/upwork-init/references/evidence-contract.md).  
Readable legacy v1/v2 files are used only for diagnostics and recovery, without automatic promotion to `verified`.  
[analysis.example.json](../skills/upwork-init/references/analysis.example.json) and its companion `source`/`observation` files are explicitly synthetic offline fixtures, never client facts.  

`save-analysis <project> --candidate <JSON|-> [--expected-sha256 <current-hash>]` validates structure and primary provenance and archives history; updating an existing JSON file requires its current SHA-256.  
`render-analysis <canonical ꘖ/KB/Analysis.json> [--output <Markdown>]` validates v3 and evidence and preserves prior publications; manual edits to a rendered file save the candidate separately and report a conflict.  
`validate-analysis <JSON> --format json --evidence` reads and diagnoses legacy schemas as well; `--render` enforces full new-publication requirements.  
Hypotheses in `causes` and `misconceptions` record alternatives and a discriminating check; unverified hypotheses with an empty `against` list are capped at `probability_percent <= 75`; in verified `observation`/`client_report` claims, every standalone number in `essence` must be backed by primary quotes or calculations; recommendations require applicability conditions and a result verification criterion; `high`/`critical` impact requires versioned grounds.  
`percent_change` calculations are verified with exact `Decimal` arithmetic against source numbers, identical units, an explicit formula, and rounding; expert percentages are not measurements.  

`prepare-experiment <project> --spec <JSON|->` freezes the experiment plan before observation, including disconfirming criteria.  
`record-experiment <project> --spec <JSON|->` records an immutable experiment run, real artifacts, native actions, conditions, and outcome; it never executes browser actions or code from the specification.  
Assertions evaluate raw saved artifacts: an outcome that fails the expected criteria cannot be turned into `verified` by prose in a report.  
Amending criteria creates a new plan version via `--amendment-of`/`--amendment-reason` and requires fresh observations; failed or inconclusive runs remain in history.  
`question-finish` accepts `--results <JSON|->` for each requirement, including specific unavailable checks; a qualified result is valid.  

`red_flags` references `identity` claims; criteria and statuses are in [Red Flags](../skills/upwork-init/references/workflow.md#red-flags).  
Rendering places active risks at the top of the report and synchronizes the managed level-1 section at the end of `readme.md` (legacy root `.md`) while preserving authored text and history.  

# Substantive Audit and KB

Internal agents use `ꘖ/KB` and primary evidence; `Context.md` remains an external export.  
`prepare-review <project> --parent <UUID> --spec <JSON|-> --response-file <text|->` freezes the current requests, exact response bytes, claim map, KB digests, and Evidence, verifying that all standalone numbers in `response_excerpt` are backed by primary sources.  
The `risk`/`basis`/`request_scope`/`task_flags`/`claim_ids`/`claims` specification has no default `routine`; see [review.example.json](../skills/upwork-init/references/review.example.json).  
The tool recomputes the minimum risk category from the types of new claims; significant conclusions require two independent A.A auditors, while a routine restatement requires proven unchanged grounds.  
The auditor receives the package, sources, and response candidate without a desired verdict, one-sided JSON template, or another auditor's report.  
Across configured environments, the auditor first runs `review-input` to obtain a neutral `report_contract` listing all valid outcomes; in Codex this also binds an encrypted spawn assignment to the package.  

The authored schema v2 JSON report covers the five stages, `kb_consistency`, `response`, and every mapped claim; it evaluates the method, alternatives, limitations, ability of the test to falsify the claim, and agreement between raw results and pre-registered criteria (when `outcome: supported`, every standalone number in the claim and `response_excerpt` must be confirmed in `observed` or `tested_claim`).  
An independent auditor operates strictly read-only inside the current project root and returns this JSON in its final native message; `native-review-proof` is generated after completion and verifies the absence of `prompt_bias_issues` and `reviewer_isolation_issues`.  
`record-review --report <JSON|-> --native-evidence <proof>` matches the JSON against the native final message and writes an immutable record.  
For a routine `self_review`, specify `review_kind` explicitly with identical `parent` and `reviewer` IDs; self-review is not an independent audit.  
`needs_changes` and `open` findings persist and block completion; `review-disposition` records parent handling separately without overwriting the auditor's verdict.  
Any change to material conclusions, KB modules, evidence, or the response requires a new clearance; unchanged evidence collection need not be repeated.  
Detailed fields and commands are in [workflow.md](../skills/upwork-init/references/workflow.md#independent-review).  

`native-executor-metadata <project> --conversation <UUID> --role primary|AA|AF [--parent <UUID>] [--save]` reads actual metadata from the active platform, tracking `requested`/`observed` and verification status separately; `--save` writes an immutable snapshot.  
Codex compares model and effort against the parent's native spawn call; Antigravity checks the parent's native `invoke_subagent` selection against available generation/executor/model configuration metadata.  
Role mappings and the parent-driven subagent selection policy live in `runtime.json`; metadata inspection never launches models and never backfills unknowns from `runtime.json`.  
A programmatic receipt does not guarantee substantive truth: A.A evaluates meaning.  

# Exact Journal and External Export

`turn-begin <project> [--dry-run] --platform codex` establishes the native turn and applicability of FILE-3/EXEC-5/DOC-2 regardless of text format (`--dry-run` validates native ownership and hygiene checks without writing receipts or upgrading journals); Antigravity requires `--conversation <native-uuid> --platform antigravity` (and runs idempotent `turn-begin` automatically on the first `PreInvocation` of a primary turn in tracked workspaces via `check_pre_invocation.py`).  
`answer-check <project> --response-file <candidate-answer> [--conversation <native-uuid>]` runs all candidate-response gates (`LINK-4` / `LINK-5`, `DOC-4`, `DOC-2`, `VERIFY-1` / `ResponseEvidenceAuditor` / `local_source_grounding_issues`, `compaction_check`, `EXEC-5` / `issue_first_check`, `EXEC-2` / `tdd_check`, and `EXEC-5` / `code_lifecycle_check`) in one read-only pass for primary turns, Plan Mode, and child `A.A` / `A.F` subagents without writing to `ꙮ` or `ꘖ/data/turns` (exit code `0` when valid, `2` when validation issues are found).  
`answer-prepare <project> --response-file <exact-final-answer>` records the exact native requests and response (automatically prepending a tab-indented JSON metadata header to new journal response files while returning `body_sha256` alongside on-disk `response_sha256` so clean chat replies pass `check_stop_gate.py` and `journal-sync`), verifies read-back bytes and prior clearances of linked documents/analysis, and returns `response_file` and `ready: true`.  
`journal-sync <project> --conversation <native-uuid>` synchronously reconciles a completed native reply against the journal; a skipped preparation is recovered post-hoc, and any byte discrepancy is saved as a conflict without overwriting history.  
`sync-conversation-title <project> --conversation <native-uuid> [--journal <dir>] [--dry-run]` computes the sorted comma-separated project Journal `ꙮ` step numbers belonging to that conversation (e.g., `211` or `191, 204`) and updates the Antigravity conversation title via the active instance's local `LanguageServerService/UpdateConversationAnnotations` RPC (also executed automatically during Antigravity `turn-begin`, `answer-prepare`, and `journal-sync`).  
All journal execution is foreground-only: `turn-begin` reconciles earlier completed turns of its current conversation, and `answer-prepare` records the present response without registering or launching a persistent process.  
Native delivery is confirmed on the next foreground working call after publication; if no later call occurs, it remains unverified.  
`--no-watch` and the Python `watch` parameter are compatibility inputs and never enable autonomous work; on compacted turns, `turn-begin`, `recover-checkpoint`, and `answer-prepare` offload full `pre_checkpoint_records` and read/evicted file lists to `ꘖ/data/turns/<turn_key>-recovery/index.json` (keeping `stdout` concise), `recover-checkpoint <project> [--conversation <native-uuid>] [--dry-run]` supports a read-only `--dry-run` `file_index` (`SHA-256`, byte/line counts, and citation re-read flags) for Plan Mode without bypassing `COMPACT-1`, and confirmed `delivered` turns prune temporary `<turn_key>-recovery/` checkpoint directories.  
Repeated unchanged reconciliation preserves domain-state bytes, timestamps and mtime; real changes and conflicts are recorded without silently replacing history.  
New answers pass the current applicable document, source, and approval gates and retain an immutable admission proof; repeated historical verification checks the selected recorded sources and approvals without reapplying wall-clock freshness rules.  
Missing legacy admission proofs remain visible gaps, and prior failed admission is not bypassed by recovery.  
<!-- https://github.com/dmitry-ai/harness/issues/41 -->  
Exact guarantees and limits are in the [turn completion contract](../references/turn-completion.md#limits-and-verification); saved state does not prove rule comprehension, and preparation does not prove UI delivery.  

`validate_step.py --dir <journal> --all` validates pairs and checks for stale reservations.  
`recover-turn-violation <project> --conversation <native-uuid> [--reason <note>]` records a retrospective violation receipt in `ꘖ/data/turns/<turn_key>-violation-recovery.json` so `answer-prepare` can complete the journal with `answer-groups` receipts after an earlier `EXEC-5` or `http_fetch` tool-call violation in the same turn; direct writes to `ꙮ/**/req|res/*.md` and standalone `record_step.py` invocations are blocked by the PreToolUse gate.  
`similar-project-exempt <project> --peer <repo-or-root> --reason "<reason >= 30 chars>" [--conversation <native-uuid>]` records an audited technical exemption in `ꘖ/data/turns/<turn_key>-similar-exemptions.json` when changes in a declared `similar_projects` peer or `affiliated_paths` source do not apply to that sibling project.  
`ratchet-ok <project> --file <test-file> --reason "<reason >= 30 chars>" [--conversation <native-uuid>]` records an audited `RATCHET-OK` approval in `ꘖ/data/turns/<turn_key>-ratchet-ok.json` when a user decision or changed requirement genuinely requires modifying or removing an existing test expectation (test-fitting excuses are rejected; `RATCHET-OK:` lines in linked GitHub issue Evidence JSON are also honored).  
`tdd-check <project> [--conversation <native-uuid>]` runs read-only diagnostics of the active turn's `EXEC-2` Red-First TDD and Full-Suite-Green state (exit code `0` when valid, `2` when violations exist), complementing the live `PreToolUse` TDD/ratchet/behavioral gate in `check_rules_and_server_gate.py`, the Git `pre-commit` TDD/ratchet gate in `agent_tools/git_gate.py`, and the `Stop` gate in `check_stop_gate.py`.  
`issue-first-check <project> [--conversation <native-uuid>]` runs read-only diagnostics of the active turn's `EXEC-5` pre-TDD `Issue-First` state (verifying that an open parent/strategic GitHub issue was created or fetched strictly before any test, production code, or versioned deliverable write in a GitHub-backed repository; exit code `0` when valid, `2` when violations exist), complementing live `EXEC-5-ISSUE-FIRST-GATE` (`PreToolUse`, running strictly before `EXEC-2-TDD-GATE`), `df_github_issue.py` `pre_flight_issue_first`, Git `pre-commit`, and `check_stop_gate.py`.  
Service records in `ꘖ/data/.journal` are bound to the journal path, token, and SHA-256 digests; file publication is atomic.  
Legacy `record-answer <project> --response-file <exact-final-answer>` and `agent_tools.journal` (`record_step` / `recover_step`) remain as internal compatibility and recovery primitives; standard primary turn completion uses `answer-prepare`.  
Reserving the entire request group upfront prevents sequence gaps after crashes.  
`stage ... finalize` verifies the current KB, reviews, journal, emptiness of `ꘖ/data/scratch`, and absence of one-off scripts in the project without automatically building `Context.md`; this certifies response readiness rather than confirmed UI delivery.  

`generate_context.py [<project> | --root <project>] [--config <context.json>] [--output <path>] [--dry-run]` exports the current generation timestamp and the Agent Knowledge Base (`ꘖ/KB`: all `.md` files, strictly excluding the `Evidence` subfolder) to `Ⰿ/≻/♙/Context/output/Context.md` (legacy `ꙮ/0/Context.md`).  
If `--config` is omitted, it defaults to `default_context_config()`; custom manifests remain supported via `--config`.  
All paths are confined to the project root; an export never overwrites a source file.  
`Context.md` is built for manual submission to an external agent, primarily Gemini DeepThink; internal agents never use it as their working KB.  
<!-- https://github.com/dmitry-ai/harness/issues/42 -->  
<!-- https://github.com/dmitry-ai/harness/issues/116 -->  
<!-- https://github.com/dmitry-ai/harness/issues/117 -->  
<!-- https://github.com/dmitry-ai/harness/issues/118 -->  
<!-- https://github.com/dmitry-ai/harness/issues/119 -->  
<!-- https://github.com/dmitry-ai/harness/issues/120 -->  
<!-- https://github.com/dmitry-ai/harness/issues/122 -->  
<!-- https://github.com/dmitry-ai/harness/issues/123 -->  
<!-- https://github.com/dmitry-ai/harness/issues/139 -->  
<!-- https://github.com/dmitry-ai/harness/issues/147 -->  
<!-- https://github.com/dmitry-ai/harness/issues/152 -->  

# Additional Tools

`snapshot_draft.py <draft.md> --turn <ID>` saves exact bytes to a sibling `draft.prev.md` and the `ꘖ/data/.draft-snapshots` archive; repeating within the same turn preserves the initial baseline.  
`validate_links.py <files> --local-anchors` validates local file targets, heading anchors, and JSON pointers; `--unique-urls` enforces an explicit no-duplicate-URL policy.  
`validate_links.py --readable <files>` checks LINK-5 in authored Markdown/text/HTML source: authored links must preserve spaces and Unicode, whereas URI encoding performed by a downstream renderer is not flagged.  
Build new links with `agent_tools.links.markdown_link`; `readable_reference` strips unnecessary percent-encoding from paths and fragments while preserving significant query parameters and delimiters.  
`check-project`, `record-answer`, `finalize`, and shared publication helpers validate authored text while preserving verbatim quotes, code blocks, primary captures, and the exact journal.  
`validate_anchors.py <files> --include-code` checks raw HTML anchors over HTTP; it does not prove DOM state, authentication, or semantic applicability.  
Exit codes for standalone link tools: `0` — checks passed; `1` — input or local validation error; `2` — network check unconfirmed.  
`safe_commit.py --repo <root> --file <path> -m <message> [--execute]` verifies the exact Git index, unstaged/conflicted files, and Markdown links without running `git add` or `git push`.  
`harness.py git-read [root] [status|diff|log|rev-parse|show|ls-files] [--short] [--stat] [--check] [--arg <arg>]` (or `upwork_project.py git-read`) executes read-only Git commands strictly with `--no-optional-locks` and `GIT_OPTIONAL_LOCKS=0`; the `git_shim.py` wrapper (`shim/git.cmd`) intercepts read-only `git` invocations in `PATH` and injects `--no-optional-locks`.  
`df_github_issue.py [lint|fetch|create|edit|comment|close|audit-repo|transfer-repo] ...` performs deterministic fetching (`fetch` with read-back Evidence persistence for already-open parent issues), creation (enforcing `pre_flight_issue_first` dirty-repo rejection for unparented issues, `open`-parent verification for `--parent <N>`, and automatic tab-indented JSON metadata header prepending unless `--no-metadata` is specified), editing, commenting, closing, and auditing of GitHub issues from UTF-8 files without BOM (`--body-file`) via `gh api --input -` with pre-flight syntax linting and mandatory byte-exact read-back verification per the [df-github-issue](../skills/df-github-issue/SKILL.md) skill, as well as audited repository ownership transfers (`transfer-repo --repo <owner/repo> --new-owner <org>`) with read-back verification and Evidence persistence.  
`validate_statements.py <directory>` checks non-empty `.md` and `Test.md` files in numbered statement directories; it does not prove substantive truth.  
`metrics <trace.jsonl> ... [--bindings <JSON>] [--project <project>]` aggregates fresh input, cache read, output tokens, and tool calls from observed trace data, deduplicating repeated exports and keeping unknown fields unknown rather than zero.  

# Client Text

Article profile: [df-article](../skills/df-article/SKILL.md); Upwork proposal profile: [df-proposal](../skills/df-proposal/SKILL.md).  
Both profiles share the same [workflow](../references/client-text/workflow.md), [review contract](../references/client-text/review.md), CLI, and library.  
[Commands and schemas](../references/client-text/operations.md) cover `begin`/`check`/`apply`, the block map, `sources`/replay, native review provenance, and journaling.  
`df_article.py` and `df_proposal.py` select the format preset; `df_text.py` runs the shared operations without duplicating implementation code.  
`source-check` binds the exact URL, anchor, and quote from saved HTTP/DOM bytes to the candidate; `manifest.source_checks` is mandatory for all external URLs in the candidate, including mechanical edits.  
`lint --network --project <root>` also records failed probes.  
Clearance checks and reviewer `source_reviews` enforce the [unified source contract](../references/client-text/sources.md#mandatory-source-clearance).  
Substantive readiness requires primary evidence and independent clearance; a passing linter validates only its structural rules.  

# Regression Suite

Canonical parallel fail-fast runners: `python -m pytest <.agents>/tests -n auto --dist worksteal -x` (executes existing `unittest.TestCase` modules across CPU cores with worksteal load balancing, automatic `tests/conftest.py` path and `HARNESS_TEST_NO_FSYNC=1` setup, and fail-fast exit) and `python <.agents>/scripts/harness.py run-tests <.agents>/tests [--workers N] [--module-timeout 300] [--no-failfast] [--module <name>] [--format text|json]` (runs modules in longest-processing-time-first order with `-f` and `-b` enabled by default and cancels sibling processes immediately on first failure or module timeout); both satisfy `EXEC-2 TDD-FULL-GATE`.  
Direct `unittest` fallback must also enable fail-fast and a synchronous startup window (`WaitMsBeforeAsync: 10000`, enforced by `EXEC-2-TEST-FAILFAST-GATE` in `PreToolUse`): `python -m unittest discover -f -s <.agents>/tests -p test_*.py -v`.  
Subsystem references: [Worktrees, FIFO Landing Lease, and Parallel Testing](docs/worktrees-and-testing.md) and [Open-Closed Plugin Registries and Code Size Ratchet](docs/plugin-registries.md) (or run `harness.py cli-docs` for the generated command index).  
`UPWORK_CAPTURE_DIR` points tests to saved `*/source.json` fixtures; the test suite creates temporary directories and never modifies real projects or browser state.  
During cleanup, delete only temporary files created by your own run; preserve material evidence and active reservations.  
<!-- https://github.com/dmitry-ai/harness/issues/164 -->  
<!-- https://github.com/dmitry-ai/harness/issues/168 -->  
<!-- https://github.com/dmitry-ai/harness/issues/178 -->  

# Material Lifecycle

`incoming` is used solely for pre-import staging.  
`intake-drain` verifies `snapshot`/`job_id`, copies unique bytes into project `Evidence`, and writes a source-path → SHA-256/permanent-path manifest; `--apply` deletes only verified unchanged staging files.  
Incomplete or unrecognized captures are preserved.  

`save-analysis --candidate -`, `question-add --spec -`, `collect --plan -`, and `record-answer --response-file -` accept UTF-8 via stdin.  
A file input inside `<project>/ꘖ/data/scratch` passed with `--consume-input` is deleted after a confirmed write when its bytes are unchanged; by `finalize`, `<project>/ꘖ/data/scratch` must be empty.  
Without `--output`, `collect` still persists the captured response.  
The collector plan is stored in full inside publication provenance.  
Do not create one-off scripts inside projects (`check-project` rejects executable scripts in `ꘖ/data` and `.agents`).  

Canonical analysis publication updates the explicit `websites` block in the root project card: URL or `null`, role (`client|target`), and `basis_id` of the `identity` claim.  
The managed block protects surrounding manual text.  
User `🕮/` (legacy `KB/`) files are not modified.  
`Progress.md` is updated in place without archiving old navigation snapshots.  
Collector metrics maintain cumulative counters and the last 32 diagnostic events; legacy list formats migrate without losing known totals.  
