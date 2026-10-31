---
name: upwork-init
description: "Creates a project workspace and performs the five-stage initial analysis of an Upwork job post; use for /upwork-init and when resuming a saved analysis after an interruption or switching between Antigravity and Codex."
---
# Initial Upwork Analysis

Deliverable: complete initial project card, current self-consistent agent KB, five INIT-3 stages, resolved A.A review findings, exact journal, and complete external `Context.md` export.  
Material Red Flags appear at the very top of the report before detailed analysis and are duplicated at the end of the project's root `.md` inside a dedicated level-1 section (`# Red Flags`) per INIT-5.  
Internal agents work with `ꘖ/KB`, its overview/topical modules, and primary evidence.  
All agents format intermediate and final documents, including proposals, articles, and client letters, with human-readable links without URL encoding per [LINK-5](../../rules/02-link-standards.md#link-5).  
`Context.md` is built for manual submission to an external agent, primarily Gemini DeepThink via `https://gemini.google.com`.  

Shared rules are connected natively; read them directly if their full current text is not yet loaded in context.  
Determine the active platform and read only its adapter: [Codex](../../platforms/codex.md) or [Antigravity](../../platforms/antigravity.md).  
Pass `--platform` of the active environment to internal commands; inspect default models, effort, and profile settings in `runtime.json` via `doctor`.  
In Codex, verify native projections via `build-native --check`; if rule paths, roles, or `runtime.json` changed, run `build-native`.  
Canonical texts are read from their single source without creating `CODEX.md`.  
Tool: `C:/work/research/provision/code/AI/harness/code/scripts/upwork_project.py`.  
`doctor` reports version digests, existing paths, default models, and selection policy; it does not prove the active session model.  
Roles A.A/A.F, default models, and selection policy are defined solely by `runtime.json`; never substitute memorized model names.  
Verify available actual metadata and mark anything unknown explicitly.  
Models are invoked via native UI conversation tools; Python scripts never launch models.  
All commands below are executed internally by the agent; the user only enters chat requests.  

## New Project

The user starts with `/upwork-init <URL>`.  
Save the exact request and raw capture materials in a dedicated staging folder `AI/harness/_/ꘖ/data/incoming/<job_id>-<ID>`.  
Run `inspect <URL> --output <staging>/source.json` once; when multiple tabs match, pass an explicit `--tab-id`.  
Inspect all attachments and `coverage`; `history_complete: false` never means complete client history.  
All client-attached files must be saved simultaneously in the root `source/` folder of the project and in `ꘖ/KB/Evidence/Attachments/<sha256>/`.  
Include all attached text documents (PDF, DOCX, TXT, MD, etc.) verbatim and in full in both knowledge bases (`KB/Project.md` and `ꘖ/KB/{Project,Projects,Evidence}.md`) with proper Markdown formatting; transcribe all client-referenced videos (including Loom links in the job description or attached documents) in full with `[MM:SS]` timestamps; transcribe all attached images in full (verbatim text in `«»`, complete UI description, confirmations and contradictions against client statements with `%` scores) via `sync-attachments <project> --media-descriptions -`.  
If anything material could not be extracted automatically, inspect it via an available authenticated session with separate evidence or document the exact limitation.  

Name the project directory after the verified domain without scheme or `www`, or use a concise topic label when no domain is proven.  
Website ownership is established via a DOC-2 hypothesis rather than a folder name or bare URL mention.  
The `site.json` hypothesis specifies an explicit `website_url` (HTTP(S) or `null`, for the initial block in the root card), `id`, `essence`, `for`, `against`, `probability_percent`, and `assessment_basis`; each argument includes `argument`, `source`, and `quote`; documented absence of counterevidence is permitted under DOC-2.  
Run `init <URL> --from-json <staging>/source.json --domain <label> --date YYYY-MM-DD`, adding `--site-hypothesis <staging>/site.json` only when a website hypothesis is substantiated.  
Use the initial request date in `Europe/Istanbul`, not the continuation date.  
The initial manual `KB/Project.md` card is created once and ported in full into the agent KB along with all attachments in `source/`.  
After `init`, staging materials are imported into `Evidence` with hashes and an `intake-drain` receipt, and `incoming` is emptied; any incomplete capture is preserved.  
`intake-drain --apply` completes prior imports.  
When adding attachments or video/image transcripts later, run `sync-attachments <project>`.  
Subsequent research never overwrites manual `KB/Project.md`.  
When instructed by the user, maintain the managed website and Red Flags blocks in the root `.md` while preserving all other authored text and manual `KB/` per KB-1.  
In `Analysis.json`, populate `websites`: a non-empty list of `{url: HTTP(S) or null, role: client|target, basis_id: identity ID}`.  
Distinguish an intermediary agency's website from the target website; the folder name is never evidence.  
Standard `init` requests registration of the same directory in both platforms per `runtime.registration.targets`.  
Verify the actual project title `<domain-or-topic> - U.P.YYYY.MM.DD`, root path, native and shared IDs (when applicable), `folder_id`, `folder_path`, and the `Upwork / Proposals / YYYY / MM / DD` branch.  
Top-level `complete` refers to the active platform, while `all_registered` refers to both.  
Unavailability of the secondary platform is recorded for a later `register` retry and does not block analysis in the active platform; never report the secondary registration as complete while it is pending.  
An unfinished Codex registration returns `complete: false`; retry idempotent `register` and account for pending native folder-trust confirmation.  
In Codex, use Shared-Projects: one shared catalog and folder branch with separate native C1/C2 IDs; legacy `ui-folders.json` files are never edited.  
To finish an incomplete registration, run `register <project>`, which preserves existing IDs, settings, and conversations.  

## Resuming a Project

When the user writes `"Continue analysis. Analysis was interrupted due to ..."`, resume the same project.  
This also applies in a new chat of the other platform when the user specifies the exact project or when the UI workspace uniquely binds the project root.  
Match the native Codex `cwd` or single Antigravity `workspace_uri` against the exact project root; if native binding is ambiguous, require an explicit `"Project root: <absolute path>"` in the user's message.  
Example of an unambiguous prompt: `"Continue preparing the proposal. Project root: `<absolute path>`"`.  
Do not ask the user to re-run `/upwork-init`.  
Take the exact root/URL from the current chat history; never pick the most recently modified or neighboring project by guesswork.  
Read the overview, topical modules, and saved results in the agent KB, then run `status <project>` and `resume <project> --reason <reason>`.  
When switching platforms, run `configure <project>`, then `configure <project> --check`, and idempotent `register <project>` for both platforms.  
A prior Antigravity confirmation does not substitute for Codex registration or vice versa; never copy or recreate the working directory.  
Verify the active profile and folder branch before completing `identity_init`; this does not require re-running `init` or re-collecting sources.  
Check completed stages, file hashes, and actual worker states; the mere existence of an old file does not prove analysis completion.  
Reuse the saved snapshot, evidence, and worker reports; do not repeat a successful unchanged capture.  
If the interruption occurred during workspace creation itself, finish the missing step from the exact saved snapshot without regenerating manual or enriched documents.  
Preserve and explicitly diagnose any corrupted or partial file; if no valid snapshot exists, perform a new capture without overwriting prior files.  
Exact request adoption and continuation commands are detailed in [workflow.md](references/workflow.md).  

## Post-Analysis: Proposal Work

A completed initial analysis serves as the input to subsequent work; completing `finalize` does not mean a proposal is ready.  
When the user instructs you to draft or edit a proposal, execute that specific semi-manual task using the shared KB, exact journal, `ꘖ/data/continuation.md`, and actual `result/**` files.  
Read the requested `draft.md` and any existing `final.md` as distinct versions; never pick a draft by modification timestamp or from a neighboring project.  
Before the first edit to `draft.md` in a turn, save its exact bytes via `snapshot_draft.py` per FILE-2.  
Record completed work, the active working file, open questions, and the next step in `continuation.md`; keep facts and primary grounds in the topical KB modules and evidence store.  
Proposal workflows do not add synthetic automated stages: do not invent stage statuses or re-run `inspect`/`init` merely because the user switched UI platforms.  
Write standalone articles via [df-article](../df-article/SKILL.md), proposals via [df-proposal](../df-proposal/SKILL.md), and letters via the [shared procedure](../../references/client-text/workflow.md) with `kind=letter` (PUB-1).  
Once initial analysis is finalized, record a proposal-only request via `scripts/record_step.py` (or `answer-prepare`) per FILE-3 without re-opening initial analysis stages.  
Submitting a proposal to the client requires a separate explicit instruction.  

## Research and KB

Follow [workflow.md](references/workflow.md) for the question registry, saved observations, stages, and reviews when executing those operations.  
For new analyses and deep-dives, read the [evidence and experiment contract](references/evidence-contract.md): typed F/H/M claims, provenance, methods, observation scope, and deterministic calculations.  
New `save-analysis`/`render-analysis` runs and turn completion enforce the current contract version; legacy formats remain readable for diagnostics without automatic promotion to `verified` or history rewriting.  
Before collecting data, map material claims to questions, alternatives, conditions, appropriate methods, and testable outcomes; record actual results or a specific gap for every requirement.  
Never design a test merely to confirm a pre-existing belief: state the measured indicator and a counterexample where the target claim is false yet the test passes; a proxy indicator supports only a qualified conclusion.  
HTTP collection is suitable for raw server markup; interactive behavior requires an executed browser scenario, geo-dependent behavior requires verified connection conditions, and hidden admin settings require their primary source.  
When auditing a website, never infer page content, "demo clutter", or missing schema from `sitemap.xml` URL paths alone: collect a representative sample of every template (home, catalog/listing, product/work item, blog post, contact page; for Squarespace also `?format=json-pretty` when needed) and inspect `site_summary`/`sitemap_issues`/`tracking_summary`.  
Do not run an exhaustive country/browser matrix for every job post: scope experiments to the material claims and boundaries of the instruction.  
Evaluate two independent Red Flags first: `RF-CLIENT-INTERMEDIARY` (the client is acting as an intermediary for an end client) and `RF-WEBSITE-UNIDENTIFIED` (the target website cannot be identified from available data).  
Being an agency does not by itself prove intermediation on the current job: weigh internal agency projects, client wording, work history, and alternatives; frame unproven intermediation as a DOC-2 hypothesis.  
The second flag applies to tasks targeting a specific website or checkout flow; a URL not yet provided prior to research, downtime of an already known domain, or a greenfield/non-website task does not trigger it.  
Check the job post, saved history/attachments, and targeted search per EXEC-1; if the website remains unidentified, state the search scope, limitations, and what must be requested from the client.  
Never substitute the website of an agency, platform vendor, past/unrelated client, or unverified candidate for the target website.  
As soon as a Red Flag is substantiated, report it in the current update and write the managed block at the end of the root `.md` inside the level-1 `# Red Flags` section without waiting for later stages to finish.  
At the very beginning of the final report/response (immediately after the title, if any), before client identification, technical details, completed actions, or recommendations, place a prominent `Red Flags` heading and a separate bold bullet for each active flag with its brief basis, status, and link; when `red_flags` is empty (`[]`), omit the `Red Flags` heading and block from both the response and the root `.md`.  
When both flags are active, add the bold warning: `"Both Red Flags simultaneously: high likelihood of declining the project"`, noting explicitly if intermediation is hypothetical.  
This block informs the user's decision; it is not an automatic project cancellation or permission to abort the requested analysis unilaterally.  
In `Analysis.json`, populate `red_flags` explicitly (using an empty list `[]` only after evaluating both risks); follow the [Red Flags contract](references/workflow.md#red-flags) for statuses and `identity` claim links.  
`render-analysis` duplicates the block at the end of the root `.md`: first the level-1 heading `# Red Flags`, then the opening marker, content, and closing marker inside that section; if adding the block manually early on, use the exact same markers and keep it synchronized with current evidence.  
Update both placements whenever new data arrives; remove a cleared flag from active warnings while preserving the historical basis in the KB.  
Before starting an investigation, define the question, its impact on conclusions, and the completion criterion.  
Assign a single owner per question; justify any repeat independent extraction by pointing to a specific disputed claim.  
Extract additional fields or quotes from the already saved capture; changed conditions or freshness checks require a new observation with `refresh_reason`.  
Deterministic checks are run by tools; reserve A.F for extraction or evaluation tasks that require model judgment.  
Do not guess missing file paths or probe infrastructure without a specific diagnostic question.  
After three empty searches on the same question, record the gap or justify a method change; hitting the limit does not confirm a hypothesis.  

Execute all five stages: client/website identification, client concerns, misconceptions, causes in the client's system, and solution methods.  
Maintain F/H/M claims, stable IDs, concrete arguments for/against, score bases, and links; never invent causes, misconceptions, or counterevidence.  
Record new verified findings and corrections in the agent KB immediately, checking dependent claims and topical modules for consistency.  
Structure and examples are in [README-agent-tools.md](../../scripts/README-agent-tools.md) and [analysis.example.json](references/analysis.example.json).  
Write the candidate in `ꘖ/data` and publish via `save-analysis` with the expected SHA-256 of the current JSON; `render-analysis` then updates Markdown while preserving history and manual edits.  
Run formal validations via `validate-analysis ... --format json --evidence` and `check-project <project>`; passing them does not prove substantive truth.  
For documentation links, provide a verified `#anchor` or a recorded `anchor_exception` (section title, quote, and observation) per LINK-2.  

## Audit and Completion

In a justified routine case, the primary A.A performs the substantive check and KB consistency audit, recording `self_review` explicitly without calling it an independent audit.  
Delegate independent evaluation of disputed conclusions to A.A via the active platform's native UI subagent tool.  
For significant or disputed conclusions and architectural changes, use two independent A.A auditors per REVIEW-3.  
Prepare an immutable KB review package and pass it along with primary sources to the reviewer; never pass another auditor's conclusions or a one-sided JSON verdict template in the prompt—the auditor runs `review-input <project> --package <path> --platform <platform>` to obtain the neutral `report_contract` listing all valid outcomes.  
Before preparing the package, write the exact response candidate and map its material claims; the package binds them to the current requests, KB digests, and primary evidence, and every standalone number in `essence` and `response_excerpt` must be backed by primary quotes or verified calculations.  
Justify the risk category under REVIEW-3: new material causal, architectural, or pricing conclusions (including a five-stage analysis introducing new `causes`/`misconceptions`/`methods`) require `significant` and cannot be downgraded to `routine` by omitting stages from the claim map; a `routine` restatement requires proven unchanged grounds.  
An independent auditor operates strictly read-only inside the current project root: it does not invoke write tools, does not generate reports via external scripts, and does not read neighboring `daily` projects.  
Preserve the original JSON verdict from the auditor's final native message separately from parent dispositions of findings; `needs_changes` persists and blocks completion.  
Save the report and native launch/completion proof; fix each finding or reject it with documented primary evidence.  
After modifying any affected conclusion, update dependent KB modules and obtain a new review clearance for the revised version; never claim an older audit cleared a modified response.  

Before responding, verify task completeness, KB consistency, sources, links, and remaining unknowns.  
Omit internal procedural sections about artifact generation (`finalize`, `Context.md`, internal folder paths) from the final response; comply with DOC-4 (one sentence per line with `  \n`) and synchronize the established client name in `KB/Project.md`.  
Validate authored Markdown/text files with `validate_links.py --readable <files>`; use human-readable `<...>` paths and never alter exact source captures or journals.  
When Red Flags are present, verify their prominent placement at the very top of the final response and at the end of the root `.md` inside the level-1 section; mentioning them only inside KB modules is insufficient.  
Save the exact requests and complete final response; when multiple requests share a single response, link them explicitly via `record-answer` / `answer-prepare`.  
Publish the exact verified response bytes; adding new claims after review requires clearance of the new version, including when continuing a previously finalized project.  
After recording the journal and passing all checks, build the external `Context.md` export without summarizing or truncating sources.  
`stage ... finalize` requires a current A.A substantive review (plus independent reviews when required), a consistent KB, a complete journal, an empty `ꘖ/data/scratch` directory, and no one-off scripts in the project; it certifies file and response readiness rather than confirmed UI message delivery.  
Delete only your own temporary scratch files after verifying permanent copies (`--consume-input`); preserve snapshots, material screenshots, and primary evidence.  
