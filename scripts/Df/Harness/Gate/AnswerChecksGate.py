# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class AnswerChecksGate:
	__BLOCKED_REPORT_DEFERRED_GATES = frozenset({'code_lifecycle', 'issue_first', 'tdd'})
	# @used-by :meth:`AnswerChecksGate.run()`
	@staticmethod
	def __addon_observability_messages(ctx: dict) -> list[str]:
		chk = ctx.get('addon_obs_chk')
		if None is chk and None is not ctx.get('root'):
			from agent_tools.addon_observability import evaluate_addon_observability
			chk = evaluate_addon_observability(ctx['root'], ctx.get('native'), ctx.get('turn'), ctx.get('value'), ctx.get('response'))
			ctx['addon_obs_chk'] = chk
		return [] if (chk or {}).get('verified', True) else [str(chk['detail'])]
	# @used-by :meth:`AnswerChecksGate.run()`
	@staticmethod
	def __architecture_messages(ctx: dict) -> list[str]:
		chk = ctx.get('arch_chk')
		if None is chk and None is not ctx.get('response'):
			from agent_tools.arch.evaluator import evaluate_response_architecture
			chk = evaluate_response_architecture(ctx.get('root'), ctx.get('turn'), ctx.get('response'), blocked_report=bool(ctx.get('blocked_report')))
			ctx['arch_chk'] = chk
		return [] if (chk or {}).get('verified', True) else list((chk or {}).get('violations') or [])
	# @used-by :meth:`AnswerChecksGate.run()`
	@staticmethod
	def __build_checks_map(ctx: dict) -> dict[str, bool]:
		return {
			'addon_observability': bool((ctx.get('addon_obs_chk') or {}).get('verified', True)), 'architecture': bool((ctx.get('arch_chk') or {}).get('verified', True)),
			'causal_probability': not ctx['prob_errs'], 'code_lifecycle': bool(ctx['lifecycle_chk'].get('verified', True)),
			'compaction': bool(ctx['comp_chk'].get('verified', True) and (not ctx['evicted_cited'])), 'delegation': bool(ctx['del_chk'].get('verified', True) and (not ctx['del_chk'].get('aa_partial_read_violations'))),
			'doc4': not ctx['doc4_errs'], 'exec5': bool(ctx['exec5_chk'].get('verified', True)),
			'hook_crash': bool((ctx.get('hook_crash_chk') or {}).get('verified', True)), 'http_fetch': bool(ctx['http_chk'].get('verified', True)),
			'issue_first': bool(ctx['issue_first_chk'].get('verified', True)), 'language_and_stub': not ctx['lang_errs'],
			# 2026-11-28 "Wire ProblemReportEvaluator into answer-check, answer-prepare, Stop Gate, TurnAuditor, and CrashAuditor": https://github.com/dmitry-ai/harness/issues/430
			'links': not ctx['link_errs'], 'problem_report': bool((ctx.get('problem_report_chk') or {}).get('verified', True)),
			'scope_deferral': bool((ctx.get('scope_deferral_chk') or {}).get('verified', True)),
			'source_grounding': not ctx['source_errs'], 'tdd': bool(ctx['tdd_chk'].get('verified', True)),
			'verification_observability': bool((ctx.get('verification_observability_chk') or {}).get('verified', True)), 'workflow': not ctx['wf_errs'],
		}
	# @used-by :meth:`AnswerChecksGate.run()`
	@staticmethod
	def __compaction_messages(ctx: dict) -> list[str]:
		msgs: list[str] = []
		comp = ctx['comp_chk']
		if ctx['role'] in ('primary', 'child') and (not comp.get('verified', True)):
			unreread = comp.get('unreread_analysis_sources') or []
			msgs.append(('COMPACT-1 / KB-3 violation in active turn: analysis.md written after CHECKPOINT without re-reading evicted sibling source.md: ' + ', '.join(unreread)) if unreread else 'COMPACT-1 / KB-3 violation in active turn: context compaction (CHECKPOINT) occurred after tool calls without post-checkpoint recovery; run recover-checkpoint or inspect transcript_full.jsonl before answer-prepare')
		return msgs
	# @used-by :meth:`AnswerChecksGate.run()`
	@staticmethod
	def __delegation_messages(ctx: dict) -> list[str]:
		del_chk = ctx['del_chk']
		msgs: list[str] = []
		if 'primary' == ctx['role'] and (not del_chk.get('verified', True)):
			msgs.append(f"REVIEW-1 / KB-3 violation in active turn: bulk primary-agent research (tool_steps={del_chk.get('tool_step_count', 0)}, max_streak={del_chk.get('max_unpersisted_step_streak', 0)} > {del_chk.get('max_unpersisted_steps', 40)}) executed without A.F/A.A subagent delegation or incremental \ua616/KB persistence")
		return msgs
	# @used-by :meth:`AnswerChecksGate.run()`
	@staticmethod
	def __evicted_messages(ctx: dict) -> list[str]:
		ev = ctx['evicted_cited']
		return ['COMPACT-1 / KB-3 violation in active turn: primary source file(s) read before CHECKPOINT were evicted from context and cited in response without re-reading after checkpoint: ' + ', '.join(ev)] if ev else []
	# @used-by :meth:`AnswerChecksGate.run()`
	@staticmethod
	def __exec5_messages(ctx: dict) -> list[str]:
		chk = ctx['exec5_chk']
		if chk.get('verified', True):
			r: list[str] = []
		else:
			cmds = [cmd for item in chk.get('violations') or [] for cmd in item.get('commands', [])]
			r = ['EXEC-5 violation in active turn (git read command without --no-optional-locks; run recover-turn-violation): ' + '; '.join(cmds)]
		return r
	# @used-by :meth:`AnswerChecksGate.run()`
	@staticmethod
	def __hook_crash_messages(ctx: dict) -> list[str]:
		chk = ctx.get('hook_crash_chk') or {}
		return [] if chk.get('verified', True) else [str(chk.get('detail') or 'DOC-5 / EXEC-5 hook_crash_check: unhandled JSON hook failure in active turn')]
	# @used-by :meth:`AnswerChecksGate.run()`
	@staticmethod
	def __http_messages(ctx: dict) -> list[str]:
		chk = ctx['http_chk']
		if chk.get('verified', True):
			r: list[str] = []
		else:
			cmds = [cmd for item in chk.get('violations') or [] for cmd in item.get('commands', [])]
			r = ['KB-3 / EXEC-1 violation in active turn (ad-hoc HTTP fetch in shell without persistent Evidence collection): ' + '; '.join(cmds)]
		return r
	# @used-by :meth:`AnswerChecksGate.run()`
	@staticmethod
	def __lifecycle_messages(ctx: dict) -> list[str]:
		chk = ctx['lifecycle_chk']
		return [] if chk.get('verified', True) else [f'EXEC-5 violation in active turn (code/issue lifecycle incomplete): {v}' for v in chk.get('violations') or []]
	# @used-by :meth:`AnswerChecksGate.run()`
	@staticmethod
	def __partial_read_messages(ctx: dict) -> list[str]:
		p_viols = ctx['del_chk'].get('aa_partial_read_violations') or []
		return ['REVIEW-3 / REVIEW-4: Independent A.A reviewer subagent performed a partial/truncated read of the candidate response: ' + '; '.join(p_viols)] if p_viols else []
	# 2026-11-28 "Wire ProblemReportEvaluator into answer-check, answer-prepare, Stop Gate, TurnAuditor, and CrashAuditor": https://github.com/dmitry-ai/harness/issues/430
	# @used-by :meth:`AnswerChecksGate.run()`
	@staticmethod
	def __problem_report_messages(ctx: dict) -> list[str]:
		chk = ctx.get('problem_report_chk')
		if None is chk and None is not ctx.get('response'):
			from Df.Harness.Grounding.ProblemReportEvaluator import ProblemReportEvaluator
			turn = ctx.get('turn')
			reqs = list(turn.get('requests') or ()) if isinstance(turn, dict) and 'primary' == ctx.get('role') else []
			chk = ProblemReportEvaluator(ctx.get('root'), turn, ctx.get('value'), ctx.get('response'), requests=reqs, native=ctx.get('native')).evaluate()
			ctx['problem_report_chk'] = chk
		return [] if (chk or {}).get('verified', True) else list((chk or {}).get('violations') or [])
	# @used-by :meth:`AnswerChecksGate.run()`
	@staticmethod
	def __scope_deferral_messages(ctx: dict) -> list[str]:
		chk = ctx.get('scope_deferral_chk')
		if None is chk:
			from agent_tools.scope_deferral import evaluate_scope_deferral
			chk = evaluate_scope_deferral(ctx.get('turn'), ctx.get('value'), ctx.get('lifecycle_chk'), ctx.get('response'), blocked_report=bool(ctx.get('blocked_report')))
			ctx['scope_deferral_chk'] = chk
		return [] if chk.get('verified', True) else list(chk.get('violations') or ())
	# @used-by :meth:`AnswerChecksGate.run()`
	@staticmethod
	def __verification_obs_messages(ctx: dict) -> list[str]:
		chk = ctx.get('verification_observability_chk')
		if None is chk and None is not ctx.get('root'):
			from agent_tools.verification_observability import evaluate_verification_observability
			chk = evaluate_verification_observability(ctx['root'], ctx.get('native'), ctx.get('turn') or ctx.get('turn_obj'), ctx.get('value') or ctx.get('value_obj'), ctx.get('response'))
			ctx['verification_observability_chk'] = chk
		return [] if (chk or {}).get('verified', True) else [str(chk.get('detail') or 'EXEC-2 / VERIFY-4 verification_observability_check: unresolved shadow-replay failure in active turn')]
	ANSWER_GATES = (
		('doc4', 'response.doc4', lambda c: list(c['doc4_errs'])),
		('links', 'response.links', lambda c: list(c['link_errs'])),
		('causal_probability', 'response.doc2', lambda c: list(c['prob_errs'])),
		('source_grounding', 'response.grounding', lambda c: list(c['source_errs'])),
		('problem_report', 'response.problem_report', __problem_report_messages),
		('language_and_stub', 'response.language', lambda c: list(c['lang_errs'])),
		('exec5', 'turn.exec5', __exec5_messages),
		('hook_crash', 'turn.hook_crash', __hook_crash_messages),
		('addon_observability', 'turn.addon_observability', __addon_observability_messages),
		('verification_observability', 'turn.verification_observability', __verification_obs_messages),
		('architecture', 'response.architecture', __architecture_messages),
		('http_fetch', 'turn.http_fetch', __http_messages),
		('compaction', 'turn.compaction', __compaction_messages),
		('evicted_citations', 'turn.evicted_citations', __evicted_messages),
		('delegation', 'turn.delegation', __delegation_messages),
		('aa_partial_read', 'turn.aa_partial_read', __partial_read_messages),
		('issue_first', 'turn.issue_first', lambda c: [] if c['issue_first_chk'].get('verified', True) else list(c['issue_first_chk'].get('violations') or [])),
		('code_lifecycle', 'turn.code_lifecycle', __lifecycle_messages),
		('scope_deferral', 'turn.scope_deferral', __scope_deferral_messages),
		('tdd', 'turn.tdd', lambda c: [] if c['tdd_chk'].get('verified', True) else list(c['tdd_chk'].get('violations') or [])),
		('workflow', 'turn.workflow', lambda c: list(c['wf_errs'])),
	)
	# @used-by :func:`agent_tools.gates.answer_checks.run_answer_gates()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_pretool_classes_cover_all_guards()`
	# @uses :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__addon_observability_messages()`
	# @uses :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__architecture_messages()`
	# @uses :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__compaction_messages()`
	# @uses :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__delegation_messages()`
	# @uses :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__evicted_messages()`
	# @uses :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__exec5_messages()`
	# @uses :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__hook_crash_messages()`
	# @uses :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__http_messages()`
	# @uses :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__lifecycle_messages()`
	# @uses :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__partial_read_messages()`
	# @uses :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__problem_report_messages()`
	# @uses :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__scope_deferral_messages()`
	# @uses :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__verification_obs_messages()`
	def run(self, ctx: dict) -> tuple[list[dict], dict[str, bool]]:
		issues: list[dict] = []
		seen: set[str] = set()
		deferred = AnswerChecksGate.__BLOCKED_REPORT_DEFERRED_GATES if ctx.get('blocked_report') else frozenset()
		for gate_id, code, fn in AnswerChecksGate.ANSWER_GATES:
			if gate_id in deferred:
				continue
			for msg in fn(ctx):
				if msg and msg not in seen:
					seen.add(msg)
					issues.append({'code': code, 'gate_id': gate_id, 'message': msg})
		return (issues, AnswerChecksGate.__build_checks_map(ctx))
