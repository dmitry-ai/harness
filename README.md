# Upwork Automation

A new analysis in Antigravity 2.0 UI and Codex starts with the `/upwork-init <URL>` command; Codex also accepts `$upwork-init <URL>`.  
After a quota limit, power outage, or Windows freeze, the user writes `"Continue analysis…"` in the same chat; the agent verifies saved results and resumes the existing project.  
The same directory can be continued in a new chat of the other system, up to semi-manual proposal preparation under a specific user instruction.  

This directory is the shared single source: Python core, rules, skills, and worker responsibility definitions.  
Adapters in `platforms/` and `scripts/agent_tools/platforms/` contain environment differences: registration, exact messages, and review provenance.  
Antigravity connects all eleven `always_on` rules via `.agents/{rules,skills,agents}.json`.  
Access to authenticated portals is governed by [EXEC-3/EXEC-6](rules/08-execution-and-tools.md#exec-6) and the [shared procedure](skills/upwork-init/references/authenticated-access.md).  
The agent opens required pages itself in the verified profile and uses its authentication in a targeted manner, including required tokens, without exporting secrets into responses or journals.  
Codex receives a short loader through the root `AGENTS.md`; the same text is preserved in `developer_instructions` of `.codex/config.toml` for compatibility.  
The skill is discovered from `.agents/skills/upwork-init/SKILL.md`, and roles from `.codex/agents/*.toml`.  
The loader requires reading the canonical rules and adapter; their full texts are not copied across projects.  
Root `CODEX.md` files are no longer created.  
`python scripts/upwork_project.py build-native` updates these projections; `build-native --check` detects drift.  
Manual edits to managed documents are preserved with diagnostics.  
For any primary turn, including routine `.agents` analysis, [turn completion](references/turn-completion.md#turn-begin) applies: `turn-begin`, then `answer-prepare` before publication, and independent native verification after delivery.  
This contract is independent of the client text format; a prepared record and verified delivery have distinct states.  
Environments, paths, default models, and selection policy reside solely in [runtime.json](runtime.json); this tool does not launch LLMs.  
Symlinks and copying of shared modules into new projects are not used.  
The project-level `.agents` contains Antigravity bindings and local rule sources; the workspace loader reads them from the current project.  
`configure` preserves parent instruction inheritance and user TOML settings; empty legacy service configs are removed.  
An old `CODEX.md` is removed only when it matches the ownership receipt; a manual file is preserved with a conflict.  
`configure --check` verifies bindings for both environments and the currency of the project projection.  
A same-named skill is not duplicated across subprojects: Codex discovers the root `.agents/skills` up the repository chain.  

Internal agents work with their own current, consistent `ꘖ/KB`, primary evidence, and `ꘖ/data` state.  
Manual `KB/Project.md` is created once and initially ported in full into the agent KB.  
`ꙮ/0/Context.md` is a complete external export of documents and the exact journal, primarily for manual submission to Gemini DeepThink via gemini.google.com.  

Invocations of A.A/A.F remain visible in the UI.  
Antigravity uses `self`/`af-worker` with their respective parameters.  
In Codex, the parent selects the model and effort of each worker based on context and available options; the fallback is inheriting the current session.  
Role TOML files do not lock a model on top of the parent's choice.  
The primary chat model is selected in the application UI.  
The A.A role does not switch the model by itself; runtime stores selection rules for child workers and the explicitly configured Antigravity A.F preset.  
Codex registers projects through the existing Shared-Projects helper: a shared catalog and branch `Upwork / Proposals / YYYY / MM / DD`, with separate native profile IDs.  
Pending native confirmation is reflected as `complete: false`; it must not be reported as a completed registration.  
Repeated `register` is idempotent.  
Standard `init`/`register` request both systems according to `registration.targets`; `complete` refers to the executing environment, while `all_registered` refers to both.  
Intents, attempts, errors, and last successful IDs are saved in `ꘖ/data/registrations.json`; secondary unavailability does not block work in the active system.  
The title and date come from the existing project; a manual mismatched name is preserved and diagnosed without silent renaming.  
Python performs mechanical checks; A.A evaluates substantive conclusions and consistency.  
New publications use analysis contract v3: primary grounds, claim type/status, observation scope, and dependency versions; legacy files remain readable without automatic promotion to `verified`.  
Sufficiency verification compares the target claim against the actually tested statement and a counterexample: a positive proxy indicator is not full confirmation.  
An experiment stores the plan, raw artifacts, and interpretation separately; review v2 binds the authored verdict to exact requests, the response, and KB/Evidence.  
Exact model/effort versions require actual metadata; Codex verifies the child `turn_context` against the parent's native call, while Antigravity reads available generation/executor metadata.  
The unknown remains unknown.  

[Procedure](skills/upwork-init/SKILL.md) · [Evidence Contract](skills/upwork-init/references/evidence-contract.md) · [Continuation and Research Protocol](skills/upwork-init/references/workflow.md) · [Tools and Schema](scripts/README-agent-tools.md) · [Client Text](skills/df-article/SKILL.md).  

Articles are written via [df-article](skills/df-article/SKILL.md), and Upwork proposals via the separate [df-proposal](skills/df-proposal/SKILL.md).  
The [shared procedure](references/client-text/workflow.md) binds edit boundaries, evidence, the paragraph map, independent review, version verification on write, and the exact journal; letters use it with `kind=letter`.  
Formatting engines differ, while the shared core and lexicon are unified.  
[Commands and schemas](references/client-text/operations.md) are available through `df_text.py`, `df_article.py`, and `df_proposal.py`.  

After initial analysis, `status` continues to describe its stages while listing actual proposal files separately.  
Semi-manual work uses the KB, exact journal, existing `result/draft/final`, and the current step in `ꘖ/data/continuation.md`; the original draft is protected by a FILE-2 snapshot.  
No new automatic proposal workflow stages are added; transferring files between systems does not require migrating UI history or running `init` again.  
