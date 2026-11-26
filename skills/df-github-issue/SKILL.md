---
name: df-github-issue
description: "Creates, edits, comments on, closes, and audits GitHub issues via UTF-8 file input and API read-back without PowerShell corruption; use for /df-github-issue and any work with GitHub issues."
---
<!-- 2026-10-30 "Implement /df-github-issue skill and df_github_issue.py CLI with UTF-8 file input and mandatory API read-back verification": https://github.com/dmitry-ai/harness/issues/20 -->  
<!-- 2026-10-31 "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow": https://github.com/dmitry-ai/harness/issues/26 -->  
# Working with GitHub Issues Without Syntax Corruption

<!-- 2026-11-20 "Wire V2 filesystem layout across Harness runtime subsystems and shared projections": https://github.com/dmitry-ai/harness/issues/101 -->  
<!-- 2026-11-20 "Replace V2 verbal directory names with Ⰿ/♕/♙ symbols and add Antigravity hook runner": https://github.com/dmitry-ai/harness/issues/103 -->  
Shared tool: `C:/work/research/provision/code/AI/harness/Ⰿ/≻/♕/⛯/scripts/df_github_issue.py`.  
All creation, editing, commenting, closing, and auditing of GitHub issues in Windows PowerShell must be executed exclusively through this tool using a UTF-8 file without BOM.  

## Prohibited `gh` Invocation Patterns in PowerShell

Never pass Markdown issue bodies or comments via command-line arguments or an unconfigured PowerShell pipeline:  
- Prohibited: `--body "..."`, `-b "..."`, `--body @"..."@`, `--comment "..."`: inside PowerShell double quotes, the backtick `` ` `` is an escape prefix, so `` `0 `` turns into a `NUL` byte (`0x00`) and truncates the body at the first null byte in `CreateProcessW`, `` `a ``/`` `b ``/`` `f ``/`` `t ``/`` `v `` turn into ASCII control characters (`0x07`, `0x08`, `0x0C`, `0x09`, `0x0B`), single backticks `` ` `` are stripped, bash-escaped `` \`code\` `` turns into `\code\`, and `$this` / `$var` tokens expand to empty strings.  
- Prohibited: passing a variable `--body $body` to the native `gh.exe` process: in Windows PowerShell 5.1 (`Legacy` argument passing), embedded double quotes `"` are not escaped when assembling the command line, so `CommandLineToArgvW` strips quotes from XML/HTML attributes (`<argument name="session">` becomes `<argument name=session>`) or breaks argument splitting on spaces.  
- Prohibited: piping `@'...'@ | gh issue create --body-file -` or `@'...'@ | python -` without prior UTF-8-no-BOM configuration: by default, `$OutputEncoding` in Windows PowerShell 5.1 is `US-ASCII`, which replaces dashes `–`/`—`, guillemets `«»`, and `§` with `?`, while UTF-8 with preamble prepends `U+FEFF` (`UTF-8 BOM`) to the body and breaks a first-line heading (`\ufeff### Problem`).  

<!-- 2026-11-18 "Document parent-child issue decomposition and enumerated title ban in EXEC-5 and df-github-issue": https://github.com/dmitry-ai/harness/issues/85 -->  
## Prohibited Enumerated Titles and Monolithic Bundling

Never write three-or-more-item enumerated issue titles (`"X, Y, and Z"`, `"X, Y and Z"`, `"X; Y; Z"`, `"X, Y, Z"`); `df_github_issue.py` rejects them with `ENUMERATED_SLOP_TITLE`.  
Never bundle multiple autonomous `M-...` subtasks into a single issue or a single commit (`BUNDLED_SUBTASKS_IN_SINGLE_ISSUE`).  

<!-- 2026-11-18 "Document parent-child issue decomposition and enumerated title ban in EXEC-5 and df-github-issue": https://github.com/dmitry-ai/harness/issues/85 -->  
<!-- 2026-11-23 "Codify mandatory pre-TDD Issue-First workflow in Harness rules and documentation": https://github.com/dmitry-ai/harness/issues/147 -->  
## Parent Problem Issues, Issue-First Order, and Per-Subtask Child Issues

1. Follow the mandatory `Issue-First` workflow strictly before writing any tests or code in any GitHub-backed repository: first state the problem and root causes in a single open parent/strategic issue via `df_github_issue.py create` (without `--parent`), or register an existing open user-provided parent issue via `df_github_issue.py fetch --repo <owner/repo> --issue <N>`.  
1. Do not write tests or code first and file an issue afterward: unparented `df_github_issue.py create` enforces `pre_flight_issue_first` and exits with code `2` whenever the local repository already has uncommitted governed test, code, or deliverable files, while `EXEC-5-ISSUE-FIRST-GATE` blocks governed edits before an open parent issue is established in the active turn.  
1. Do not bundle `M-...` implementations into the parent issue or commit code directly against it; once the parent issue is open, create a separate child issue per autonomous subtask via `df_github_issue.py create --parent <parent_number>` (requiring the parent issue to be `open`) and start its body with `Parent: [Issue #<parent_number>](https://github.com/<owner>/<repo>/issues/<parent_number>)`.  
<!-- 2026-11-26 "Codify daily Git tagging and tagged GitHub links in rules and documentation": https://github.com/dmitry-ai/harness/issues/265 -->  
<!-- 2026-11-26 "Codify contextual issue-comment placement standard in Harness rules": https://github.com/dmitry-ai/harness/issues/272 -->  
1. Commit each child issue in its own separate Git commit whose message is only `https://github.com/<owner>/<repo>/issues/<child_number>`, placing each required issue URL comment immediately before the modified code block or in the header of a wholly changed function/method/class (never dumping partial-edit issue comments into the file header, and writing `YYYY-MM-DD Dmitrii Fediuk https://github.com/dmitrii-fediuk` once per file in the header with its creation date per [issue-comments.md](../../references/code-formatting/issue-comments.md)), push, assign and push a daily Git tag (`YYYY-MM-DD` or `YYYY-MM-DD--<N>`) via `harness.py repo-tag <repo> --commit <sha> --push` (enforced by `df_github_issue.py close` and `issue_lifecycle.py`), close each child issue via `df_github_issue.py close`, and close the parent issue only after all child subtasks are completed.  

## Mandatory Workflow

1. Write the complete Markdown body or comment to a UTF-8 file without BOM inside `ꘖ/data/scratch/` (or the conversation's scratch directory) using the native `write_file` tool.  
<!-- 2026-11-18 "Document parent-child issue decomposition and enumerated title ban in EXEC-5 and df-github-issue": https://github.com/dmitry-ai/harness/issues/85 -->  
<!-- 2026-11-20 "Wire V2 filesystem layout across Harness runtime subsystems and shared projections": https://github.com/dmitry-ai/harness/issues/101 -->  
<!-- 2026-11-20 "Replace V2 verbal directory names with Ⰿ/♕/♙ symbols and add Antigravity hook runner": https://github.com/dmitry-ai/harness/issues/103 -->  
2. Run the required operation via `df_github_issue.py`:  
   - Pre-flight syntax check of the Markdown file without network calls:  
     `python "C:/work/research/provision/code/AI/harness/Ⰿ/≻/♕/⛯/scripts/df_github_issue.py" lint --title "<title>" --body-file "<path/to/body.md>" [--repo <owner/repo>] [--parent <N>]`  
<!-- 2026-11-23 "Codify mandatory pre-TDD Issue-First workflow in Harness rules and documentation": https://github.com/dmitry-ai/harness/issues/147 -->  
   - Fetch and verify an existing GitHub issue (persisting read-back Evidence JSON for `Issue-First` tracking when working on an already-open parent issue):  
     `python "C:/work/research/provision/code/AI/harness/Ⰿ/≻/♕/⛯/scripts/df_github_issue.py" fetch --repo <owner/repo> --issue <N> [--project-root "<path>"]`  
<!-- 2026-11-23 "Codify mandatory pre-TDD Issue-First workflow in Harness rules and documentation": https://github.com/dmitry-ai/harness/issues/147 -->  
<!-- 2026-11-23 "Document JSON metadata header contract in rules and references": https://github.com/dmitry-ai/harness/issues/152 -->  
   - Create an issue with `pre_flight_issue_first` dirty-repo guard (for unparented issues), pre-flight syntax checking, UTF-8 stdin JSON transport to `gh api`, automatic prepending of a tab-indented JSON metadata header (`Time` in the computer's local timezone, `Issue`, `Project`, `Journal`, `Agent` with `System`/`Instance`/`Model`/`Effort`, and `Trace`; opt out via `--no-metadata`), and byte-exact read-back verification from GitHub:  
     `python "C:/work/research/provision/code/AI/harness/Ⰿ/≻/♕/⛯/scripts/df_github_issue.py" create --repo <owner/repo> [--parent <N>] --title "<title>" --body-file "<path/to/body.md>" [--label "<labels>"] [--no-metadata] --consume-input`  
   - Edit an existing issue with full read-back verification:  
     `python "C:/work/research/provision/code/AI/harness/Ⰿ/≻/♕/⛯/scripts/df_github_issue.py" edit --repo <owner/repo> --issue <N> [--parent <P>] [--body-file "<path/to/body.md>"] [--title "<new-title>"] --consume-input`  
   - Add or update an issue comment:  
     `python "C:/work/research/provision/code/AI/harness/Ⰿ/≻/♕/⛯/scripts/df_github_issue.py" comment --repo <owner/repo> (--issue <N> | --comment-id <ID>) --body-file "<path/to/comment.md>" --consume-input`  
   - Close an issue with a verified closing comment:  
     `python "C:/work/research/provision/code/AI/harness/Ⰿ/≻/♕/⛯/scripts/df_github_issue.py" close --repo <owner/repo> --issue <N> [--reason completed|not_planned] [--comment-file "<path/to/comment.md>"] --consume-input`  
   - Audit all open and closed issues and comments in a repository for syntax or encoding corruption:  
     `python "C:/work/research/provision/code/AI/harness/Ⰿ/≻/♕/⛯/scripts/df_github_issue.py" audit-repo --repo <owner/repo> --include-comments`  
3. If the title contains double quotes `"`, `$`, or backticks `` ` ``, write the title to a separate UTF-8 file and pass `--title-file "<path/to/title.txt>"`.  
4. Treat the operation as successful only when the exit code is `0` and the tool's JSON output reports `"verified": true`.  
