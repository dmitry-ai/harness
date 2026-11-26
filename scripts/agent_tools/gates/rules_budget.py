# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.RulesBudgetGate import RulesBudgetGate
NAME = RulesBudgetGate.NAME
PRIORITY = RulesBudgetGate.PRIORITY
TOOLS = RulesBudgetGate.TOOLS
# @used-by :meth:`Df.Harness.Gate.PreToolRegistry.PreToolRegistry.__load_builtin_entry()`
# @used-by :meth:`test_rules_audit.RulesAuditTests.test_pre_tool_use_rules_budget_and_doctor_and_pre_commit_enforce_limits()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	return RulesBudgetGate().check(name, args, payload)
