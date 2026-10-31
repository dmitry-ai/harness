# Environment and Interface

`/upwork-cleanup` is the shared skill for cleaning up empty auto-created projects in Antigravity and Codex C1/C2.  
The internal command `upwork_project.py cleanup --platform codex` (or `antigravity`) shows a dry-run preview; `--apply` removes registrations and emptied Folders branches.  
Criterion: strictly older than 72 hours and zero conversations across all three stores, including archived and child conversations, matched by project ID or working directory.  
Unknown conversation history blocks deletion of the corresponding project.  
Projects with confirmed conversations are excluded from legacy `/upwork-init` provenance warnings: they are counted in `preserved` and `discovery.excluded_with_conversations`, and reported to the user only in the total preserved count.  
A closed required Codex profile yields `pending` without queuing a deferred deletion; re-run the command after opening that profile.  
A partial deletion records a minimal `cleanupHold` until the next run, which finishes native cleanup and removes bindings from the shared catalog.  
All of `proposals/daily` remains untouched on disk; its `ꘖ/data/projects.json` serves as the historical job index.  
For new `init` runs, the exact creation timestamp is stored in `ꘖ/project.json:created_at`; re-running `init` preserves it.  
Before publishing the final `/upwork-cleanup` response, pass it via stdin to `cleanup-report --answer - --platform <platform>`.  
The command saves the full text to `AI/log/cleanup/YYYY/MM/DD--HH-mm.md`, prepending a first line `YYYY-MM-DD HH:mm UTC+3` in `Europe/Istanbul`, and returns the verbatim `answer` field for chat publication.  
Multiple reports within the same minute receive suffixes `--2`, `--3`, etc.; prior logs are never overwritten.  

The user starts with `/upwork-init <URL>` and continues with ordinary messages in the same chat.  
Work on the same directory may be resumed in a new chat of the other platform, including semi-manual proposal preparation under a separate instruction.  
All commands below are executed by the agent; Python 3.12+ is required, with dependencies listed in `requirements-agent-tools.txt`.  
General entry point: `python <scripts>/upwork_project.py <command> --help`.  
A single shared library services Antigravity and Codex; workspace root, daily directory, models, time zone, and paths are defined in `../runtime.json` (schema v2).  
Pass `--platform antigravity|codex` to every operation; omitting the flag preserves Antigravity compatibility.  
Codex resolves C1/C2 from `CODEX_HOME`, or accepts an explicit `--codex-profile C1|C2`.  
On `extract`, `--profile` continues to select the extraction profile.  
The configured `platforms.codex.registration_profile` is used only when registering from an environment without `CODEX_HOME`; reading native evidence remains bound to an explicitly known profile.  
Platform adapters live in `agent_tools/platforms`, while domain logic, KB, journaling, stages, and context export are shared.  
`doctor` reports the version digest across all static tools, rules, and references, along with existing paths and launch parameters.  
An unchanged static `doctor` result may be reused; the selected browser tab, active model, and actual rule loading are verified separately per session.  
`install-global` merges native skill/worker manifest entries while preserving other entries; it does not install project analysis rules globally.  
`build-native [--root <root>] [--check]` builds or verifies native Codex projections from the shared rules, skills, worker protocol, and `runtime.json`.  
Python code is never copied into projects.  
The build writes a root `AGENTS.md` containing a short loader for the canonical rules; the same loader is stored in native `developer_instructions` inside `.codex/config.toml` for compatibility, without creating a root `CODEX.md` or copying full policy bodies into role files.  
The primary chat model and effort are chosen in the UI; `build-native` does not hardcode them.  
`AGENTS.md` is created when `build-native` runs prior to a new chat so the new session reads the ready file.  
`build-native --check` only verifies presence and currency without writing.  
Unrelated TOML sections are preserved.  
Managed files are guarded by SHA-256 digests in `ꘖ/data/native-config.json`; an unrecognized manual edit raises a conflict instead of being overwritten.  
Changing the set of rule paths, roles, or `runtime.json` requires running `build-native`, then `build-native --check`, and starting a new chat; edits to the body of existing rule files are read live from their canonical paths.  

Detailed command order, stages, and source rules are in [workflow.md](../skills/upwork-init/references/workflow.md).  
Exit codes of `upwork_project.py`: `0` — operation succeeded; `1` — input, structure, or runtime failure; `2` — validation or publication requires action.  
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

`init` creates the root project card, manual and agent KBs, an immutable SHA-256 snapshot, hash-verified attachment copies, and the shared native manifest.  
Re-running the internal operation preserves the sequence number, manual documents, and IDs; normal continuation never re-runs `init`.  
An active daily project is registered under `Upwork / Proposals / YYYY / MM / DD`, verifying `project_id`, `folder_id`, and `folder_path`.  
In Codex, registration uses Shared-Projects via the UI helper: `shared_id`, the shared catalog/assignment, and `profiles` with distinct native C1/C2 IDs.  
No direct writes are made to `catalog.json`, legacy `ui-folders.json`, or Codex SQLite stores.  
Initial native creation may wait for source-profile folder trust: `complete=false`/`status=pending` is saved in `ꘖ/data/registrations.json`, and `register` is retried until confirmed.  
Secondary profiles are populated only after observing a genuine source registration.  
`register <project>` completes registration alone while preserving IDs, settings, and conversations.  
`configure <project>` merges manifest bindings and updates generator-owned projections while preserving user sources and settings.  
Standard `init`/`register` target both platforms per `runtime.registration.targets`; `--platform` marks the executing environment, while `--target` on `register` repairs a single platform registration.  
`complete` refers to the active platform and `all_registered` to both; a secondary error or pending state is saved for retry and does not block work in the active platform.  
Shared `registration.py` validates the name, root, folder, and native IDs, records `intent` prior to the call and the attempt/outcome afterward; `last_success` preserves prior confirmed IDs if a later retry fails.  
A manual mismatched title is never silently renamed: a conflict reports both the expected and actual values.  
`configure` merges mandatory Antigravity manifest entries with existing ones.  
The shared workspace loader directs the agent to read the project's local rules and `rules.json` path entries; a local `developer_instructions` key is written only when a manual override already exists, preserving its text, and otherwise parent instructions are inherited.  
All other TOML keys are preserved, and any verified tool-owned `CODEX.md` is retired.  
Duplicate rule paths are deduplicated; `inherits`/`include_only`/`exclude` selectors currently require explicit resolution and return a diagnostic error rather than an incomplete projection.  
`configure --check` validates bindings for both platforms and project projection currency without writing.  
Legacy standard `context.json` files are upgraded to `draft-or-final` selection while archiving the original bytes in `config-history`; custom user configurations are left untouched.  
`--no-register` is reserved for isolated testing, never for real analysis.  

`status <project>` reads the agent KB, file hashes, registered questions, and workflow stages.  
`scope=initial_analysis` explicitly bounds the meaning of stage statuses; `proposal_artifacts` lists existing `draft`/`final`/previous snapshot files separately.  
`ꘖ/data/continuation.md` records the current instruction, working files, and next step for cross-platform handoff; its presence does not certify proposal readiness.  
During semi-manual proposal work, read the exact journal and user-indicated `result/**` files, snapshot any existing `draft.md` with `snapshot_draft.py`, and execute the specific instruction.  
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

`collect <project> --plan <JSON>` performs batch GET observations and extractions; when writing to an existing report in `ꘖ/KB/Evidence/*.json`, it merges prior `results` without losing earlier observations.  
[collection.example.json](../skills/upwork-init/references/collection.example.json) is illustrative: `example.invalid` is not a real source.  
Extraction profiles: `html` (title/meta/meta_all/canonical/text/sections/anchors/links/JSON-LD), `shopify` (public JSON plus a deterministic `summary` across object arrays: `record_count`, `timestamp_ranges`, `field_counts`), `tracking` (identifiers and literal JSON), and `document` (text/PDF/DOCX with Markdown formatting, plus `summary` for JSON).  
`extract <project> <observation> --profile <name>` re-extracts from a saved response without making a new HTTP request.  
`extract-file <project> <project-relative-path> --profile document` saves the extraction alongside the source file's SHA-256 digest.  
`sync-attachments <project> [--media-descriptions <JSON|->] [--no-fetch-videos]` synchronizes all client attachments into both the root `source/` folder and `ꘖ/KB/Evidence/Attachments/`, extracting verbatim Markdown of documents (PDF, DOCX, TXT, MD, etc.), video transcripts (including Loom), and image descriptions into both knowledge bases (`KB/Project.md` and `ꘖ/KB/{Project,Projects,Evidence}.md`).  
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
Rendering places active risks at the top of the report and synchronizes the managed level-1 section at the end of the root project card while preserving authored text and history.  

# Substantive Audit and KB

Internal agents use `ꘖ/KB` and primary evidence; `Context.md` remains an external export.  
`prepare-review <project> --parent <UUID> --spec <JSON|-> --response-file <text|->` freezes the current requests, exact response bytes, claim map, KB digests, and Evidence, verifying that all standalone numbers in `response_excerpt` are backed by primary sources.  
The `risk`/`basis`/`request_scope`/`task_flags`/`claim_ids`/`claims` specification has no default `routine`; see [review.example.json](../skills/upwork-init/references/review.example.json).  
The tool recomputes the minimum risk category from the types of new claims; significant conclusions require two independent A.A auditors, while a routine restatement requires proven unchanged grounds.  
The auditor receives the package, sources, and response candidate without a desired verdict, one-sided JSON template, or another auditor's report.  
In both platforms, the auditor first runs `review-input` to obtain a neutral `report_contract` listing all valid outcomes; in Codex this also binds an encrypted spawn assignment to the package.  

The authored schema v2 JSON report covers the five stages, `kb_consistency`, `response`, and every mapped claim; it evaluates the method, alternatives, limitations, ability of the test to falsify the claim, and agreement between raw results and pre-registered criteria (when `outcome: supported`, every standalone number in the claim and `response_excerpt` must be confirmed in `observed` or `tested_claim`).  
An independent auditor operates strictly read-only inside the current project root and returns this JSON in its final native message; `native-review-proof` is generated after completion and verifies the absence of `prompt_bias_issues` and `reviewer_isolation_issues`.  
`record-review --report <JSON|-> --native-evidence <proof>` matches the JSON against the native final message and writes an immutable record.  
For a routine `self_review`, specify `review_kind` explicitly with identical `parent` and `reviewer` IDs; self-review is not an independent audit.  
`needs_changes` and `open` findings persist and block completion; `review-disposition` records parent handling separately without overwriting the auditor's verdict.  
Any change to material conclusions, KB modules, evidence, or the response requires a new clearance; unchanged evidence collection need not be repeated.  
Detailed fields and commands are in [workflow.md](../skills/upwork-init/references/workflow.md#independent-review).  

`native-executor-metadata <project> --conversation <UUID> --role primary|AA|AF [--parent <UUID>] [--save]` reads actual metadata from the active platform, tracking `requested`/`observed` and verification status separately; `--save` writes an immutable snapshot.  
Codex compares model and effort against the parent's native spawn call; Antigravity reads available generation/executor/model configuration metadata.  
Selection policy and defaults remain in `runtime.json`; metadata inspection never launches models and never backfills unknowns from `runtime.json`.  
A programmatic receipt does not guarantee substantive truth: A.A evaluates meaning.  

# Exact Journal and External Export

`turn-begin <project> --platform codex` establishes the native turn and applicability of FILE-3/EXEC-5/DOC-2 regardless of text format; Antigravity requires `--conversation <native-uuid> --platform antigravity`.  
`answer-prepare <project> --response-file <exact-final-answer>` records the exact native requests and response, verifies read-back bytes and prior clearances of linked documents/analysis, and returns the `response_file` to publish verbatim.  
`journal-sync <project> --conversation <native-uuid>` independently reconciles a completed native reply against the journal; a skipped preparation is recovered post-hoc, and any byte discrepancy is saved as a conflict without overwriting history.  
By default, `turn-begin` registers the active conversation with the hidden local verifier; `journal-watch --action status|once|start|stop` manages that watcher, and `journal-unwatch <project> --conversation <native-uuid>` removes a single registration upon explicit user opt-out.  
Exact guarantees and limits are in the [turn completion contract](../references/turn-completion.md#limits-and-verification); saved state does not prove rule comprehension, and preparation does not prove UI delivery.  

`record_step.py --dir <journal> --req-file request.txt --res-file response.txt [--step N]` writes exact UTF-8 bytes into the next free pair.  
`validate_step.py --dir <journal> --all` validates pairs and checks for stale reservations.  
`record_step.py --dir <same-journal> --recover N --token <token>` recovers an interrupted write without overwriting conflicting files.  
Service records in `ꘖ/data/.journal` are bound to the journal path, token, and SHA-256 digests; file publication is atomic.  
Legacy `record-answer <project> --response-file <exact-final-answer>` remains as a low-level compatibility and recovery primitive; standard primary turn completion uses `answer-prepare`.  
Reserving the entire request group upfront prevents sequence gaps after crashes.  
`stage ... finalize` verifies the current KB, reviews, journal, emptiness of `ꘖ/data/scratch`, and absence of one-off scripts in the project, then builds `Context.md`; this certifies response readiness rather than confirmed UI delivery.  

`generate_context.py --root <project> --config <project>/.agents/context.json [--dry-run]` includes all declared documents and the exact journal in full, preserving authors and boundaries.  
The `drafts` section selects a non-empty `final.md` in each language directory under `result/`, falling back to `draft.md`; both language versions are included, while `draft.prev.md` is never substituted automatically.  
An empty existing `final.md` blocks a new export while preserving the prior `Context.md` and all source files.  
Grouped requests are annotated as sharing a single response, while every original pair is preserved in full.  
Incomplete pairs/groups, an empty `final.md`, or a missing mandatory source file block overwriting the previous valid export.  
All paths are confined to the project root; an export never overwrites a source file.  
`Context.md` is built for manual submission to an external agent, primarily Gemini DeepThink; internal agents never use it as their working KB.  

# Additional Tools

`snapshot_draft.py <draft.md> --turn <ID>` saves exact bytes to a sibling `draft.prev.md` and the `ꘖ/data/.draft-snapshots` archive; repeating within the same turn preserves the initial baseline.  
`validate_links.py <files> --local-anchors` validates local file targets, heading anchors, and JSON pointers; `--unique-urls` enforces an explicit no-duplicate-URL policy.  
`validate_links.py --readable <files>` checks LINK-5 in authored Markdown/text/HTML source: authored links must preserve spaces and Unicode, whereas URI encoding performed by a downstream renderer is not flagged.  
Build new links with `agent_tools.links.markdown_link`; `readable_reference` strips unnecessary percent-encoding from paths and fragments while preserving significant query parameters and delimiters.  
`check-project`, `record-answer`, `finalize`, and shared publication helpers validate authored text while preserving verbatim quotes, code blocks, primary captures, and the exact journal.  
`validate_anchors.py <files> --include-code` checks raw HTML anchors over HTTP; it does not prove DOM state, authentication, or semantic applicability.  
Exit codes for standalone link tools: `0` — checks passed; `1` — input or local validation error; `2` — network check unconfirmed.  
`safe_commit.py --repo <root> --file <path> -m <message> [--execute]` verifies the exact Git index, unstaged/conflicted files, and Markdown links without running `git add` or `git push`.  
`upwork_project.py git-read [root] [status|diff|log|rev-parse|show|ls-files] [--short] [--stat] [--check] [--arg <arg>]` executes read-only Git commands strictly with `--no-optional-locks` and `GIT_OPTIONAL_LOCKS=0`; the `git_shim.py` wrapper (`shim/git.cmd`) intercepts read-only `git` invocations in `PATH` and injects `--no-optional-locks`.  
`df_github_issue.py [lint|create|edit|comment|close|audit-repo] ...` performs deterministic creation, editing, commenting, closing, and auditing of GitHub issues from UTF-8 files without BOM (`--body-file`) via `gh api --input -` with pre-flight syntax linting and mandatory byte-exact read-back verification per the [df-github-issue](../skills/df-github-issue/SKILL.md) skill.  
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

`python -m unittest discover -s <.agents>/tests -p test_*.py -v`.  
`UPWORK_CAPTURE_DIR` points tests to saved `*/source.json` fixtures; the test suite creates temporary directories and never modifies real projects or browser state.  
During cleanup, delete only temporary files created by your own run; preserve material evidence and active reservations.  

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
User `KB/` files are not modified.  
`Progress.md` is updated in place without archiving old navigation snapshots.  
Collector metrics maintain cumulative counters and the last 32 diagnostic events; legacy list formats migrate without losing known totals.  
