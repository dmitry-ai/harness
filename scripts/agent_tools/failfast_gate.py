# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.FailfastGate import FailfastGate
from Df.Harness.Gate.ScheduleGate import ScheduleGate
import re
# @used-by :meth:`test_falsifier_and_schedule_subagent_gate_m8.FalsifierAndScheduleSubagentGateM8Tests.test_allows_schedule_after_subagent_finishes_or_on_explicit_slash_schedule()`
# @used-by :meth:`test_falsifier_and_schedule_subagent_gate_m8.FalsifierAndScheduleSubagentGateM8Tests.test_blocks_one_shot_schedule_while_invoke_subagent_is_active()`
# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests.test_schedule_gate_blocks_after_send_message_and_ignores_task_sender()`
# @used-by :mod:`agent_tools.failfast_gate`
def evaluate_pre_tool_use_schedule(name: str, args: dict, payload: dict) -> str | None:
	return ScheduleGate().check(name, args, payload)
# @used-by :func:`check_rules_and_server_gate._apply_failfast()`
# @used-by :meth:`test_pytest_xdist_runner.PytestXdistRunnerTests.test_classify_pytest_xdist_full_suite_and_filtered()`
# @used-by :meth:`test_watchdog_and_timeout_gate.WatchdogAndTimeoutGateTests.test_non_test_command_mentioning_pytest_in_quoted_arg_is_ignored()`
# @used-by :meth:`test_watchdog_and_timeout_gate.WatchdogAndTimeoutGateTests.test_pre_tool_use_normalizes_unbounded_unittest_and_pytest_and_denies_multi_segment()`
# @used-by :mod:`agent_tools.failfast_gate`
def evaluate_pre_tool_use_test_failfast(name: str, args: dict) -> tuple[str | None, dict | None]:
	return FailfastGate().evaluate(name, args)
# @used-by :func:`agent_tools.tdd.evaluator._collect_failfast_warnings()`
# @used-by :mod:`agent_tools.failfast_gate`
def missing_failfast_flag(seg: str) -> tuple[str, str, re.Match] | None:
	return FailfastGate.missing_failfast_flag(seg)
# @used-by :mod:`agent_tools.failfast_gate`
def missing_timeout_guard(seg: str) -> tuple[str, str] | None:
	return FailfastGate.missing_timeout_guard(seg)
__all__ = ['evaluate_pre_tool_use_schedule', 'evaluate_pre_tool_use_test_failfast', 'missing_failfast_flag', 'missing_timeout_guard']
