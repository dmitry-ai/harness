# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-24
# "Allow blocked-report journaling over hygiene gates with DOC-5 compatibility":
# https://github.com/dmitry-ai/harness/issues/225
_BLOCKED_REPORT_DEFERRED_GATES = frozenset({'code_lifecycle', 'issue_first', 'tdd'})
# 2026-11-26 "Harden addon companion observability and conflict reservation hygiene": https://github.com/dmitry-ai/harness/issues/302
# @used-by :mod:`agent_tools.gates.answer_checks`
def _addon_observability_messages(ctx: dict) -> list[str]:
	chk = ctx.get('addon_obs_chk')
	if None is chk and None is not ctx.get('root'):
		from ..addon_observability import evaluate_addon_observability
		chk = evaluate_addon_observability(ctx['root'], ctx.get('native'), ctx.get('turn'), ctx.get('value'), ctx.get('response'))
		ctx['addon_obs_chk'] = chk
	return [] if (chk or {}).get('verified', True) else [str(chk['detail'])]
# @used-by :mod:`agent_tools.gates.answer_checks`
def _compaction_messages(ctx: dict) -> list[str]:
	msgs: list[str] = []
	comp = ctx['comp_chk']
	if ctx['role'] in ('primary', 'child') and (not comp.get('verified', True)):
		unreread = comp.get('unreread_analysis_sources') or []
		msgs.append(('COMPACT-1 / KB-3 violation in active turn: analysis.md written after CHECKPOINT without re-reading evicted sibling source.md: ' + ', '.join(unreread)) if unreread else 'COMPACT-1 / KB-3 violation in active turn: context compaction (CHECKPOINT) occurred after tool calls without post-checkpoint recovery; run recover-checkpoint or inspect transcript_full.jsonl before answer-prepare')
	return msgs
# @used-by :mod:`agent_tools.gates.answer_checks`
def _delegation_messages(ctx: dict) -> list[str]:
	del_chk = ctx['del_chk']
	msgs: list[str] = []
	if 'primary' == ctx['role'] and (not del_chk.get('verified', True)):
		msgs.append(f"REVIEW-1 / KB-3 violation in active turn: bulk primary-agent research (tool_steps={del_chk.get('tool_step_count', 0)}, max_streak={del_chk.get('max_unpersisted_step_streak', 0)} > {del_chk.get('max_unpersisted_steps', 40)}) executed without A.F/A.A subagent delegation or incremental \ua616/KB persistence")
	return msgs
# @used-by :mod:`agent_tools.gates.answer_checks`
def _evicted_messages(ctx: dict) -> list[str]:
	ev = ctx['evicted_cited']
	return ['COMPACT-1 / KB-3 violation in active turn: primary source file(s) read before CHECKPOINT were evicted from context and cited in response without re-reading after checkpoint: ' + ', '.join(ev)] if ev else []
# @used-by :mod:`agent_tools.gates.answer_checks`
def _exec5_messages(ctx: dict) -> list[str]:
	chk = ctx['exec5_chk']
	if chk.get('verified', True):
		r: list[str] = []
	else:
		cmds = [cmd for item in chk.get('violations') or [] for cmd in item.get('commands', [])]
		r = ['EXEC-5 violation in active turn (git read command without --no-optional-locks; run recover-turn-violation): ' + '; '.join(cmds)]
	return r
# 2026-11-25
# "Add PreToolUse canary probe to runtime snapshot validation and turn hook-crash audit":
# https://github.com/dmitry-ai/harness/issues/251
# @used-by :mod:`agent_tools.gates.answer_checks`
def _hook_crash_messages(ctx: dict) -> list[str]:
	chk = ctx.get('hook_crash_chk') or {}
	return [] if chk.get('verified', True) else [str(chk.get('detail') or 'DOC-5 / EXEC-5 hook_crash_check: unhandled JSON hook failure in active turn')]
# 2026-11-26 "Add verification observability gate for failed shadow-replay runs": https://github.com/dmitry-ai/harness/issues/296
# @used-by :mod:`agent_tools.gates.answer_checks`
def _verification_obs_messages(ctx: dict) -> list[str]:
	chk = ctx.get('verification_observability_chk')
	if None is chk and None is not ctx.get('root'):
		from ..verification_observability import evaluate_verification_observability
		chk = evaluate_verification_observability(ctx['root'], ctx.get('native'), ctx.get('turn') or ctx.get('turn_obj'), ctx.get('value') or ctx.get('value_obj'), ctx.get('response'))
		ctx['verification_observability_chk'] = chk
	return [] if (chk or {}).get('verified', True) else [str(chk.get('detail') or 'EXEC-2 / VERIFY-4 verification_observability_check: unresolved shadow-replay failure in active turn')]
# @used-by :mod:`agent_tools.gates.answer_checks`
def _http_messages(ctx: dict) -> list[str]:
	chk = ctx['http_chk']
	if chk.get('verified', True):
		r: list[str] = []
	else:
		cmds = [cmd for item in chk.get('violations') or [] for cmd in item.get('commands', [])]
		r = ['KB-3 / EXEC-1 violation in active turn (ad-hoc HTTP fetch in shell without persistent Evidence collection): ' + '; '.join(cmds)]
	return r
# @used-by :mod:`agent_tools.gates.answer_checks`
def _lifecycle_messages(ctx: dict) -> list[str]:
	chk = ctx['lifecycle_chk']
	return [] if chk.get('verified', True) else [f'EXEC-5 violation in active turn (code/issue lifecycle incomplete): {v}' for v in chk.get('violations') or []]
# @used-by :mod:`agent_tools.gates.answer_checks`
def _partial_read_messages(ctx: dict) -> list[str]:
	p_viols = ctx['del_chk'].get('aa_partial_read_violations') or []
	return ['REVIEW-3 / REVIEW-4: Independent A.A reviewer subagent performed a partial/truncated read of the candidate response: ' + '; '.join(p_viols)] if p_viols else []
# 2026-11-26 "Verify explicit user stop consent in clarifications during answer checks": https://github.com/dmitry-ai/harness/issues/375
# @used-by :mod:`agent_tools.gates.answer_checks`
def _scope_deferral_messages(ctx: dict) -> list[str]:
	chk = ctx.get('scope_deferral_chk')
	if None is chk:
		from ..scope_deferral import evaluate_scope_deferral
		chk = evaluate_scope_deferral(ctx.get('turn'), ctx.get('value'), ctx.get('lifecycle_chk'), ctx.get('response'), blocked_report=bool(ctx.get('blocked_report')))
		ctx['scope_deferral_chk'] = chk
	return [] if chk.get('verified', True) else list(chk.get('violations') or ())
# 2026-11-23
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
ANSWER_GATES = (
	('doc4', 'response.doc4', lambda c: list(c['doc4_errs'])),
	('links', 'response.links', lambda c: list(c['link_errs'])),
	('causal_probability', 'response.doc2', lambda c: list(c['prob_errs'])),
	('source_grounding', 'response.grounding', lambda c: list(c['source_errs'])),
	('language_and_stub', 'response.language', lambda c: list(c['lang_errs'])),
	('exec5', 'turn.exec5', _exec5_messages),
	# 2026-11-25
	# "Add PreToolUse canary probe to runtime snapshot validation and turn hook-crash audit":
	# https://github.com/dmitry-ai/harness/issues/251
	('hook_crash', 'turn.hook_crash', _hook_crash_messages),
	# 2026-11-26 "Harden addon companion observability and conflict reservation hygiene": https://github.com/dmitry-ai/harness/issues/302
	('addon_observability', 'turn.addon_observability', _addon_observability_messages),
	# 2026-11-26 "Add verification observability gate for failed shadow-replay runs": https://github.com/dmitry-ai/harness/issues/296
	('verification_observability', 'turn.verification_observability', _verification_obs_messages),
	('http_fetch', 'turn.http_fetch', _http_messages),
	('compaction', 'turn.compaction', _compaction_messages),
	('evicted_citations', 'turn.evicted_citations', _evicted_messages),
	('delegation', 'turn.delegation', _delegation_messages),
	('aa_partial_read', 'turn.aa_partial_read', _partial_read_messages),
	('issue_first', 'turn.issue_first', lambda c: [] if c['issue_first_chk'].get('verified', True) else list(c['issue_first_chk'].get('violations') or [])),
	('code_lifecycle', 'turn.code_lifecycle', _lifecycle_messages),
	# 2026-11-26 "Verify explicit user stop consent in clarifications during answer checks": https://github.com/dmitry-ai/harness/issues/375
	('scope_deferral', 'turn.scope_deferral', _scope_deferral_messages),
	('tdd', 'turn.tdd', lambda c: [] if c['tdd_chk'].get('verified', True) else list(c['tdd_chk'].get('violations') or [])),
	('workflow', 'turn.workflow', lambda c: list(c['wf_errs'])),
)
# @used-by :func:`run_answer_gates()`
def _build_checks_map(ctx: dict) -> dict[str, bool]:
	# 2026-11-25
	# "Add PreToolUse canary probe to runtime snapshot validation and turn hook-crash audit":
	# https://github.com/dmitry-ai/harness/issues/251
	# 2026-11-26 "Harden addon companion observability and conflict reservation hygiene": https://github.com/dmitry-ai/harness/issues/302
	# 2026-11-26 "Add verification observability gate for failed shadow-replay runs": https://github.com/dmitry-ai/harness/issues/296
	# 2026-11-26 "Verify explicit user stop consent in clarifications during answer checks": https://github.com/dmitry-ai/harness/issues/375
	return {'doc4': not ctx['doc4_errs'], 'links': not ctx['link_errs'], 'causal_probability': not ctx['prob_errs'], 'source_grounding': not ctx['source_errs'], 'language_and_stub': not ctx['lang_errs'], 'exec5': bool(ctx['exec5_chk'].get('verified', True)), 'hook_crash': bool((ctx.get('hook_crash_chk') or {}).get('verified', True)), 'addon_observability': bool((ctx.get('addon_obs_chk') or {}).get('verified', True)), 'verification_observability': bool((ctx.get('verification_observability_chk') or {}).get('verified', True)), 'http_fetch': bool(ctx['http_chk'].get('verified', True)), 'compaction': bool(ctx['comp_chk'].get('verified', True) and (not ctx['evicted_cited'])), 'delegation': bool(ctx['del_chk'].get('verified', True) and (not ctx['del_chk'].get('aa_partial_read_violations'))), 'issue_first': bool(ctx['issue_first_chk'].get('verified', True)), 'code_lifecycle': bool(ctx['lifecycle_chk'].get('verified', True)), 'scope_deferral': bool((ctx.get('scope_deferral_chk') or {}).get('verified', True)), 'tdd': bool(ctx['tdd_chk'].get('verified', True)), 'workflow': not ctx['wf_errs']}
# 2026-11-23
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
# @used-by :func:`agent_tools.completion.check_answer()`
# @used-by :meth:`test_clarification_stop_consent.ClarificationStopConsentTests.test_explicit_user_stop_consent_in_clarifications_unblocks_deferral()`
# @used-by :meth:`test_clarification_stop_consent.ClarificationStopConsentTests.test_step_100_102_real_clarifications_rejected_with_open_deferred_children()`
# @used-by :meth:`test_gate_registry.GateRegistryTests.test_answer_gates_collect_issues_and_checks_map()`
# @used-by :meth:`test_incomplete_scope_regression_matrix.IncompleteScopeRegressionMatrixTests.test_step_281_scope_deferral_matrix_blocks_open_children_allows_unrelated_bugs_and_consent()`
# @used-by :meth:`test_journal_clarifications_and_disclosure.JournalClarificationsAndDisclosureTests.test_deferral_disclosure_gate_rejects_silent_response_and_accepts_disclosed_rationale()`
# @used-by :meth:`test_open_child_deferral_gate.OpenChildDeferralGateTests.test_open_deferred_child_blocks_lifecycle_and_answer_gates()`
# @used-by :mod:`agent_tools.gates`
def run_answer_gates(ctx: dict) -> tuple[list[dict], dict[str, bool]]:
	issues: list[dict] = []
	seen: set[str] = set()
	# 2026-11-24
	# "Allow blocked-report journaling over hygiene gates with DOC-5 compatibility":
	# https://github.com/dmitry-ai/harness/issues/225
	deferred = _BLOCKED_REPORT_DEFERRED_GATES if ctx.get('blocked_report') else frozenset()
	for gate_id, code, fn in ANSWER_GATES:
		if gate_id in deferred:
			continue
		for msg in fn(ctx):
			if msg and msg not in seen:
				seen.add(msg)
				issues.append({'code': code, 'gate_id': gate_id, 'message': msg})
	return (issues, _build_checks_map(ctx))
