# Open-Closed Plugin Registries and Code Size Ratchet

`scripts/agent_tools/gates/` discovers `PreToolUse` gate plugins automatically in ascending `(PRIORITY, NAME)` order via `discover_pre_tool_gates()` and `run_pre_tool_gates()`, keeping `EXEC-5-ISSUE-FIRST-GATE` (`100`) strictly before `EXEC-2-TDD-GATE` (`110`) and `CODE-SIZE-RATCHET-GATE` (`120`).  
`scripts/agent_tools/gates/stop_checks.py` and `scripts/agent_tools/gates/answer_checks.py` centralize `Stop` and `answer-check` gate registries without bloating `check_stop_gate.py` or `completion.py`.  
`scripts/agent_tools/cli_registry.py` and `scripts/agent_tools/cli_domains.py` register CLI subcommands declaratively; run `harness.py cli-docs` to render the current command index directly from the registry.  
`scripts/agent_tools/code_size_gate.py` enforces `CODE-4` (`<= 20` executable SLOC and `<= 8` McCabe complexity per production function, `<= 300` executable SLOC per production file, semicolon anti-gaming guard, and a one-way ratchet for pre-existing legacy files) in both `PreToolUse` and Git `pre-commit`.  
Add new tests in dedicated per-feature `tests/test_<feature>.py` modules instead of appending to monolithic test files.  
<!-- https://github.com/dmitry-ai/harness/issues/168 -->  
