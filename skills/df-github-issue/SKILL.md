---
name: df-github-issue
description: "Creates, edits, comments on, closes, and audits GitHub issues via UTF-8 file input and API read-back without PowerShell corruption; use for /df-github-issue and any work with GitHub issues."
---
# Working with GitHub Issues Without Syntax Corruption

Shared tool: `C:/work/research/provision/code/AI/harness/code/scripts/df_github_issue.py`.  
All creation, editing, commenting, closing, and auditing of GitHub issues in Windows PowerShell must be executed exclusively through this tool using a UTF-8 file without BOM.  

## Prohibited `gh` Invocation Patterns in PowerShell

Never pass Markdown issue bodies or comments via command-line arguments or an unconfigured PowerShell pipeline:  
- Prohibited: `--body "..."`, `-b "..."`, `--body @"..."@`, `--comment "..."`: inside PowerShell double quotes, the backtick `` ` `` is an escape prefix, so `` `0 `` turns into a `NUL` byte (`0x00`) and truncates the body at the first null byte in `CreateProcessW`, `` `a ``/`` `b ``/`` `f ``/`` `t ``/`` `v `` turn into ASCII control characters (`0x07`, `0x08`, `0x0C`, `0x09`, `0x0B`), single backticks `` ` `` are stripped, bash-escaped `` \`code\` `` turns into `\code\`, and `$this` / `$var` tokens expand to empty strings.  
- Prohibited: passing a variable `--body $body` to the native `gh.exe` process: in Windows PowerShell 5.1 (`Legacy` argument passing), embedded double quotes `"` are not escaped when assembling the command line, so `CommandLineToArgvW` strips quotes from XML/HTML attributes (`<argument name="session">` becomes `<argument name=session>`) or breaks argument splitting on spaces.  
- Prohibited: piping `@'...'@ | gh issue create --body-file -` or `@'...'@ | python -` without prior UTF-8-no-BOM configuration: by default, `$OutputEncoding` in Windows PowerShell 5.1 is `US-ASCII`, which replaces dashes `–`/`—`, guillemets `«»`, and `§` with `?`, while UTF-8 with preamble prepends `U+FEFF` (`UTF-8 BOM`) to the body and breaks a first-line heading (`\ufeff### Problem`).  

## Mandatory Workflow

1. Write the complete Markdown body or comment to a UTF-8 file without BOM inside `ꘖ/data/scratch/` (or the conversation's scratch directory) using the native `write_file` tool.  
2. Run the required operation via `df_github_issue.py`:  
   - Pre-flight syntax check of the Markdown file without network calls:  
     `python "C:/work/research/provision/code/AI/harness/code/scripts/df_github_issue.py" lint --title "<title>" --body-file "<path/to/body.md>"`  
   - Create an issue with pre-flight syntax checking, UTF-8 stdin JSON transport to `gh api`, and byte-exact read-back verification from GitHub:  
     `python "C:/work/research/provision/code/AI/harness/code/scripts/df_github_issue.py" create --repo <owner/repo> --title "<title>" --body-file "<path/to/body.md>" [--label "<labels>"] --consume-input`  
   - Edit an existing issue with full read-back verification:  
     `python "C:/work/research/provision/code/AI/harness/code/scripts/df_github_issue.py" edit --repo <owner/repo> --issue <N> --body-file "<path/to/body.md>" [--title "<new-title>"] --consume-input`  
   - Add or update an issue comment:  
     `python "C:/work/research/provision/code/AI/harness/code/scripts/df_github_issue.py" comment --repo <owner/repo> (--issue <N> | --comment-id <ID>) --body-file "<path/to/comment.md>" --consume-input`  
   - Close an issue with a verified closing comment:  
     `python "C:/work/research/provision/code/AI/harness/code/scripts/df_github_issue.py" close --repo <owner/repo> --issue <N> [--reason completed|not_planned] [--comment-file "<path/to/comment.md>"] --consume-input`  
   - Audit all open and closed issues and comments in a repository for syntax or encoding corruption:  
     `python "C:/work/research/provision/code/AI/harness/code/scripts/df_github_issue.py" audit-repo --repo <owner/repo> --include-comments`  
3. If the title contains double quotes `"`, `$`, or backticks `` ` ``, write the title to a separate UTF-8 file and pass `--title-file "<path/to/title.txt>"`.  
4. Treat the operation as successful only when the exit code is `0` and the tool's JSON output reports `"verified": true`.  
