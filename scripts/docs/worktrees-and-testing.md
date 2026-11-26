<!-- 2026-11-23 "Replace monolithic CLI router with declarative registry and modular docs": https://github.com/dmitry-ai/harness/issues/168 -->  
# Worktrees, FIFO Landing Lease, and Parallel Testing

`harness.py run-tests [<tests-dir>] [--workers N] [--module-timeout S] [--module M] [--no-failfast]` runs `test_*.py` modules in parallel child processes with `-f` and `-b` enabled by default, schedules slower modules first, enforces per-module watchdog timeouts, and terminates sibling workers on the first failure.  
`harness.py land-acquire <repo> [--owner <id>] [--wait] [--timeout S] [--ttl S]` acquires a FIFO landing lease stored in `ꘖ/data/repo-leases/<repo_hash>.json` with PID liveness and TTL eviction; release it via `harness.py land-release <repo>` and inspect queue state via `harness.py land-status <repo>`.  
`harness.py worktree-begin <repo> --task <id> [--base main]` allocates an isolated linked worktree under `project_paths.worktrees_dir` on branch `task/<id>`; inspect worktrees via `worktree-status`, land onto `main` under the FIFO lease (rebase, single parallel full test run, `--ff-only`, optional push/cleanup) via `worktree-land`, and remove worktrees via `worktree-cleanup`.  
Run host-global mutations (`harness.py build-native`, `harness.py install-global`) strictly on `main` during landing rather than inside parallel linked worktrees.  
`df_github_issue.py` accepts `--repo-root <path>` and prioritizes an explicit `--repo-root` or an active linked worktree `cwd` ahead of `project_paths.code_repos`.  

<!-- 2026-11-26 "Add multi-MB hook latency canary and codify multi-track delegation policy": https://github.com/dmitry-ai/harness/issues/357 -->  
## Multi-Track Delegation and Snapshot Promotion Canary

For requests spanning `>= 3` independent coding tracks, prefer short-lived per-track worktrees with parallel `self` subagents on disjoint file scopes and sequential coordinator landings onto `main` via `worktree-land` rather than accumulating a monolithic branch.  
Runtime snapshot promotion runs an isolated multi-MB synthetic transcript `PreToolUse` latency canary that rejects releases whose median latency across `3` runs exceeds `1.5s`, and inspects `fallback.log` for new `TimeoutError` spikes strictly newer than the previous promotion timestamp (blocking promotion only when `fail_on_fallback_spike=True` so emergency hotfixes remain unblocked).  
