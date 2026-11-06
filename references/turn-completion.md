# Completing Any Turn

This contract applies to the primary conversation and ordinary analytical responses, including `.agents` investigations; an article/proposal format or the five-stage analysis workflow is not a prerequisite for journaling.  
An explicit current user instruction takes priority under SCOPE-1; child A.A/A.F subagents do not maintain the user journal.  
Edits to client documents retain their own checks for scope, baseline, evidence, and reviews.  

## Turn Begin

After determining the exact root of the primary conversation, run:  

```text
python <agents>/scripts/harness.py turn-begin <root> --platform codex
python <agents>/scripts/harness.py turn-begin <root> --conversation <native-uuid> --platform antigravity
```

Codex obtains the UUID from `CODEX_THREAD_ID` and the profile from `CODEX_HOME` or an explicit `--codex-profile`; a neighboring profile or chat is never selected automatically.  
Antigravity requires the valid UUID of the current conversation.  
The tool verifies native request ownership for the root and the `primary`/`child` role; an ordinary agent project does not require a synthetic job post or client article.  
`ꘖ/data/turns` records the root, native turn, exact requests, applicable FILE-3/EXEC-5/DOC-2 rules, their sources, and mandatory stages.  
In the first phase of a turn, run `policy-instructions` (in Codex), `turn-begin`, and batched reading of rules without output truncation; launch any `git` commands only after receiving the first-phase output and strictly with `--no-optional-locks` (or via `git-read`).  
The `--journal <directory>` option records a journal explicitly chosen by the user; without it, a new turn uses `ꙮ/1 - Analysis` (or `ꙮ` when configured at the root) and an existing turn retains its prior binding.  
The journal of an already started turn cannot be silently redirected; the verifier preserves its binding and also checks linked documents against the project root.  
This record is evidence of applicability and configuration, not proof that the model read or understood the rules.  
`instruction_snapshot` records the list and SHA256 digests of shared rules, the adapter, `runtime.json`, local registration, and its path sources; for Codex it also records discovered `AGENTS.md`/`AGENTS.override.md` candidates along the configured root and in the active profile.  
This is an inventory of available sources rather than proof of trigger selection or actual context injection: `selection_verified` and `delivery_to_model_verified` remain `false`.  
Errors resolving local registrations are saved in `errors`; appending a snapshot to prior state is marked `existing-state-upgrade`, and post-delivery recovery is marked `recovery`.  
Execution is foreground-only: `turn-begin` reconciles earlier completed turns of the current conversation synchronously, and `answer-prepare` records the current exact response before returning.  
Neither command registers or starts a background process, including calls using the legacy `watch` parameter; `--no-watch` remains a compatibility option.  
No persistent verifier, detached worker, polling loop, or timer runs between working calls, whether applications are open or closed.  
Prepared response bytes are saved before publication; native delivery can only be confirmed during a later foreground call after the completion event exists.  
When the user explicitly opts out of journaling, first run `journal-unwatch <root> --conversation <native-uuid> --platform <platform>`, then honor the opt-out and do not call `answer-prepare` for that response.  
The command removes only the legacy binding and waits for any in-progress explicit foreground verification pass to finish; previously saved history remains intact.  

## Answer Preparation

```text
python <agents>/scripts/harness.py answer-prepare <root> --response-file <root>/ꘖ/data/scratch/answer.md --consume-input --platform codex
python <agents>/scripts/harness.py answer-prepare <root> --response-file <root>/ꘖ/data/scratch/answer.md --consume-input --conversation <native-uuid> --platform antigravity
```

**Mandatory UTF-8 encoding rule in Windows PowerShell:**  
1. In Windows PowerShell 5.1, piping text (`@' ... '@ | python ...` or `"..." | python ... --response-file -`) defaults to the single-byte `[Console]::OutputEncoding` (OEM/ASCII), irreversibly replacing Cyrillic and the characters `ꘖ` (`\ua616`) / `ꙮ` (`\ua66e`) with question marks `?` (`0x3F`).  
2. Therefore, before calling `answer-prepare` (as well as `record-answer`, `prepare-review`, `record-review`, and `save-analysis`), **always write the response text in UTF-8 without BOM to `<root>/ꘖ/data/scratch/answer.md`** using the native file tool (`write_file` in Antigravity or `[System.IO.File]::WriteAllText($path, $text, [System.Text.UTF8Encoding]::new($false))` in PowerShell) and pass the path via `--response-file "<root>/ꘖ/data/scratch/answer.md" --consume-input`.  
3. If you run a `python -` one-liner via a pipe `|` in PowerShell, always prefix the command with `[Console]::InputEncoding = [Console]::OutputEncoding = $OutputEncoding = [System.Text.UTF8Encoding]::new($false);`, and use the Unicode escapes `\ua616` and `\ua66e` for paths containing `ꘖ` and `ꙮ` inside Python code.  

The operation re-verifies the active native turn, records the exact requests and response through the existing `record_answer` mechanism, validates the read-back bytes (rejecting corrupted OEM/ASCII output where words were replaced by `???`), and returns `response_file`, SHA256, pair numbers, and `ready: true`.  
New answer admission runs the current linked-document and source freshness gates, including semantic approval when required for the linked operation, before recording a proof bound to the exact journal, native turn, request identities, and response bytes.  
The immutable proof retains the selected document revision, source checks, evidence, and approvals used at admission; unrelated registry entries do not become historical dependencies.  
Its scope reflects the checks required for that operation; semantic publication clearance remains a separate requirement for publication workflows.  
It also checks public tool calls of the active turn for compliance with `EXEC-5` (no read-only Git invocations without `--no-optional-locks`), saving the result in `exec5_check`.  
If an earlier step in the active turn triggered an `exec5_check` or `http_fetch_check` violation, run `python <agents>/scripts/harness.py recover-turn-violation <root> --conversation <native-uuid> --reason "<explanation>"` to record a retrospective violation receipt in `ꘖ/data/turns/<turn_key>-violation-recovery.json` (preserving the violation list with `recovered_via_receipt: true`) before calling `answer-prepare`, rather than writing directly to `ꙮ/**/req|res/*.md`.  
Additionally, `answer-prepare` performs five protective turn and source checks:  
1. `http_fetch_check` (`KB-3` / `EXEC-1`): rejects ad-hoc external network requests in the shell (`urllib.request`, `requests`, `Invoke-WebRequest`, `curl`) executed outside `collect` / `collect-http` / `collect-browser`.  
2. `compaction_check` (`COMPACT-1` / `KB-3`): if context compaction (`CHECKPOINT` / `context_compacted`) occurred in the active turn after tool calls, requires restoring pre-compaction results via `harness.py recover-checkpoint <root> --conversation <native-uuid>` or reading `transcript_full.jsonl` after the `CHECKPOINT` step, and blocks citing any primary source file (`source.md`, `res/<N>.md`, `ꘖ/KB/Evidence/**`) that was read only before `CHECKPOINT` and evicted without a post-checkpoint re-read.  
3. `delegation_check` (`REVIEW-1` / `KB-3` / `REVIEW-4`): in Upwork projects (`ꘖ/project.json`), rejects executing more than 40 tool steps in the primary agent without delegating to subagents (`A.F`/`A.A`) or writing intermediate findings to `ꘖ/KB` (when inspecting file tools, only the target path `Path` / `TargetFile` is checked, not `Content`), and rejects `A.A` audit subagents that read only a truncated or non-contiguous partial slice of a candidate response (`aa_partial_read_violations`).  
4. `code_lifecycle_check` (`EXEC-5`): for any issue-tracked `code` repository modified during the active turn (whether inside or outside `<root>`, including nested subagents), requires zero uncommitted changes, a GitHub Issue URL reference in every modified code file, a commit in `HEAD` referencing that exact Issue URL (with the commit message containing only the Issue URL), `HEAD` pushed to upstream `@{u}`, and the GitHub Issue closed (`state == 'closed'`); for analysis-only turns that diagnose repository defects and remediation methods in an issue-tracked `code` workspace without modifying code, requires filing verified open GitHub Issues via `df_github_issue.py` with saved read-back Evidence JSON and local source grounding.  
5. `source_kb_check` (`LINK-1` / `LINK-5` / `VERIFY-1` / `KB-1` / `KB-3`): verifies link readability (`readable_link_issues`, permitting unencoded local `file:///C:/...` links in chat responses), provenance tiers (`Tier 0`/`Tier 1`/`Tier 2`, rejecting `Tier 2` rule/draft/`res/*.md` files as sole evidence for factual or numeric claims and auto-binding sibling `source.md` whenever `analysis.md` is linked), structured fact-tuple consistency against `ꘖ/data/facts.json` (`vcpu=null`, `mem_total`, `swap_total`, normalized `load average`), deterministic AST inline arithmetic (`A - B = C`, `A / B = C`), presence of all external `http(s)://` links from the response in `ꘖ/KB` modules or `Analysis.json` (in projects with `ꘖ/project.json`), presence of valid primary observations in `ꘖ/KB/Evidence` across all projects for every external link (rejecting anti-bot/JS challenge shells with `browser_check_required: true` and empty `word_count: 0` HTML captures), verification of `#fragment` anchors against extracted `anchors`, verification of attributed verbatim quotes (`«...»` / `Оригинал:`) against the saved observation text, and agreement between a descriptive link label (`[Title](url)`) and the actual `<title>` / `<h1>` / JSON topic title in the saved observation.  
<!-- https://github.com/dmitry-ai/harness/issues/47 -->
<!-- https://github.com/dmitry-ai/harness/issues/48 -->

In tracked projects with `ꘖ/data/workflow.json` and `ꘖ/project.json`, while the `finalize` stage of initial analysis is incomplete (or when a subsequent analytical response contains causal hypotheses or methods `H-N` / `M-N` without a delegated subagent audit in the current turn), requests must be adopted via `adopt-requests` and approved via `authorize` (filtered to the current conversation without blocking on historical conversations); once `finalize` is complete, client text edits (`/df-article`, `/df-proposal`) and ordinary follow-up turns are recorded in the journal via `_record` and checked against `source_kb_check` and `gate_requests` without binding to the initial analysis cards in `Analysis.json`.  
Verification includes a full request snapshot after `turn-begin`, after lock acquisition, and after writing the journal.  
If a new request or turn change is detected after writing, history is preserved, the state receives `preparation_unverified` and a negative `readiness_check`, and readiness is withheld.  
This check does not create an atomic transaction with platform delivery: a message arriving after the last check still requires handling by the primary agent.  
Linked client documents pass through `gate_requests`; requests of a tracked initial analysis retain the substantive `authorize` gate.  
Publish the exact contents of `response_file` without modification.  
Retrying with the exact same bytes is idempotent; a different version of an already recorded response or a new uncovered request never overwrites prior history.  
`delivery_verified: false` indicates preparation rather than observed delivery.  
A narrow check rejects justifying equal probabilities solely from absence of data; verbatim quotes, code blocks, and explicit negations of that fallacy are preserved.  
This check does not identify hidden causes, does not forbid justified equal priors, and does not replace substantive review.  

## Native Verification

```text
python <agents>/scripts/harness.py journal-sync <root> --conversation <native-uuid> --platform codex
python <agents>/scripts/harness.py journal-watch --action status
python <agents>/scripts/harness.py journal-watch --action once
python <agents>/scripts/harness.py journal-watch --action once --dry-run
python <agents>/scripts/harness.py journal-watch --action stop
```

The foreground reconciler reads the explicitly selected conversation, its exact user requests, and completed final messages; private reasoning traces are never exported.  
The next `turn-begin` performs this check for earlier completed turns in the current conversation; `journal-sync` requests it explicitly without starting any later work.  
`journal-watch --action once` is a bounded compatibility command for explicitly auditing saved legacy bindings; it does not schedule another pass.  
`journal-watch --action start` and `--action run` reject persistent execution, `status` is read-only, and `stop` can cooperatively retire a verifier from an older installation.  
Codex requires a native turn-completion event and a final assistant message matching that completion event.  
Antigravity verifies a completed step; for the active tail, it additionally requires native idle state, `not_fully_idle: 0`, absence of killed status, and consistent indices for the last user request and planner step.  
Incomplete entries, explicitly aborted Codex turns, a killed Antigravity tail, unrelated projects, child subagents, and truncated JSONL lines never count as successful delivery.  
When the prepared and delivered bytes match, the state transitions to `delivered` with `delivery.verified: true`.  
If preparation was skipped, the actual exchange is recorded with `recovered_after_delivery: true`; this is post-hoc recovery rather than compliance with FILE-3 before publication.  
If the exact request group already existed without the new contract state, reconciliation records `completion_provenance: existing_journal`, avoids creating a duplicate, and does not retroactively mark it as pre-delivery verified.  
Historical responses are preserved verbatim even if they contain errors; recording them does not constitute substantive approval.  
Altered bytes are recorded as a conflict alongside the separate native text; existing journal pairs are never overwritten.  
An explicit reconciliation checks current journal integrity even when the native source is unchanged; repeated checks preserve unchanged receipt bytes, timestamps, and file modification times.  
For an already recorded answer, reconciliation verifies its original admission proof and historical integrity rather than re-running publication-time freshness or requesting new semantic approval.  
Elapsed time and a later legitimate applied revision do not invalidate the earlier admission; altered or missing journal, proof, evidence, or required document history remain integrity conflicts.  
Applied successors bind the preceding registered version; historical verification follows this receipt chain to the admitted version so replaying an older valid receipt is not accepted as a later revision.  
Explicit baseline reconciliation retains its acknowledged bytes and predecessor link, preserving earlier history while the changed baseline awaits any required new publication approval.  
Legacy records without a proof report an explicit proof gap and are never silently promoted to current approval; a previously failed admission cannot become approved through recovery.  
When a completion state exists, deleting a recorded pair or its receipt is flagged as a conflict without silent restoration or history duplication.  
When an unrecorded native turn matches an existing unclaimed pair in `req/<N>.md` and `res/<N>.md` (after normalizing `CRLF`/`LF`, trailing newlines, and local `file:///` prefixes), `_record` adopts that pair into `answer-groups/native-<turn_key>.json` with `completion_provenance: existing_journal` instead of allocating a duplicate `max + 1` pair; if the matching on-disk pair is claimed by another `answer-groups` receipt whose recorded hashes disagree with the overwritten disk bytes, `_record` raises a conflict and preserves the evidence.  
A syntactically or structurally corrupted binding is preserved with an error and does not halt verification of other conversations; a transient read error is retried on the next pass rather than cached as success.  
Failure of a prior gate on a linked client document is likewise preserved as a conflict with the native text rather than bypassed for recovery.  
A stable native ID and request check prevent duplicates; identical wording in different turns is not treated as the same request.  

## Limits and Verification

The shared source remains `AI/harness/code`; legacy audit bindings and retirement metadata remain in `AI/harness/_/ꘖ/data/journal-watch`, and native databases are never modified.  
Foreground reconciliation does not close windows, restart Codex or Antigravity, or terminate third-party processes; legacy `stop` targets only the old verifier's own token.  
The contract does not intercept platform message submission: an agent can still bypass preparation by emitting a direct final reply, after which the next foreground reconciliation detects the violation and recovers the journal entry.  
If no later working call occurs, native delivery remains unverified; there is no autonomous post-delivery repair or promise of immediate background recovery.  
Criteria: routine analysis and articles use the same FILE-3 contract; an incomplete reply is not imported; a skipped preparation is recovered; retries do not duplicate pairs; a foreign root/profile/child is rejected; a conflict preserves the original bytes.  
<!-- https://github.com/dmitry-ai/harness/issues/41 -->
<!-- https://github.com/dmitry-ai/harness/issues/48 -->
