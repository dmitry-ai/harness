---
trigger: always_on
description: "Deterministic operations, browser, tests, and turn completion"
---
# Execution
## EXEC-1
Perform any repeatable operation with an existing tool or a single parameterized script.  
Do not write a one-off script for each special case or hardcode the expected answer into evidence.  
Internal tools are documented in `scripts/README-agent-tools.md`; rule files do not execute scripts themselves.  
Save an HTTP response and its observation conditions once; run subsequent extractions against the saved capture.  
Use `harness.py collect-http` or `collect-browser` for a single observation and `collect` for batch collection (`upwork_project.py` remains a compatibility alias), with automatic CDP browser fallback (`--browser auto` on `cdp_port: 9222`) when HTTP returns an anti-bot challenge or empty JS shell; direct network requests (`urllib`/`requests`/`Invoke-WebRequest`/`curl`) in the shell that bypass the evidence store and substituting `search_web` snippets for primary page observations are blocked.  
Changed conditions, required refreshes, and longitudinal measurements are separate observations with an explicit reason.  
After three fruitless searches on the same question, return the specific gap or justify a method change; hitting the search limit does not confirm a hypothesis.  
## EXEC-2
In any GitHub-backed repository, satisfy the mandatory pre-TDD `Issue-First` contract (`EXEC-5`) before writing any test or production code.  
Strict Test-Driven Development (TDD) is mandatory for all software code in every language and repository: agents are strictly prohibited from creating or editing any production code before writing a behavioral test for it and observing that test fail (`Red`).  
Only after observing a genuine test-runner failure (`Red`) may an agent implement or modify production code (`Green`), and writing production code first and fitting tests to it afterward is strictly prohibited (`PreToolUse`, Git `pre-commit`, `answer-check`, `answer-prepare`, and `Stop` enforce this contract).  
Every test must verify observable runtime behavior rather than reading or matching production source-code text (`read_text`, `open`, `inspect.getsource`, `readFileSync`, `File.ReadAllText`, `file_get_contents`, `Get-Content`), and assertionless test stubs are prohibited.  
Existing tests and assertions operate as a one-way Test Ratchet: deleting, skipping, or weakening existing test files, test definitions, or assertions (and weakening assertions in newly created test files after production code has been modified in the same cycle) is prohibited unless an audited `RATCHET-OK` approval (`>= 30` characters citing the requirement or user decision, never a test-fitting excuse) is recorded via `harness.py ratchet-ok` or inside the linked GitHub issue body.  
Before completing a turn or closing a code task, run the full test suite (not a single-file subset when the repository has multiple test files) after the final edit and verify all tests pass (`Green`); inspect active-turn compliance via `harness.py tdd-check`.  
During intermediate Red/Green iterations in multi-step tasks, target only the changing case with a narrow filter (`python -m pytest <file> -k <test_name> -x`, where a `-k` typo fails immediately with exit code `5` rather than `unittest`'s silent `Ran 0 tests` / `OK`) instead of re-running unrelated slow test files, and execute the full parallel test suite (`python -m pytest <tests> -n auto --dist worksteal -x` or `harness.py run-tests`) once after the final edit.  
Run test commands with fail-fast enabled by default (`harness.py run-tests` for parallel Python `unittest` suites, `-f` for `unittest`, `-x` for `pytest`, `--bail` for JS runners, `-failfast` for `go test`, `--stop-on-failure` for `phpunit`) and a synchronous startup window (`WaitMsBeforeAsync: 10000`, enforced via `EXEC-2-TEST-FAILFAST-GATE` in `PreToolUse`).  
A test must verify material behavior and reproduce the defect; distinguish mocks, integration tests, and live execution.  
Before closing any `/upwork-init` incident parent issue or claiming a complete fix, execute `harness.py shadow-replay` on an isolated workspace-local copy of the failed project (strictly inside `ꘖ/data/scratch/shadow-replay/` per [FILE-6](01-file-boundaries.md#file-6), never outside the workspace) across all remaining downstream CLI and hook stages (`PreInvocation`, `turn-begin`, review authorization, `answer-check`, `answer-prepare`, `stage finalize`, and `Stop Gate`), confirm automatic cleanup of the shadow copy, and report explicitly which stages were verified (`stages_verified`) versus not executed (`stages_not_run`, such as live LLM generation).  
For code managing persistent connections, daemons, or child-process lifecycles, verify handle release and clean exit on a real process rather than mocks alone.  
Verify your own changes and the requested environments; a third-party defect does not authorize modifying unrelated files, weakening a check, or substituting a source.  
## EXEC-3
Determine the browser profile and account from the instruction and environment settings, then verify them; when ambiguous, do not pick an arbitrary profile or CDP target.  
Treat a user tab as read-only: no navigation, reload, focus stealing, or closing.  
If the required page is not open, open your own tab or window in the verified profile; do not require the user to pre-open every page.  
Keep agent-opened tabs/windows in a separate tool session while preserving the required authenticated profile; use a clean profile only for an explicitly isolated scenario, never as a substitute for an available user session.  
Take window coordinates and monitor selection from environment settings, not from universal rules.  
Do not terminate the shared browser or delete its lock files.  
## EXEC-4
Harness execution follows the foreground-only lifecycle in [FILE-3](01-file-boundaries.md#file-3); all entry points must return without leaving autonomous Harness work running.  
In asynchronous workflows, distinguish submission, acceptance, execution, and result retrieval; track response IDs and timeouts.  
Before retrying, check whether the first request was accepted; do not promise background continuation without a working mechanism.  
Bound test runs, browser fixtures, and child commands with in-process timeouts (such as `harness.py run-tests --module-timeout` or `--test-force-exit` and `--test-timeout` for `node --test`), and inspect or terminate stalled tasks via `manage_task` rather than waiting indefinitely.  
Do not attach one-shot `schedule` timers (`DurationSeconds`) to background `run_command` tasks or active `invoke_subagent` workers: both deliver their own reactive completion notifications, and redundant timers over active `run_command` or `invoke_subagent` work are blocked by `EXEC-4-SCHEDULE-GATE` in `PreToolUse`.  
When landing concurrent repository changes onto `main`, serialize only the final landing step through `harness.py land-acquire <repo> --wait --timeout <S>` (with `land-release` on exit) so agents proceed strictly in FIFO order with reactive wakeups; for logically related parallel work launched together, prefer coordinating under `swarm` or `invoke_subagent` with `workspace: "share"`.  
Never delegate waiting for a parallel agent's transient repository or journal lock to the user before exhausting deterministic foreground reactive waiting (`harness.py wait-repo <repo> [--clean | --lease-free] --timeout <S>`, `harness.py land-acquire --wait`, or `harness.py answer-prepare --wait-timeout <S>`) and verifying whether the lock holder PID is still alive.  
## EXEC-5
Before any Git operation, verify the repository root, branch, and remote; commit only an explicit file list in the established order, without unrelated changes or Git hooks.  
For concurrent tasks on the same repository (and unconditionally for all agent edits in the self-hosted Harness repository), isolate development and `Red`-TDD in a linked worktree (`harness.py worktree-begin <repo> --task <id>`), land via `harness.py worktree-land <wt>` (single rebase + single parallel full suite + `--ff-only`), and execute host-global mutations (`harness.py build-native`, `harness.py install-global`) strictly on `main` during landing rather than inside parallel worktrees; `EXEC-5-WORKTREE-GATE` (`PreToolUse`) blocks direct `write_file`/`edit_file` in live Harness `main` unconditionally and in other Git repository `main` checkouts whenever `>= 2` concurrent open turns are active in `ꘖ/data/turns/`.  
Run read-only Git checks with `--no-optional-locks` so the index is not updated as a side effect (preferably via `harness.py git-read` or with `GIT_OPTIONAL_LOCKS=0`; do not combine `git` calls with initial rule reading before `turn-begin` completes).  
Create, edit, comment on, close, and fetch GitHub issues per the [df-github-issue](../skills/df-github-issue/SKILL.md) skill via `df_github_issue.py` using a UTF-8 file without BOM (`--body-file`) and mandatory read-back verification; never pass Markdown bodies via `--body`/`--comment` on the command line or through a PowerShell pipeline without UTF-8.  
`df_github_issue.py create` automatically prepends a tab-indented JSON metadata header (`Time`, `Issue`, `Project`, `Journal`, `Agent`, `Trace`) to new GitHub issues before read-back verification unless `--no-metadata` is explicitly passed.  
Mandatory `Issue-First` workflow executes strictly before developing tests (`EXEC-2`) or writing code in any GitHub-backed repository: agents are strictly prohibited from creating or editing any test file, production code file, or versioned deliverable before stating the current problem in an open parent/strategic GitHub issue (`df_github_issue.py create` without `--parent`, or verifying an already-open user-provided parent issue via `df_github_issue.py fetch`).  
Unparented `df_github_issue.py create` enforces `pre_flight_issue_first` and rejects issue creation whenever the local repository already contains uncommitted governed test, code, or deliverable changes; child subtask issues (`--parent <N>`) may be created while the parent issue remains open, and closing the parent issue closes that work cycle so subsequent work requires a new open parent issue.  
`Issue-First` is enforced live by `EXEC-5-ISSUE-FIRST-GATE` (`PreToolUse`, running strictly before `EXEC-2-TDD-GATE`), Git `pre-commit`, `answer-check`, `answer-prepare`, and `Stop` (`issue_first_check`, never bypassed by `recover-turn-violation`); inspect active-turn status via `harness.py issue-first-check`.  
GitHub issue titles using three-or-more-item enumerations (`"X, Y, and Z"`, `"X, Y and Z"`, `"X; Y; Z"`, `"X, Y, Z"`) are prohibited (`ENUMERATED_SLOP_TITLE`): state a single cohesive problem in a parent issue or a single autonomous subtask in a child issue.  
When auditing or diagnosing defects and remediation methods in an issue-tracked `code` repository, record a parent GitHub issue documenting the original problem and verified root causes rather than bundling multiple `M-...` remediations into one issue.  
When implementing multiple autonomous subtasks (such as multiple `M-...` recommendations or independent specification items), document the original problem in a parent GitHub issue, create a separate child issue per autonomous subtask via `df_github_issue.py create --parent <N>` with a link to the parent issue in its body, commit each child issue in its own separate Git commit (`https://github.com/<owner>/<repo>/issues/<child>`), close each child issue via `df_github_issue.py close` after `git push`, and close the parent issue once all its child subtasks are completed.  
Perform any code changes in `code` repositories strictly by first creating or linking the corresponding GitHub Issue via `/df-github-issue`, referencing the full issue URL in relevant code comments, setting the commit message to contain only the full GitHub Issue URL (`https://github.com/<owner>/<repo>/issues/<N>`), and closing the issue via `df_github_issue.py close` after `git push` (without bypassing Harness Git hooks via `--no-verify`), while maintaining the Unified Journal `ꙮ`.  
Agent commits modifying production code must stage substantive behavioral tests and satisfy the Test Ratchet (`EXEC-2`) enforced by Git `pre-commit`, `check_commit`, and turn completion (`tdd_check`).  
When modifying code or declared `affiliated_paths` of a member of a `similar_projects` group or overlay in [paths.json](../paths.json), maintain sibling parity within the same turn: update peer code, file or update a porting GitHub issue in the peer repository with saved API read-back Evidence JSON via `df_github_issue.py`, or record an explicit `>= 30`-character technical justification via `harness.py similar-project-exempt`.  
External actions are governed by [SCOPE-2](00-scope.md#scope-2).  
Before responding, verify task completeness, evidence, checks, the journal, and your own temporary files; report the substantive result and anything left unverified.  
Use [unified turn completion](../references/turn-completion.md#answer-preparation); a successful file write does not prove chat delivery, which is verified by native reconciliation.  
Before `answer-prepare`, if context compaction (`CHECKPOINT`) occurred during the active turn, run `recover-checkpoint`.  
## EXEC-6
For instructed actions in a verified account, use the active browser authentication, including cookies, CSRF tokens, and access tokens; a pre-opened page or manual token handoff is not a prerequisite.  
Prefer the service's native UI or in-page API client; a required token may be used in memory in a targeted manner for a verified API of that service without exposing the secret to the model output, command line, files, or logs.  
Do not scrape all cookies or storage searching for `token`/`auth`; identify the specific credential source and recipient per the service contract.  
Distinguish a missing tab, expired login, insufficient operation permissions, and tool policy rejection; successful page reading does not prove write permission.  
Before working with an authenticated portal, read the [authenticated access procedure](../skills/upwork-init/references/authenticated-access.md); permission to use a session does not expand the scope of the instruction to sending messages, making payments, or performing other external changes under [SCOPE-2](00-scope.md#scope-2).  
<!-- https://github.com/dmitry-ai/harness/issues/48 -->  
<!-- https://github.com/dmitry-ai/harness/issues/85 -->  
<!-- https://github.com/dmitry-ai/harness/issues/98 -->  
<!-- https://github.com/dmitry-ai/harness/issues/123 -->  
<!-- https://github.com/dmitry-ai/harness/issues/139 -->  
<!-- https://github.com/dmitry-ai/harness/issues/147 -->  
<!-- https://github.com/dmitry-ai/harness/issues/152 -->  
<!-- https://github.com/dmitry-ai/harness/issues/163 -->  
<!-- https://github.com/dmitry-ai/harness/issues/164 -->  
<!-- https://github.com/dmitry-ai/harness/issues/165 -->  
<!-- https://github.com/dmitry-ai/harness/issues/183 -->  
<!-- https://github.com/dmitry-ai/harness/issues/185 -->  
<!-- https://github.com/dmitry-ai/harness/issues/199 -->  
<!-- https://github.com/dmitry-ai/harness/issues/215 -->  
<!-- https://github.com/dmitry-ai/harness/issues/237 -->  
