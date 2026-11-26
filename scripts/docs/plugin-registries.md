<!-- 2026-11-23 "Replace monolithic CLI router with declarative registry and modular docs": https://github.com/dmitry-ai/harness/issues/168 -->  
# Open-Closed Plugin Registries and Code Size Ratchet

<!-- 2026-11-26 "Add deterministic rules-audit CLI and aggregate budget enforcement": https://github.com/dmitry-ai/harness/issues/244 -->  
`scripts/agent_tools/gates/` discovers `PreToolUse` gate plugins automatically in ascending `(PRIORITY, NAME)` order via `discover_pre_tool_gates()` and `run_pre_tool_gates()`, keeping `RULES-BUDGET-GATE` (`10`, enforcing local `.agents/rules/` and shared `rules/*.md` budgets plus HTML-comment stripping), `EXEC-5-ISSUE-FIRST-GATE` (`100`) strictly before `EXEC-2-TDD-GATE` (`110`), `CODE-SIZE-RATCHET-GATE` (`120`), and `CODE-STYLE-GATE` (`125`, AST/tokenize `CODE-1` Python style ratchet).  
`scripts/agent_tools/gates/stop_checks.py` and `scripts/agent_tools/gates/answer_checks.py` centralize `Stop` and `answer-check` gate registries without bloating `check_stop_gate.py` or `completion.py`.  
`scripts/agent_tools/cli_registry.py` and `scripts/agent_tools/cli_domains.py` register CLI subcommands declaratively; run `harness.py cli-docs` to render the current command index directly from the registry.  
<!-- 2026-11-26 "Add deterministic rules-audit CLI and aggregate budget enforcement": https://github.com/dmitry-ai/harness/issues/244 -->  
`scripts/agent_tools/code_size_gate.py`, `scripts/agent_tools/code_style_gate.py`, and `scripts/agent_tools/rules_audit.py` enforce `CODE-4`, `CODE-1` Python style ratchets, and shared-rule configuration smell audits in both `PreToolUse` and Git `pre-commit` (`staged_gates.py`).  
Add new tests in dedicated per-feature `tests/test_<feature>.py` modules instead of appending to monolithic test files.  
