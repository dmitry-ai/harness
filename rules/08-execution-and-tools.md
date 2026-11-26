---
trigger: always_on
description: "Core execution invariants: deterministic tools, Red-First TDD, foreground lifecycle, Issue-First Git/worktree workflow"
---
# Execution
## EXEC-1
Use existing parameterized tools from [README-agent-tools.md](../scripts/README-agent-tools.md) (read when choosing Harness CLI subcommands or flags) instead of one-off scripts.  
Collect external HTTP(S)/DOM evidence via `harness.py collect|collect-http|collect-browser` (`--browser auto`); direct shell HTTP calls (`curl`/`urllib`/`requests`/`Invoke-WebRequest`) and `search_web` quotes are prohibited.  
After three fruitless searches on the same question, report the specific gap or justify a method change.  
## EXEC-2
In GitHub-backed repositories, satisfy `Issue-First` ([EXEC-5](#exec-5)) before writing any test or code.  
Mandatory Red-First TDD for software code: write a behavioral test (no source-reading or empty stubs) and observe failure (`Red`) before editing production code (`Green`).  
One-way Test Ratchet: never delete, skip, or weaken tests/assertions without audited `RATCHET-OK` (`>= 30` chars citing a requirement/decision via `harness.py ratchet-ok` or linked issue).  
Run narrow fail-fast tests (`-x`/`-f`, `WaitMsBeforeAsync: 10000`) during Red/Green and the full test suite (`harness.py run-tests` or parallel `pytest -x`) after the final edit (`harness.py tdd-check`).  
## EXEC-3
Never navigate, reload, steal focus from, or close user-owned browser tabs, never terminate the shared browser or delete its lock files, and open agent-owned tabs in the verified profile instead of asking the user to pre-open pages.  
## EXEC-4
Harness follows the foreground-only lifecycle in [FILE-3](01-file-boundaries.md#file-3) and bounds test or child commands with in-process timeouts; never attach one-shot `schedule` timers (`DurationSeconds`) to active `run_command` or `invoke_subagent` tasks.  
Serialize repo landings via `harness.py land-acquire --wait` / `land-release` (or `swarm` / `workspace: "share"`), exhausting foreground waits (`wait-repo`, `land-acquire --wait`, `answer-prepare --wait-timeout`) before escalating lock contention.  
## EXEC-5
Mandatory `Issue-First`: before creating or editing any test, code, or versioned deliverable in a GitHub-backed repository, state the problem in an open parent GitHub issue via `df_github_issue.py create` or register an existing open issue via `fetch` (inspect via `harness.py issue-first-check`).  
Follow [df-github-issue](../skills/df-github-issue/SKILL.md) (read before GitHub issue actions) for `--body-file`, `--parent <N>` per subtask, issue URL comments, URL-only commits, `git push`, `harness.py repo-tag` (`YYYY-MM-DD` / `YYYY-MM-DD--<N>`) on closing commits ([LINK-6](02-link-standards.md#link-6)), and `close` without `--no-verify`.  
Isolate concurrent repository work—and unconditionally all edits in Harness—inside a linked worktree (`harness.py worktree-begin` / `worktree-land`), executing `build-native` and `install-global` only on `main`; run read-only Git checks with `--no-optional-locks` (or `harness.py git-read`).  
Maintain sibling parity for declared `similar_projects` peers in [paths.json](../paths.json) (update peer code, file a peer issue, or record `harness.py similar-project-exempt`), and finalize every turn via [turn-completion.md](../references/turn-completion.md#answer-preparation) (`answer-prepare`, running `recover-checkpoint` if compacted).  
## EXEC-6
Before accessing any authenticated portal or session cookie/token, read [authenticated-access.md](../skills/upwork-init/references/authenticated-access.md) and restrict external actions to explicit instructions under [SCOPE-2](00-scope.md#scope-2).  
