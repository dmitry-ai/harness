# Harness: Codex

<!-- Generated from canonical rules; https://github.com/dmitry-ai/harness/issues/35 -->

Read the listed canonical rule sources before executing the task.  
Shared always_on rules and the Codex adapter are mandatory in every new chat, including child subagents.  
For project-specific sources, honor the frontmatter trigger; links are not copies of the rules.  
First run the Python tool "C:/work/research/provision/code/AI/harness/code/scripts/harness.py" policy-instructions --platform codex; apply the returned global developer_instructions of the active profile in addition to these rules.  
That command reads only the required TOML key rather than the entire configuration file.  
- C:/work/research/provision/code/AI/harness/code/rules/00-scope.md
- C:/work/research/provision/code/AI/harness/code/rules/01-file-boundaries.md
- C:/work/research/provision/code/AI/harness/code/rules/02-link-standards.md
- C:/work/research/provision/code/AI/harness/code/rules/03-language-lexicon.md
- C:/work/research/provision/code/AI/harness/code/rules/04-statement-structure.md
- C:/work/research/provision/code/AI/harness/code/rules/05-verification-audit.md
- C:/work/research/provision/code/AI/harness/code/rules/06-knowledge-base.md
- C:/work/research/provision/code/AI/harness/code/rules/07-review-and-delegation.md
- C:/work/research/provision/code/AI/harness/code/rules/08-execution-and-tools.md
- C:/work/research/provision/code/AI/harness/code/rules/09-initial-analysis.md
- C:/work/research/provision/code/AI/harness/code/rules/10-client-text.md
- C:/work/research/provision/code/AI/harness/code/platforms/codex.md
Then, in the exact project root of the current chat, read local .agents/rules/*.md and .agents/rules.json.  
Read all additional path sources from rules.json while honoring their trigger; you do not need to re-read the shared rules directory.  
Never pick a neighboring project.  
If the root of the current task is unknown, determine it from the explicit chat binding.  
For the established root of every turn, run the Python tool "C:/work/research/provision/code/AI/harness/code/scripts/harness.py" turn-begin "<exact root of current chat>" --platform codex; the UUID is read from CODEX_THREAD_ID and the profile from CODEX_HOME.  
FILE-3 and EXEC-5 also apply to ordinary analytical responses and .agents investigations; the article/proposal profile does not define their scope.  
Run read-only Git checks with `--no-optional-locks` so the index is not updated as a side effect (or via harness.py git-read; read rules in batches without Get-Content output truncation and do not bundle git calls with initial rule reading before turn-begin completes).  
Before publishing the final response, the primary agent runs answer-prepare with the exact UTF-8 bytes per references/turn-completion.md; a child subagent does not maintain the user journal.  
