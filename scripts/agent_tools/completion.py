# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from . import journal
# 2026-11-13
# "Extract issue_lifecycle.py from completion.py, fix open backlog-issue lifecycle gating, and consolidate Git/issue helpers in git_gate.py":
# https://github.com/dmitry-ai/harness/issues/53
# 2026-11-13
# "Extract ResponseEvidenceAuditor class into response_grounding.py from response_source_and_kb_issues and helpers in completion.py":
# https://github.com/dmitry-ai/harness/issues/56
from .issue_lifecycle import code_and_issue_lifecycle_status as _code_and_issue_lifecycle_status, evidence_issue_files as _evidence_issue_files, evidence_issue_state as _evidence_issue_state, origin_repo_slug as _origin_repo_slug
# 2026-11-26
# "Exempt service finalization calls from PreToolUse TDD gate and add journal-sync --all-open":
# https://github.com/dmitry-ai/harness/issues/256
from .journal_sync_all import reconcile_before_begin, resolve_sync_provenance, sync_all_open
from .platforms import adapter
# 2026-11-13
# "Extract ResponseEvidenceAuditor class into response_grounding.py from response_source_and_kb_issues and helpers in completion.py":
# https://github.com/dmitry-ai/harness/issues/56
from .response_grounding import ResponseEvidenceAuditor, response_source_and_kb_issues
# 2026-11-24
# "Cache runtime settings and deduplicate evidence validation in hot paths":
# https://github.com/dmitry-ai/harness/issues/227
from .runtime import PRIMARY, platform_adapter_name, platform_name, settings, skip_shell_violations
# 2026-11-13
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
from .storage import create_bytes, data_dir_for, locked, replace_bytes, write_immutable_bytes
# 2026-11-23
# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
# https://github.com/dmitry-ai/harness/issues/146
COMMANDS = ('turn-begin', 'answer-check', 'answer-prepare', 'recover-checkpoint', 'recover-turn-violation', 'similar-project-exempt', 'ratchet-ok', 'tdd-check', 'issue-first-check', 'journal-sync', 'reconcile-unprepared-delivery', 'sync-conversation-title')
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
RULES = {'FILE-3': ('rules/01-file-boundaries.md', 'file-3'), 'EXEC-5': ('rules/08-execution-and-tools.md', 'exec-5'), 'DOC-2': ('rules/04-statement-structure.md', 'doc-2')}
# 2026-10-24
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
RULE_REQUIREMENTS = {'FILE-3': 'Before publication, the primary agent saves the exact request and complete final response via answer-prepare.', 'EXEC-5': 'Run read-only Git checks with `--no-optional-locks` to avoid updating the index as a side effect.', 'DOC-2': 'Frame any unknown or unproven explanation as a hypothesis with arguments for/against and an expert score in %.'}
# 2026-11-13
# "Extract AnswerPreparationRunner class from prepare in completion.py, add typed gate_id readiness tracking, deduplicate native trace loading, and unify resolve_journal_dir":
# https://github.com/dmitry-ai/harness/issues/57
class AnswerPreparationRunner:
	# 2026-11-24
	# "Add blocked-report mode to answer-prepare for pre-finalize workflow blockers":
	# https://github.com/dmitry-ai/harness/issues/213
	def __init__(self, root, response, result, native, turn, *, blocked_report=False):
		# 2026-11-19
		# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
		# https://github.com/dmitry-ai/harness/issues/96
		from .path_registry import project_paths
		self.pp = project_paths(root, exact_root=True)
		self.root, self.response, self.blocked_report = (self.pp.root, response, bool(blocked_report))
		self.sha = _hash(response.encode('utf-8'))
		self.result = result
		self.native = native
		self.turn = turn
		self.path, self.value = _state(self.root, native, turn)
		self.allow_reprepare = False
		self.workflow_path = self.pp.workflow_json
		self.wf_state = None
		self.wf_identifiers = set()
		self.wf_covered = set()
		self.is_finalized = False
		self.has_substantive_hm = False
		self.admission_check = None
	def _audit_workflow_scope(self):
		if self.workflow_path.exists():
			from .workflow import load
			self.wf_state = load(self.root)
			self.wf_identifiers = {req['id'] for req in self.turn['requests']}
			self.wf_covered = {req['id'] for req in self.wf_state['requests']} & self.wf_identifiers
			# 2026-11-03
			# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
			# https://github.com/dmitry-ai/harness/issues/43
			self.is_finalized = 'complete' == self.wf_state.get('stages', {}).get('finalize', {}).get('status')
		# 2026-11-24
		# "Add blocked-report mode to answer-prepare for pre-finalize workflow blockers":
		# https://github.com/dmitry-ai/harness/issues/213
		from .blocked_report import audit_runner_workflow_scope
		audit_runner_workflow_scope(self, factual_kb_fn=_factual_kb_note_issues, is_deliv_fn=_is_client_deliverable_path)
	# 2026-11-14
	# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
	# https://github.com/dmitry-ai/harness/issues/60
	def _authorize_and_sync_workflow(self):
		# 2026-11-24
		# "Add blocked-report mode to answer-prepare for pre-finalize workflow blockers":
		# https://github.com/dmitry-ai/harness/issues/213
		if self.blocked_report:
			from .blocked_report import record_blocked_report_entry
			record_blocked_report_entry(self)
		elif None is self.wf_state or not self.wf_covered:
			self._record_journal_entry()
		# 2026-11-03
		# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
		# https://github.com/dmitry-ai/harness/issues/43
		elif self.is_finalized and (not self.has_substantive_hm):
			self._record_journal_entry()
			from .workflow import update
			def change(s):
				for req in s.get('requests', []):
					if req['id'] in self.wf_identifiers and (not req.get('response_prepared') or self.allow_reprepare):
						req['response_prepared'] = {'sha256': self.sha, 'prepared_at': _now()}
			update(self.root, {'action': 'post_finalize_answer', 'request_ids': sorted(self.wf_identifiers)}, change)
		else:
			from .review import authorize
			try:
				approval = authorize(self.root, self.wf_state, response=self.response, request_ids=self.wf_identifiers)
			except (OSError, ValueError) as exc:
				self._fail_gate('review_authorize', str(exc), cause=exc)
			# 2026-11-25
			# "Ensure atomic answer-prepare workflow alignment and safe open-turn reconciliation":
			# https://github.com/dmitry-ai/harness/issues/232
			from .blocked_report import prepare_and_sync_authorized_workflow
			prepare_and_sync_authorized_workflow(self, approval, _now)
	# 2026-11-21
	# "Add read-only answer-check pre-flight validation command to harness CLI":
	# https://github.com/dmitry-ai/harness/issues/117
	def _check_evicted_citations(self):
		unreread_cited = _find_evicted_cited_files(self.root, self.pp, self.result['turn_key'], self.value['compaction_check'], self.response)
		if unreread_cited:
			detail = 'COMPACT-1 / KB-3 violation in active turn: primary source file(s) read before CHECKPOINT were evicted from context and cited in response without re-reading after checkpoint: ' + ', '.join(unreread_cited)
			self._fail_gate('evicted_citations', detail, extra={'cited_files': unreread_cited})
	def _check_source_grounding(self):
		source_issues = response_source_and_kb_issues(self.root, self.response, self.turn['requests'], touched_files=self.turn.get('touched_files'))
		self.value['source_kb_check'] = {'verified': not source_issues, 'issues': source_issues}
		if source_issues:
			self._fail_gate('source_grounding', '; '.join(source_issues))
	def _check_turn_hygiene(self):
		if not self.value['exec5_check']['verified']:
			commands = [cmd for item in self.value['exec5_check']['violations'] for cmd in item.get('commands', [])]
			self._fail_gate('exec5', 'EXEC-5 violation in active turn (git read command without --no-optional-locks; run recover-turn-violation to record retrospective violation receipt before answer-prepare): ' + '; '.join(commands))
		if not self.value['http_fetch_check']['verified']:
			commands = [cmd for item in self.value['http_fetch_check']['violations'] for cmd in item.get('commands', [])]
			self._fail_gate('http_fetch', 'KB-3 / EXEC-1 violation in active turn (ad-hoc HTTP fetch in shell without persistent Evidence collection; use collect/collect-http or run recover-turn-violation to record retrospective violation receipt before answer-prepare): ' + '; '.join(commands))
		if not self.value['compaction_check']['verified']:
			unreread_src = self.value['compaction_check'].get('unreread_analysis_sources') or []
			if unreread_src:
				detail = 'COMPACT-1 / KB-3 violation in active turn: analysis.md written after CHECKPOINT without re-reading evicted sibling source.md: ' + ', '.join(unreread_src)
			else:
				detail = 'COMPACT-1 / KB-3 violation in active turn: context compaction (CHECKPOINT) occurred after tool calls without post-checkpoint recovery; run recover-checkpoint or inspect transcript_full.jsonl before answer-prepare'
			self._fail_gate('compaction', detail)
		self._check_evicted_citations()
		if not self.value['delegation_check']['verified']:
			dc = self.value['delegation_check']
			detail = f"REVIEW-1 / KB-3 violation in active turn: bulk primary-agent research (tool_steps={dc['tool_step_count']}, max_streak={dc.get('max_unpersisted_step_streak', 0)} > {dc['max_unpersisted_steps']}, or unpersisted_source_reads={dc.get('max_unpersisted_source_reads', 0)} >= {dc.get('max_allowed_unpersisted_source_reads', 10)}) executed without A.F/A.A subagent delegation or incremental \ua616/KB persistence"
			self._fail_gate('delegation', detail)
		# 2026-11-24
		# "Allow blocked-report journaling over hygiene gates with DOC-5 compatibility":
		# https://github.com/dmitry-ai/harness/issues/225
		from .blocked_report import evaluate_runner_code_hygiene
		evaluate_runner_code_hygiene(self, issue_first_fn=_issue_first_status, lifecycle_fn=_code_and_issue_lifecycle_status, tdd_fn=_tdd_status)
		lang_issues = _intermediate_or_language_issues(self.turn['requests'], self.response)
		self.value['language_and_stub_check'] = {'verified': not lang_issues, 'issues': lang_issues}
		if lang_issues:
			self._fail_gate('language_and_stub', '; '.join(lang_issues))
		# 2026-11-23
		# "Prepend JSON metadata headers to new journal responses":
		# https://github.com/dmitry-ai/harness/issues/151
		if self.value['prepared'] and (not _matches_recorded_response(self.value['prepared'], self.response, self.sha)):
			if None is not self.value.get('delivery') or 'delivered' == self.value.get('status') or self.turn.get('completed'):
				raise ValueError('Prepared response bytes are immutable after delivery; preserve the earlier version and reconcile before a corrective turn')
			self.allow_reprepare = True
		if 'conflict' == self.value['status']:
			raise ValueError('Resolve the native delivery conflict without overwriting journal history')
		aa_part_errs = self.value['delegation_check'].get('aa_partial_read_violations') or []
		if aa_part_errs:
			self._fail_gate('aa_partial_read', 'REVIEW-3 / REVIEW-4: Independent A.A reviewer subagent performed a partial/truncated read of the candidate response: ' + '; '.join(aa_part_errs))
	def _fail_gate(self, gate_id, detail, *, admission_failed=False, status=None, extra=None, cause=None):
		if admission_failed:
			self.value['admission_failure'] = {'detail': detail, 'checked_at': _now()}
		if None is not status:
			self.value['status'] = status
		rc = {'verified': False, 'gate_id': gate_id, 'checked_at': _now(), 'detail': detail}
		if extra:
			rc.update(extra)
		self.value['readiness_check'] = rc
		_persist(self.path, self.value)
		if None is cause:
			raise ValueError(detail)
		else:
			raise cause
	def _record_journal_entry(self):
		try:
			self.value['prepared'], self.admission_check = _record(self.root, self.native, self.turn, self.response, self.value['journal'], existing=None if self.allow_reprepare else _recorded(self.value), allow_reprepare=self.allow_reprepare)
		except (OSError, ValueError) as exc:
			self._fail_gate('journal_admission', str(exc), admission_failed=True, cause=exc)
		self.value.pop('admission_failure', None)
	def _verify_delivered_fast_path(self):
		if 'delivered' != self.value['status']:
			r = None
		else:
			recorded = _recorded(self.value)
			# 2026-11-23
			# "Prepend JSON metadata headers to new journal responses":
			# https://github.com/dmitry-ai/harness/issues/151
			if not recorded or (not _matches_recorded_response(recorded, self.response, self.sha)):
				raise ValueError('Delivered response bytes are immutable; preserve the completed turn')
			if not self.turn.get('completed') or self.value['delivery'].get('native_response_sha256') != _hash(self.turn['response'].encode('utf-8')):
				raise ValueError('The saved native delivery requires foreground reconciliation before preparation')
			recorded, admission_check = _record(self.root, self.native, self.turn, self.response, self.value['journal'], existing=recorded, purpose='observation')
			r = {**self.result, **recorded, 'ready': True, 'status': 'delivered', 'delivery_verified': True, 'preparation_verified': self.value['delivery'].get('preparation_verified', False), 'admission_verification': admission_check}
		return r
	def run(self):
		delivered = self._verify_delivered_fast_path()
		if None is not delivered:
			r = delivered
		else:
			self._check_turn_hygiene()
			self._audit_workflow_scope()
			self._check_source_grounding()
			self._authorize_and_sync_workflow()
			try:
				_unchanged(self.root, self.native, self.turn)
			except (OSError, ValueError, sqlite3.Error) as exc:
				self._fail_gate('turn_unchanged', str(exc), status='preparation_unverified', cause=exc)
			self.value['status'] = 'prepared'
			# 2026-11-22
			# "Auto-name Antigravity conversations from project journal step numbers":
			# https://github.com/dmitry-ai/harness/issues/120
			self.value.pop('reserved_journal_steps', None)
			if not self.value.get('readiness_check', {}).get('verified'):
				self.value['readiness_check'] = {'verified': True, 'checked_at': _now()}
			# 2026-11-21
			# "Offload bulky compaction arrays to recovery index and add recover-checkpoint dry-run mode":
			# https://github.com/dmitry-ai/harness/issues/119
			if self.value.get('compaction_check', {}).get('occurred') and (not self.turn.get('completed')):
				idx_rel = _write_compaction_index_file(self.root, self.value['key'], self.turn, self.value['compaction_check'])
				self.value['compaction_check']['index_file'] = idx_rel
			_persist(self.path, self.value)
			# 2026-11-22
			# "Auto-name Antigravity conversations from project journal step numbers":
			# https://github.com/dmitry-ai/harness/issues/120
			title_sync = _sync_antigravity_conversation_title(self.root, self.native, self.value['journal'])
			# 2026-11-21
			# "Offload bulky compaction arrays to recovery index and add recover-checkpoint dry-run mode":
			# https://github.com/dmitry-ai/harness/issues/119
			r = {**self.result, 'compaction_check': _compact_compaction_check(self.value['compaction_check']), **self.value['prepared'], 'ready': True, 'status': 'prepared', 'delivery_verified': False, 'admission_verification': self.admission_check}
			if None is not title_sync:
				r['conversation_title_sync'] = title_sync
		return r
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
class TurnJournalReconciler:
	def __init__(self, root, conversation=None, *, platform=None, backend=None, from_step=0, journal_directory=None, adopt_conflict=False, preloaded_native=None):
		if int is not type(from_step) or 0 > from_step:
			raise ValueError('Native from-step must be a nonnegative integer')
		# 2026-11-19
		# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
		# https://github.com/dmitry-ai/harness/issues/96
		from .path_registry import canonicalize_root_dir
		self.root = canonicalize_root_dir(root)
		self.native = preloaded_native if None is not preloaded_native else _native(self.root, conversation, platform=platform, backend=backend)
		self.from_step = from_step
		self.journal_directory = journal_directory
		self.adopt_conflict = adopt_conflict
	def _build_delivery(self, value, turn, recorded, sha, provenance, preparation_verified):
		delivery = {**recorded, 'verified': True, 'source_file': self.native['source_file'], 'final_step': turn['final_step'], 'completion_step': turn['completion_step'], 'native_response_sha256': sha, 'completion_provenance': provenance, 'preparation_verified': preparation_verified, 'exec5_check': value['exec5_check']}
		previous_delivery = value.get('delivery') or {}
		prior_verified = value.get('prior_verified_delivery') or {}
		if 'delivered' == value['status'] and all((previous_delivery.get(name) == expected for name, expected in delivery.items())):
			r = previous_delivery
		elif prior_verified and all((prior_verified.get(name) == expected for name, expected in delivery.items() if 'verified_at' != name)):
			r = prior_verified
		else:
			delivery['verified_at'] = _now()
			r = delivery
		return r
	def _cleanup_adopted_conflict(self, value):
		value.pop('admission_failure', None)
		# 2026-11-03
		# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
		# https://github.com/dmitry-ai/harness/issues/43
		if (value.get('delivery') or {}).get('conflict_evidence'):
			# 2026-11-19
			# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
			# https://github.com/dmitry-ai/harness/issues/96
			raw_ce = Path(value['delivery']['conflict_evidence'])
			conflict_file = raw_ce if raw_ce.is_absolute() else (self.root / raw_ce)
			if conflict_file.is_file():
				try:
					conflict_file.unlink()
				except OSError:
					pass
	def _reconcile_turn(self, turn):
		path, value = _state(self.root, self.native, turn, recovered=True, allow_extended=True, journal_directory=self.journal_directory)
		# 2026-11-23
		# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
		# https://github.com/dmitry-ai/harness/issues/132
		if 'handed_off' == value.get('status'):
			return {'turn_key': value['key'], 'status': 'handed_off', 'handed_off_to': value.get('handed_off_to'), 'delivery_verified': False, 'journal_steps': [], 'recovered_after_delivery': False}
		response = turn['response']
		sha = _hash(response.encode('utf-8'))
		if value.get('uncovered_requests') and (not self.adopt_conflict):
			r = self._record_conflict(path, value, turn, response, 'Prepared answer does not cover newly received native requests')
		elif not _recorded(value) and (value.get('admission_failure') or False is value.get('readiness_check', {}).get('verified')) and (not self.adopt_conflict):
			r = self._record_conflict(path, value, turn, response, 'A prior preparation/admission gate failed; recovery cannot grant publication approval')
		else:
			conflict_res = None
			# 2026-11-20
			# "Remove retired journal-watch subsystem and prune delivered checkpoint recovery directories":
			# https://github.com/dmitry-ai/harness/issues/105
			try:
				effective_response, conflict_detail = self._resolve_effective_response(value, turn, response, sha)
				if None is not conflict_detail:
					conflict_res = self._record_conflict(path, value, turn, response, conflict_detail)
				else:
					recorded, admission_check = _record(self.root, self.native, turn, effective_response, value['journal'], existing=_recorded(value), purpose='observation')
			except (OSError, ValueError) as exc:
				conflict_res = self._record_conflict(path, value, turn, response, str(exc), retryable=isinstance(exc, OSError) and (not isinstance(exc, FileNotFoundError)))
			if None is not conflict_res:
				r = conflict_res
			elif 'legacy_proof_gap' == admission_check['status'] and value['status'] in ('delivered', 'conflict'):
				r = {'turn_key': value['key'], 'status': value['status'], 'delivery_verified': bool(value.get('delivery', {}).get('verified')), 'journal_steps': recorded['journal_steps'], 'completion_provenance': value.get('delivery', {}).get('completion_provenance'), 'preparation_verified': value.get('delivery', {}).get('preparation_verified', False), 'recovered_after_delivery': value['recovered_after_delivery'], 'exec5_check': value['exec5_check'], 'admission_verification': admission_check}
			else:
				if self.adopt_conflict:
					self._cleanup_adopted_conflict(value)
				if not _recorded(value):
					value['recovered_after_delivery'] = not bool(value['prepared']) and (not recorded['reused_complete_journal_group'])
				if self.adopt_conflict:
					value['recovered_after_delivery'] = True
				# 2026-11-26
				# "Persist emergency journal capture on Stop Gate fail-open and sync idle foreign reservations in turn-begin":
				# https://github.com/dmitry-ai/harness/issues/255
				provenance = resolve_sync_provenance(value, adopt_conflict=self.adopt_conflict)
				preparation_verified = bool(value['prepared']) and value.get('readiness_check', {}).get('verified', True) and (not self.adopt_conflict)
				value['journal_record'] = recorded
				delivery = self._build_delivery(value, turn, recorded, sha, provenance, preparation_verified)
				value.pop('prior_verified_delivery', None)
				# 2026-11-22
				# "Auto-name Antigravity conversations from project journal step numbers":
				# https://github.com/dmitry-ai/harness/issues/120
				value.pop('reserved_journal_steps', None)
				value['delivery'] = delivery
				value['status'] = 'delivered'
				if self.adopt_conflict:
					value['readiness_check'] = {'verified': True, 'checked_at': _now(), 'detail': 'Adopted into journal via --adopt-conflict'}
				_persist(path, value)
				# 2026-11-22
				# "Auto-name Antigravity conversations from project journal step numbers":
				# https://github.com/dmitry-ai/harness/issues/120
				journal.release_turn_steps(_directory(self.root, value['journal']), value['key'], request_ids=[req['id'] for req in turn['requests']])
				# 2026-11-20
				# "Remove retired journal-watch subsystem and prune delivered checkpoint recovery directories":
				# https://github.com/dmitry-ai/harness/issues/105
				self._prune_delivered_checkpoint_recovery(value['key'])
				r = {'turn_key': value['key'], 'status': 'delivered', 'delivery_verified': True, 'journal_steps': recorded['journal_steps'], 'completion_provenance': provenance, 'preparation_verified': preparation_verified, 'recovered_after_delivery': value['recovered_after_delivery'], 'exec5_check': value['exec5_check'], 'admission_verification': admission_check}
		return r
	# 2026-11-20
	# "Remove retired journal-watch subsystem and prune delivered checkpoint recovery directories":
	# https://github.com/dmitry-ai/harness/issues/105
	def _prune_delivered_checkpoint_recovery(self, key: str) -> None:
		import shutil
		folder = _folder(self.root)
		rec_dir = folder / f'{key}-recovery'
		if rec_dir.is_dir() and (not os.path.islink(rec_dir)):
			shutil.rmtree(rec_dir, ignore_errors=True)
		rec_file = folder / f'{key}-checkpoint-recovery.json'
		if rec_file.is_file() and (not os.path.islink(rec_file)):
			try:
				rec_file.unlink()
			except OSError:
				pass
	def _record_conflict(self, path, value, turn, response, detail, *, retryable=False):
		return _conflict(self.root, path, value, self.native, turn, response, detail, retryable=retryable)
	def _resolve_effective_response(self, value, turn, response, sha):
		effective_response, conflict_detail = (response, None)
		if not value['prepared']:
			matched = journal.matching_group_response(_directory(self.root, value['journal']), [req['id'] for req in turn['requests']], response)
			if None is not matched:
				effective_response = matched
		elif value['prepared']['response_sha256'] != sha:
			# 2026-11-21
			# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
			# https://github.com/dmitry-ai/harness/issues/113
			raw_prep = value['prepared'].get('response_file') or ''
			prep_file = journal.resolve_migrated_step_file(raw_prep) if raw_prep else Path()
			prep_text = prep_file.read_bytes().decode('utf-8') if prep_file.is_file() else ''
			# 2026-11-23
			# "Prepend JSON metadata headers to new journal responses":
			# https://github.com/dmitry-ai/harness/issues/151
			if prep_text and _norm_journal_response_text(prep_text) == _norm_journal_response_text(response):
				effective_response = prep_text
			elif not self.adopt_conflict:
				conflict_detail = 'Prepared and delivered response bytes differ'
		return (effective_response, conflict_detail)
	def run(self):
		if not self.native['primary']:
			raise ValueError('A child executor has no primary user journal to synchronize')
		if not any((turn['owned'] for turn in self.native['turns'])):
			raise ValueError('Native conversation has no user turns owned by this project')
		# 2026-11-21
		# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
		# https://github.com/dmitry-ai/harness/issues/109
		journal.ensure_project_journal_upgraded(self.root, selected=self.journal_directory)
		eligible = [turn for turn in self.native['turns'] if turn['owned'] and turn['completed'] and (not turn['aborted']) and (turn['start_step'] >= self.from_step)]
		if not eligible:
			r = {'valid': True, 'conversation_id': self.native['conversation_id'], 'source_file': self.native['source_file'], 'turns': [], 'pending_native_turn': self.native['active_turn_id'], 'private_reasoning_retained': False}
		else:
			results = []
			with locked(_journal_lock(self.root)):
				for turn in eligible:
					with locked(_turn_lock(self.root, _key(self.native, turn))):
						results.append(self._reconcile_turn(turn))
			# 2026-11-22
			# "Auto-name Antigravity conversations from project journal step numbers":
			# https://github.com/dmitry-ai/harness/issues/120
			if any(('delivered' == item.get('status') for item in results)):
				j_hint = self.journal_directory
				if None is j_hint:
					for item in reversed(results):
						st_p = _folder(self.root) / (item['turn_key'] + '.json')
						if st_p.is_file():
							try:
								j_hint = _read(st_p).get('journal')
								if j_hint:
									break
							except (OSError, ValueError):
								pass
				_sync_antigravity_conversation_title(self.root, self.native, j_hint)
			r = {'valid': not any(('conflict' == item['status'] for item in results)), 'conversation_id': self.native['conversation_id'], 'source_file': self.native['source_file'], 'turns': results, 'retryable': any((item.get('retryable') for item in results)), 'pending_native_turn': self.native['active_turn_id'], 'private_reasoning_retained': False}
		return r
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def _now():
	return datetime.now(timezone.utc).isoformat()
def _hash(value):
	return hashlib.sha256(value).hexdigest()
def _json(value):
	return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
def _read(path):
	value = json.loads(path.read_bytes().decode('utf-8'))
	if not isinstance(value, dict):
		raise ValueError('Completion metadata must be a JSON object: ' + str(path))
	# 2026-11-24
	# "Add deterministic reactive wait primitive for transient repository and journal contention":
	# https://github.com/dmitry-ai/harness/issues/199
	return value
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
def _folder(root):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	# 2026-11-25
	# "Add workspace-local shadow-replay CLI command and EXEC-2 acceptance gate":
	# https://github.com/dmitry-ai/harness/issues/237
	return pp.turns_dir if pp.has_explicit_path('turns_dir') else (pp.data_dir / 'turns')
# 2026-11-10
# "Isolate turn scratch answer files, allow pre-delivery response re-preparation, and enforce preemptive step/compaction budget stop":
# https://github.com/dmitry-ai/harness/issues/49
def _turn_lock(root, key):
	return _folder(root) / f'turn-{key}.lock'
# 2026-11-10
# "Isolate turn scratch answer files, allow pre-delivery response re-preparation, and enforce preemptive step/compaction budget stop":
# https://github.com/dmitry-ai/harness/issues/49
def _journal_lock(root):
	return _folder(root) / 'journal.lock'
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-11-13
# "Extract AnswerPreparationRunner class from prepare in completion.py, add typed gate_id readiness tracking, deduplicate native trace loading, and unify resolve_journal_dir":
# https://github.com/dmitry-ai/harness/issues/57
def _directory(root, selected=None):
	return journal.resolve_journal_dir(root, selected)
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def _key(native, turn):
	identity = [native['platform'], native['native_backend'], native['conversation_id'], turn['turn_id']]
	# 2026-11-24
	# "Add deterministic reactive wait primitive for transient repository and journal contention":
	# https://github.com/dmitry-ai/harness/issues/199
	return _hash(_json(identity))[:40]
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def _native(root, conversation=None, *, platform=None, backend=None):
	platform = platform_name(platform)
	conversation = conversation or (os.environ.get('CODEX_THREAD_ID') if 'codex' == platform else None)
	if not conversation:
		raise ValueError('Select the actual current native conversation; no summary or neighbouring chat fallback')
	# 2026-11-24
	# "Add deterministic reactive wait primitive for transient repository and journal contention":
	# https://github.com/dmitry-ai/harness/issues/199
	return adapter(platform).native_answers(Path(root).resolve(), conversation, backend=backend)
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-24
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def _policy():
	return {ident: {'source': relative, 'anchor': anchor, 'sha256': _hash((PRIMARY / relative).read_bytes()), 'requirement': RULE_REQUIREMENTS[ident]} for ident, (relative, anchor) in RULES.items()}
# 2026-11-02
# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
# https://github.com/dmitry-ai/harness/issues/36
def _violation_recovery(root, key):
	if None is root or not key:
		return {}
	path = _folder(root) / f'{key}-violation-recovery.json'
	if not path.is_file():
		return {}
	try:
		return _read(path)
	except (OSError, ValueError):
		return {}
# 2026-10-24
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
# 2026-11-02
# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
# https://github.com/dmitry-ai/harness/issues/36
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
def _exec5_status(turn, root=None, key=None):
	return _recoverable_step_status(turn, 'exec5_violations', 'covered_exec5_steps', root, key)
# 2026-11-13
# "Extract AnswerPreparationRunner class from prepare in completion.py, add typed gate_id readiness tracking, deduplicate native trace loading, and unify resolve_journal_dir":
# https://github.com/dmitry-ai/harness/issues/57
def _factual_kb_note_issues(root, turn):
	from .knowledge import validate_kb_factual_note
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	kb_prefix = pp.kb_dir.as_posix().lower().rstrip('/') + '/'
	ev_prefix = pp.evidence_dir.as_posix().lower().rstrip('/') + '/'
	r = {'has_normative': False, 'has_analysis': False, 'issues': []}
	for tf in turn.get('touched_files') or []:
		tf_norm = str(tf).replace('\\', '/').lower()
		fpath = Path(tf) if Path(tf).is_absolute() else (pp.root / Path(tf))
		fpath_low = fpath.as_posix().lower()
		in_kb = '/\ua616/kb/' in tf_norm or tf_norm.endswith('/kb/analysis.md') or tf_norm.endswith('/kb/analysis.json') or fpath_low.startswith(kb_prefix)
		in_ev = '/\ua616/kb/evidence/' in tf_norm or fpath_low.startswith(ev_prefix)
		if in_kb and (not in_ev):
			basename = Path(tf).name.lower()
			if basename in ('analysis.md', 'analysis.json'):
				r['has_analysis'] = True
				r['has_normative'] = True
			elif basename in ('project.md', 'projects.md'):
				r['has_normative'] = True
			elif fpath.is_file():
				try:
					note_text = fpath.read_text(encoding='utf-8', errors='replace')
					r['issues'].extend(validate_kb_factual_note(fpath, note_text))
				except OSError:
					pass
	return r
# 2026-11-23
# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
# https://github.com/dmitry-ai/harness/issues/146
def _issue_first_status(root, turn):
	from .issue_first_gate import evaluate_issue_first_events
	return evaluate_issue_first_events(list(turn.get('issue_first_events') or []), requests=list(turn.get('requests') or []), project_root=root)
# 2026-11-23
# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
# https://github.com/dmitry-ai/harness/issues/138
def _tdd_status(root, turn):
	from .tdd_gate import evaluate_tdd_events
	# 2026-11-25
	# "Add comment-only diff lexer exemption for top 20 repository languages":
	# https://github.com/dmitry-ai/harness/issues/238
	return evaluate_tdd_events(list(turn.get('tdd_events') or []), require_final_full_green=True, project_root=root)
# 2026-11-25
# "Add PreToolUse canary probe to runtime snapshot validation and turn hook-crash audit":
# https://github.com/dmitry-ai/harness/issues/251
def _hook_crash_status(root, native, turn, value, response):
	from .hook_crash_audit import evaluate_hook_crash_check
	return evaluate_hook_crash_check(root, native, turn, value, response)
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
# 2026-11-25
# "Add PreToolUse canary probe to runtime snapshot validation and turn hook-crash audit":
# https://github.com/dmitry-ai/harness/issues/251
VERIFIED_CHECK_KEYS = ('exec5_check', 'hook_crash_check', 'http_fetch_check', 'compaction_check', 'delegation_check', 'issue_first_check', 'code_lifecycle_check', 'tdd_check', 'language_and_stub_check', 'source_kb_check')
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
GATE_SPECS = (
	('exec5', ('EXEC-5 violation in active turn (git read',), lambda root_p, turn, value, rc: bool(value.get('exec5_check', {}).get('verified'))),
	# 2026-11-25
	# "Add PreToolUse canary probe to runtime snapshot validation and turn hook-crash audit":
	# https://github.com/dmitry-ai/harness/issues/251
	('hook_crash', ('DOC-5 / EXEC-5 hook_crash_check',), lambda root_p, turn, value, rc: bool(value.get('hook_crash_check', {}).get('verified', True))),
	('http_fetch', ('KB-3 / EXEC-1 violation',), lambda root_p, turn, value, rc: bool(value.get('http_fetch_check', {}).get('verified'))),
	('compaction', (), lambda root_p, turn, value, rc: bool(value.get('compaction_check', {}).get('verified'))),
	('evicted_citations', (), lambda root_p, turn, value, rc: bool(value.get('compaction_check', {}).get('verified')) and (not ((set(rc.get('cited_files') or ()) & set(value.get('compaction_check', {}).get('evicted_unreread_files') or ())) if rc.get('cited_files') else set(value.get('compaction_check', {}).get('evicted_unreread_files') or ())))),
	('delegation', ('REVIEW-1 / KB-3 violation',), lambda root_p, turn, value, rc: bool(value.get('delegation_check', {}).get('verified'))),
	# 2026-11-23
	# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
	# https://github.com/dmitry-ai/harness/issues/146
	('issue_first', ('EXEC-5 ISSUE-FIRST-GATE',), lambda root_p, turn, value, rc: bool(value.get('issue_first_check', {}).get('verified'))),
	# 2026-10-31
	# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
	# https://github.com/dmitry-ai/harness/issues/31
	('code_lifecycle', ('EXEC-5 violation in active turn (code/issue',), lambda root_p, turn, value, rc: bool(value.get('code_lifecycle_check', {}).get('verified'))),
	# 2026-11-23
	# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
	# https://github.com/dmitry-ai/harness/issues/138
	('tdd', ('EXEC-2 TDD-',), lambda root_p, turn, value, rc: bool(value.get('tdd_check', {}).get('verified'))),
	('language_and_stub', ('TEXT-1:', 'FILE-3 / REVIEW-1:'), lambda root_p, turn, value, rc: bool(value.get('language_and_stub_check', {}).get('verified'))),
	('aa_partial_read', ('REVIEW-3 / REVIEW-4: Independent A.A reviewer',), lambda root_p, turn, value, rc: not bool(value.get('delegation_check', {}).get('aa_partial_read_violations'))),
	('factual_kb_note', ('KB-2 / DOC-1 violation',), lambda root_p, turn, value, rc: not bool(_factual_kb_note_issues(root_p, turn)['issues'])),
	('workflow_adoption', ('REVIEW-3 / REVIEW-4: Adopt current requests',), lambda root_p, turn, value, rc: _workflow_gate_resolved(root_p, turn, 'workflow_adoption')),
	('review_authorize', (), lambda root_p, turn, value, rc: _workflow_gate_resolved(root_p, turn, 'review_authorize')),
	('source_grounding', ('VERIFY-1', 'LINK-', 'KB-1 / KB-3:', 'DOC-1 / VERIFY-'), lambda root_p, turn, value, rc: bool(value.get('source_kb_check', {}).get('verified'))),
)
# 2026-11-13
# "Extract AnswerPreparationRunner class from prepare in completion.py, add typed gate_id readiness tracking, deduplicate native trace loading, and unify resolve_journal_dir":
# https://github.com/dmitry-ai/harness/issues/57
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
def _gate_resolved(root, turn, value):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import canonicalize_root_dir
	rc = value.get('readiness_check') or {}
	gid = str(rc.get('gate_id') or '')
	rc_detail = str(rc.get('detail') or '')
	if '' == gid and rc_detail.startswith('COMPACT-1 / KB-3 violation'):
		gid = 'evicted_citations' if 'cited in response' in rc_detail else 'compaction'
	root_p = canonicalize_root_dir(root)
	specific = next((pred(root_p, turn, value, rc) for spec_id, prefixes, pred in GATE_SPECS if spec_id == gid or ('' == gid and prefixes and rc_detail.startswith(prefixes))), False)
	return bool(specific and all((value.get(k, {}).get('verified', True) for k in VERIFIED_CHECK_KEYS)))
# 2026-11-02
# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
# https://github.com/dmitry-ai/harness/issues/36
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
def _http_fetch_status(turn, root=None, key=None):
	return _recoverable_step_status(turn, 'http_fetch_violations', 'covered_http_fetch_steps', root, key)
# 2026-10-30
# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
# https://github.com/dmitry-ai/harness/issues/21
def _compaction_status(root, key, turn):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	ev_prefix = pp.evidence_dir.as_posix().lower().rstrip('/') + '/'
	comp = dict(turn.get('compaction') or {})
	occurred = bool(comp.get('occurred'))
	last_cp = comp.get('last_checkpoint_step')
	pre_steps = list(comp.get('pre_checkpoint_tool_steps') or [])
	post_rec = list(comp.get('post_checkpoint_recovery_steps') or [])
	# 2026-11-01
	# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
	# https://github.com/dmitry-ai/harness/issues/34
	pre_reads = list(comp.get('pre_checkpoint_read_files') or [])
	post_reads = list(comp.get('post_checkpoint_read_files') or [])
	post_writes = list(comp.get('post_checkpoint_written_files') or [])
	evicted_unreread = list(comp.get('evicted_unreread_files') or [])
	evicted_lower = {p.replace('\\', '/').lower(): p for p in evicted_unreread}
	unreread_analysis_sources = []
	# 2026-11-10
	# "Enforce source grounding and review.authorize across external client deliverables, edit_file calls, and post-compaction tool outputs":
	# https://github.com/dmitry-ai/harness/issues/50
	writes_client_deliverable = False
	for w in post_writes:
		wnorm = w.replace('\\', '/')
		wlow = wnorm.lower()
		if wlow.endswith('/kb/analysis.md'):
			sib = (Path(wnorm).parent / 'source.md').as_posix()
			if sib.lower() in evicted_lower and evicted_lower[sib.lower()] not in unreread_analysis_sources:
				unreread_analysis_sources.append(evicted_lower[sib.lower()])
		elif _is_client_deliverable_path(wlow, root):
			writes_client_deliverable = True
	# 2026-11-10
	# "Enforce source grounding and review.authorize across external client deliverables, edit_file calls, and post-compaction tool outputs":
	# https://github.com/dmitry-ai/harness/issues/50
	if writes_client_deliverable:
		for ev_l, ev_orig in evicted_lower.items():
			if ('/.system_generated/steps/' in ev_l or ev_l.endswith('/kb/source.md') or '/source/' in ev_l or '/\ua616/kb/evidence/' in ev_l or ev_l.startswith(ev_prefix)) and ev_orig not in unreread_analysis_sources:
				unreread_analysis_sources.append(ev_orig)
	recovered_in_trace = bool(comp.get('recovered_in_trace', True))
	receipt_path = _folder(root) / f'{key}-checkpoint-recovery.json'
	recovered_via_receipt = False
	if receipt_path.is_file():
		try:
			rec_data = _read(receipt_path)
			cov = rec_data.get('covered_checkpoint_step')
			if None is last_cp or (isinstance(cov, int) and cov >= last_cp):
				recovered_via_receipt = True
		except (OSError, ValueError):
			pass
	verified = bool((not occurred or not pre_steps or recovered_in_trace or recovered_via_receipt) and (not unreread_analysis_sources))
	# 2026-11-21
	# "Offload bulky compaction arrays to recovery index and add recover-checkpoint dry-run mode":
	# https://github.com/dmitry-ai/harness/issues/119
	idx_path = (_folder(root) / f'{key}-recovery/index.json') if key else None
	idx_rel = (idx_path.relative_to(root).as_posix() if idx_path.is_relative_to(root) else str(idx_path)) if None is not idx_path and occurred and idx_path.is_file() else None
	r = {'verified': verified, 'occurred': occurred, 'checkpoint_steps': list(comp.get('checkpoint_steps') or []), 'last_checkpoint_step': last_cp, 'pre_checkpoint_tool_steps': pre_steps, 'post_checkpoint_recovery_steps': post_rec, 'recovered_in_trace': recovered_in_trace, 'recovered_via_receipt': recovered_via_receipt, 'pre_checkpoint_read_files': pre_reads, 'post_checkpoint_read_files': post_reads, 'post_checkpoint_written_files': post_writes, 'evicted_unreread_files': evicted_unreread, 'unreread_analysis_sources': unreread_analysis_sources, 'index_file': idx_rel}
	return r
# 2026-11-21
# "Offload bulky compaction arrays to recovery index and add recover-checkpoint dry-run mode":
# https://github.com/dmitry-ai/harness/issues/119
def _build_compaction_file_index(root: Path, pre_reads: list[str], post_reads: list[str], evicted_unreread: list[str]) -> list[dict]:
	ev_set = {str(p).replace('\\', '/').lower() for p in (evicted_unreread or ())}
	post_set = {str(p).replace('\\', '/').lower() for p in (post_reads or ())}
	seen: set[str] = set()
	ordered: list[str] = []
	for p in [*(pre_reads or ()), *(evicted_unreread or ())]:
		ps = str(p or '').strip()
		pk = ps.replace('\\', '/').lower()
		if ps and pk not in seen:
			seen.add(pk)
			ordered.append(ps)
	items: list[dict] = []
	for raw_p in ordered:
		pk = raw_p.replace('\\', '/').lower()
		p_obj = Path(raw_p)
		if not p_obj.is_absolute():
			p_obj = (root / p_obj).resolve()
		exists = False
		sha = None
		byte_len = None
		line_cnt = None
		try:
			if p_obj.is_file():
				exists = True
				st = p_obj.stat()
				byte_len = st.st_size
				if byte_len <= 16 * 1024 * 1024:
					raw_b = p_obj.read_bytes()
					sha = _hash(raw_b)
					line_cnt = max(1, raw_b.count(b'\n') + (0 if raw_b.endswith(b'\n') or (not raw_b) else 1))
		except OSError:
			pass
		is_ev = pk in ev_set
		reread_req = bool(is_ev and (pk.endswith('/kb/source.md') or '/source/' in pk or '/res/' in pk or '/\u227a/' in pk or '/kb/' in pk))
		rel_p = p_obj.relative_to(root).as_posix() if p_obj.is_relative_to(root) else p_obj.as_posix()
		items.append({'path': rel_p, 'exists': exists, 'sha256': sha, 'bytes': byte_len, 'lines': line_cnt, 'evicted_unreread': is_ev, 'reread_after_checkpoint': pk in post_set, 'reread_required_if_cited': reread_req})
	return items
# 2026-11-21
# "Offload bulky compaction arrays to recovery index and add recover-checkpoint dry-run mode":
# https://github.com/dmitry-ai/harness/issues/119
def _write_compaction_index_file(root: Path, key: str, turn: dict, comp_check: dict, *, step_records: list[dict] | None = None) -> str:
	rec_dir = _folder(root) / f'{key}-recovery'
	rec_dir.mkdir(parents=True, exist_ok=True)
	idx_path = rec_dir / 'index.json'
	pre_reads = list(comp_check.get('pre_checkpoint_read_files') or [])
	post_reads = list(comp_check.get('post_checkpoint_read_files') or [])
	evicted = list(comp_check.get('evicted_unreread_files') or [])
	if None is not step_records:
		raw_recs = step_records
	else:
		raw_recs = []
		for rec in ((turn.get('compaction') or {}).get('pre_checkpoint_records')) or []:
			st = rec.get('step')
			outs = list(rec.get('outputs') or [])
			step_file = rec_dir / f'step-{st}.txt'
			if step_file.is_file():
				rel_step = step_file.relative_to(root).as_posix() if step_file.is_relative_to(root) else str(step_file)
				raw_recs.append({'step': st, 'tools': list(rec.get('tools') or []), 'output_file': rel_step, 'output_preview': [o[:200] for o in outs[:2]]})
			else:
				raw_recs.append(rec)
	payload = {
		'schema_version': 1,
		'turn_key': key,
		'updated_at': _now(),
		'covered_checkpoint_step': comp_check.get('last_checkpoint_step'),
		'checkpoint_steps': list(comp_check.get('checkpoint_steps') or []),
		'pre_checkpoint_tool_steps': list(comp_check.get('pre_checkpoint_tool_steps') or []),
		'post_checkpoint_recovery_steps': list(comp_check.get('post_checkpoint_recovery_steps') or []),
		'pre_checkpoint_read_files': pre_reads,
		'post_checkpoint_read_files': post_reads,
		'post_checkpoint_written_files': list(comp_check.get('post_checkpoint_written_files') or []),
		'evicted_unreread_files': evicted,
		'unreread_analysis_sources': list(comp_check.get('unreread_analysis_sources') or []),
		'file_index': _build_compaction_file_index(root, pre_reads, post_reads, evicted),
		'pre_checkpoint_records': raw_recs,
	}
	replace_bytes(idx_path, _json(payload))
	return idx_path.relative_to(root).as_posix() if idx_path.is_relative_to(root) else str(idx_path)
# 2026-11-21
# "Offload bulky compaction arrays to recovery index and add recover-checkpoint dry-run mode":
# https://github.com/dmitry-ai/harness/issues/119
def _compact_compaction_check(comp_check: dict, *, index_file: str | None = None) -> dict:
	occurred = bool(comp_check.get('occurred'))
	eff_idx = (index_file if None is not index_file else comp_check.get('index_file')) if occurred else None
	return {
		'verified': bool(comp_check.get('verified')),
		'occurred': occurred,
		'checkpoint_steps': list(comp_check.get('checkpoint_steps') or []),
		'last_checkpoint_step': comp_check.get('last_checkpoint_step'),
		'recovered_in_trace': bool(comp_check.get('recovered_in_trace')),
		'recovered_via_receipt': bool(comp_check.get('recovered_via_receipt')),
		'pre_checkpoint_tool_step_count': len(comp_check.get('pre_checkpoint_tool_steps') or []),
		'pre_checkpoint_read_count': len(comp_check.get('pre_checkpoint_read_files') or []),
		'post_checkpoint_read_count': len(comp_check.get('post_checkpoint_read_files') or []),
		'post_checkpoint_write_count': len(comp_check.get('post_checkpoint_written_files') or []),
		'evicted_unreread_count': len(comp_check.get('evicted_unreread_files') or []),
		'index_file': eff_idx,
		'unreread_analysis_sources': list(comp_check.get('unreread_analysis_sources') or []),
	}
# 2026-10-30
# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
# https://github.com/dmitry-ai/harness/issues/21
DEL_MAX_UNPERSISTED_STEPS = 40
# 2026-11-01
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
DEL_MAX_UNPERSISTED_SOURCE_READS = 10
# 2026-11-02
# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
# https://github.com/dmitry-ai/harness/issues/37
DEL_MAX_TOTAL_STEPS_WITHOUT_SUBAGENTS = 60
DEL_MAX_ISSUE_ACTIONS_WITHOUT_SUBAGENTS = 3
# 2026-10-30
# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
# https://github.com/dmitry-ai/harness/issues/21
def _delegation_status(root, turn):
	del_info = dict(turn.get('delegation') or {})
	tool_steps = int(del_info.get('tool_step_count') or 0)
	sub_steps = int(del_info.get('subagent_step_count') or 0)
	# 2026-11-01
	# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
	# https://github.com/dmitry-ai/harness/issues/34
	aa_steps = int(del_info.get('aa_subagent_step_count') if 'aa_subagent_step_count' in del_info else sub_steps)
	af_steps = int(del_info.get('af_subagent_step_count') or 0)
	kb_steps = int(del_info.get('kb_persistence_step_count') or 0)
	cur_streak = int(del_info.get('unpersisted_step_streak') if 'unpersisted_step_streak' in del_info else tool_steps if 0 == sub_steps and 0 == kb_steps else 0)
	max_streak = int(del_info.get('max_unpersisted_step_streak') if 'max_unpersisted_step_streak' in del_info else cur_streak)
	max_src_reads = int(del_info.get('max_unpersisted_source_reads') or 0)
	# 2026-11-02
	# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
	# https://github.com/dmitry-ai/harness/issues/37
	issue_actions_count = len(turn.get('issue_actions') or [])
	# 2026-11-06
	# "Enforce defect-to-issue filing gate in code repository audits, open-issue lifecycle separation, and recursive subagent trace aggregation":
	# https://github.com/dmitry-ai/harness/issues/48
	aa_part_errs = list(del_info.get('aa_partial_read_violations') or [])
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	is_upwork_project = project_paths(root, exact_root=True).project_json.is_file()
	# 2026-11-02
	# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
	# https://github.com/dmitry-ai/harness/issues/37
	unpersisted_bulk = bool(is_upwork_project and ((tool_steps > DEL_MAX_UNPERSISTED_STEPS and 0 == sub_steps and 0 == kb_steps) or cur_streak > DEL_MAX_UNPERSISTED_STEPS or (max_src_reads >= DEL_MAX_UNPERSISTED_SOURCE_READS and 0 == sub_steps) or (tool_steps > DEL_MAX_TOTAL_STEPS_WITHOUT_SUBAGENTS and 0 == sub_steps) or (issue_actions_count > DEL_MAX_ISSUE_ACTIONS_WITHOUT_SUBAGENTS and 0 == sub_steps)))
	# 2026-11-06
	# "Enforce defect-to-issue filing gate in code repository audits, open-issue lifecycle separation, and recursive subagent trace aggregation":
	# https://github.com/dmitry-ai/harness/issues/48
	r = {'verified': not unpersisted_bulk, 'tool_step_count': tool_steps, 'subagent_step_count': sub_steps, 'aa_subagent_step_count': aa_steps, 'aa_partial_read_violations': aa_part_errs, 'af_subagent_step_count': af_steps, 'kb_persistence_step_count': kb_steps, 'issue_actions_count': issue_actions_count, 'max_unpersisted_steps': DEL_MAX_UNPERSISTED_STEPS, 'unpersisted_step_streak': cur_streak, 'max_unpersisted_step_streak': max_streak, 'max_unpersisted_source_reads': max_src_reads, 'max_allowed_unpersisted_source_reads': DEL_MAX_UNPERSISTED_SOURCE_READS}
	return r
# 2026-11-10
# "Isolate turn scratch answer files, allow pre-delivery response re-preparation, and enforce preemptive step/compaction budget stop":
# https://github.com/dmitry-ai/harness/issues/49
BUDGET_MAX_CHECKPOINTS = 2
BUDGET_MAX_TOOL_STEPS = 120
BUDGET_WINDOW_5H_MAX_STEPS = 400
# 2026-11-10
# "Isolate turn scratch answer files, allow pre-delivery response re-preparation, and enforce preemptive step/compaction budget stop":
# https://github.com/dmitry-ai/harness/issues/49
def _budget_status(root, turn):
	comp = dict(turn.get('compaction') or {})
	del_info = dict(turn.get('delegation') or {})
	cp_count = len(comp.get('checkpoint_steps') or [])
	tool_steps = int(del_info.get('tool_step_count') or 0)
	now_ts = datetime.now(timezone.utc).timestamp()
	window_5h_steps = tool_steps
	turns_dir = _folder(root)
	cur_tid = turn.get('turn_id')
	if turns_dir.is_dir():
		for tf in turns_dir.glob('*.json'):
			if '-' in tf.stem:
				continue
			try:
				if now_ts - tf.stat().st_mtime <= 18000:
					td = _read(tf)
					if td.get('native_turn_id') != cur_tid:
						window_5h_steps += int((td.get('delegation_check') or {}).get('tool_step_count') or 0)
			except (OSError, ValueError):
				pass
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	cont_low = pp.continuation_md.as_posix().lower()
	kb_prefix = pp.kb_dir.as_posix().lower().rstrip('/') + '/'
	touched = [str(x).replace('\\', '/').lower() for x in (turn.get('touched_files') or [])]
	continuation_saved = any((x.endswith('/data/continuation.md') or x.endswith('\ua616/data/continuation.md') or x == cont_low for x in touched))
	kb_saved = any(('/\ua616/kb/' in x or x.endswith('/kb/analysis.md') or x.endswith('/kb/analysis.json') or x.startswith(kb_prefix) for x in touched))
	exceeded = bool(cp_count >= BUDGET_MAX_CHECKPOINTS or tool_steps >= BUDGET_MAX_TOOL_STEPS or window_5h_steps >= BUDGET_WINDOW_5H_MAX_STEPS)
	r = {'verified': True, 'checkpoint_count': cp_count, 'max_checkpoints': BUDGET_MAX_CHECKPOINTS, 'tool_step_count': tool_steps, 'max_tool_steps': BUDGET_MAX_TOOL_STEPS, 'window_5h_tool_steps': window_5h_steps, 'max_window_5h_tool_steps': BUDGET_WINDOW_5H_MAX_STEPS, 'graceful_checkpoint_required': exceeded, 'continuation_saved': continuation_saved, 'kb_saved': kb_saved}
	return r
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def _instruction_snapshot(root, native, *, stage):
	from .configuration import _project_rule_paths
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	root = pp.root
	# 2026-11-18
	# "Fix runtime instance path derivation and store validation":
	# https://github.com/dmitry-ai/harness/issues/89
	plat_id = native['platform']
	plat_cfg = (settings().get('platforms') or {}).get(plat_id)
	adapter_kind = platform_adapter_name(plat_id, plat_cfg)
	sources = {path: 'canonical' for path in sorted((PRIMARY / 'rules').glob('*.md'))}
	sources[PRIMARY / 'runtime.json'] = 'runtime'
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	if (PRIMARY / 'paths.json').is_file():
		sources[PRIMARY / 'paths.json'] = 'paths-registry'
	if None is not pp.overlay_file and pp.overlay_file.is_file():
		sources[pp.overlay_file] = 'project-paths-overlay'
	# 2026-11-18
	# "Fix runtime instance path derivation and store validation":
	# https://github.com/dmitry-ai/harness/issues/89
	adapter_doc = PRIMARY / 'platforms' / (adapter_kind + '.md')
	if adapter_doc.is_file():
		sources[adapter_doc] = 'adapter'
	errors = []
	agents_dir = pp.agents_config_dir if pp.agents_config_dir.resolve() != Path(PRIMARY).resolve() else (root / '.agents')
	manifest = agents_dir / 'rules.json'
	if manifest.exists():
		sources[manifest] = 'project-registration'
	try:
		sources.update({path: 'project-rule' for path in _project_rule_paths(root, PRIMARY)})
	except (OSError, ValueError) as exc:
		errors.append(str(exc))
	# 2026-11-18
	# "Fix runtime instance path derivation and store validation":
	# https://github.com/dmitry-ai/harness/issues/89
	if 'codex' == adapter_kind:
		workspace = Path(settings()['workspace_root']).resolve()
		folders = [root]
		if root.is_relative_to(workspace):
			folders += [parent for parent in root.parents if parent == workspace or parent.is_relative_to(workspace)]
		if native.get('native_backend'):
			folders.append(Path(native['native_backend']))
		for folder in folders:
			for name in ('AGENTS.md', 'AGENTS.override.md'):
				path = folder / name
				if path.is_file():
					sources[path] = 'native-guidance-candidate'
	files = []
	for path, kind in sorted(sources.items(), key=lambda item: str(item[0])):
		try:
			files.append({'path': str(path.resolve()), 'kind': kind, 'sha256': _hash(path.read_bytes())})
		except OSError as exc:
			errors.append(str(exc))
	r = {'captured_at': _now(), 'capture_stage': stage, 'sources': files, 'errors': errors, 'selection_verified': False, 'delivery_to_model_verified': False}
	return r
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
def _is_client_deliverable_path(path_text, root=None) -> bool:
	norm = str(path_text).replace('\\', '/').lower()
	if '/\ua616/' in norm or '/\ua66e/' in norm:
		return False
	segs = ('/letters/', '/result/', '/defects/')
	if None is not root:
		from .path_registry import project_paths
		pp = project_paths(root, exact_root=True)
		ag_pref = pp.agent_dir.as_posix().lower().rstrip('/') + '/'
		jr_pref = pp.journal_root_dir.as_posix().lower().rstrip('/') + '/'
		if norm.startswith(ag_pref) or norm.startswith(jr_pref):
			return False
		segs = tuple({*segs, *(s.lower() for s in pp.deliverable_segments)})
		for slot in ('letters_dir', 'proposals_dir', 'articles_dir'):
			sp = pp.path(slot)
			if None is not sp and norm.startswith(sp.as_posix().lower().rstrip('/') + '/'):
				return True
	return any((seg in norm for seg in segs))
# 2026-11-22
# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
# https://github.com/dmitry-ai/harness/issues/123
def _similar_projects_metadata(root: Path) -> tuple[list[str], list[str]]:
	from .issue_lifecycle import similar_project_repo_slugs
	from .path_registry import canonicalize_root_dir, load_registry, project_paths
	reg = load_registry()
	canon_root = canonicalize_root_dir(root, registry=reg)
	pp = project_paths(canon_root, registry=reg, exact_root=True)
	peers: list[Path] = []
	seen_peers: set[str] = set()
	def _push_peer(p: Path) -> None:
		cp = canonicalize_root_dir(p, registry=reg)
		if cp == canon_root:
			return
		ck = cp.as_posix().lower()
		if ck not in seen_peers:
			seen_peers.add(ck)
			peers.append(cp)
	for p in pp.similar_projects:
		_push_peer(p)
	for grp in reg.similar_project_groups:
		members = list(grp.get('members') or ())
		mem_roots = [canonicalize_root_dir(m['project'], registry=reg) for m in members]
		is_member = any((mr == canon_root for mr in mem_roots))
		has_affiliated = False
		if not is_member:
			for m in members:
				for aff in m.get('affiliated_paths') or ():
					try:
						aff_p = Path(aff).resolve()
						if aff_p == canon_root or aff_p.is_relative_to(canon_root):
							has_affiliated = True
							break
					except OSError:
						continue
				if has_affiliated:
					break
		if is_member or has_affiliated:
			for mr in mem_roots:
				_push_peer(mr)
	peer_paths = [p.as_posix() for p in peers]
	peer_repos: list[str] = []
	seen_repos: set[str] = set()
	for p in peers:
		for slug in similar_project_repo_slugs(p, registry=reg):
			if slug.lower() not in seen_repos:
				seen_repos.add(slug.lower())
				peer_repos.append(slug)
	return (peer_paths, peer_repos)
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def _new(root, native, turn, *, recovered=False, journal_directory=None):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import canonicalize_root_dir
	canon_root = canonicalize_root_dir(root)
	key = _key(native, turn)
	# 2026-11-22
	# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
	# https://github.com/dmitry-ai/harness/issues/123
	sim_paths, sim_repos = _similar_projects_metadata(canon_root)
	# 2026-10-31
	# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
	# https://github.com/dmitry-ai/harness/issues/31
	# 2026-11-22
	# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
	# https://github.com/dmitry-ai/harness/issues/123
	lifecycle = {'verified': True, 'touched_repos': {}, 'issues': [], 'similar_projects': {'verified': True, 'peers': []}, 'violations': []} if recovered else _code_and_issue_lifecycle_status(canon_root, turn)
	# 2026-11-23
	# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
	# https://github.com/dmitry-ai/harness/issues/146
	issue_first_chk = {'verified': True, 'repos': {}, 'violations': []} if recovered else _issue_first_status(canon_root, turn)
	# 2026-11-23
	# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
	# https://github.com/dmitry-ai/harness/issues/138
	tdd_chk = {'verified': True, 'scopes': {}, 'violations': []} if recovered else _tdd_status(canon_root, turn)
	# 2026-10-24
	# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
	# https://github.com/dmitry-ai/harness/issues/17
	# 2026-11-23
	# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
	# https://github.com/dmitry-ai/harness/issues/146
	r = {'schema_version': 1, 'key': key, 'project_root': str(canon_root), 'platform': native['platform'], 'native_backend': native['native_backend'], 'conversation_id': native['conversation_id'], 'native_turn_id': turn['turn_id'], 'native_start_step': turn['start_step'], 'requests': turn['requests'], 'role': 'primary', 'journal_required': True, 'journal': str(_directory(canon_root, journal_directory)), 'applicable_rules': _policy(), 'git_optional_locks_env': os.environ.setdefault('GIT_OPTIONAL_LOCKS', '0'), 'exec5_check': _exec5_status(turn, canon_root, key), 'http_fetch_check': _http_fetch_status(turn, canon_root, key), 'compaction_check': _compaction_status(canon_root, key, turn), 'delegation_check': _delegation_status(canon_root, turn), 'budget_check': _budget_status(canon_root, turn), 'issue_first_check': issue_first_chk, 'code_lifecycle_check': lifecycle, 'tdd_check': tdd_chk, 'instruction_snapshot': _instruction_snapshot(canon_root, native, stage='recovery' if recovered else 'turn-begin'), 'format_independent': True, 'rule_comprehension_verified': False, 'required_completion': ['answer-prepare', 'native-delivery-check'], 'status': 'open', 'prepared': None, 'delivery': None, 'recovered_after_delivery': recovered, 'created_at': _now()}
	# 2026-11-22
	# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
	# https://github.com/dmitry-ai/harness/issues/123
	if sim_paths:
		r['similar_projects'] = sim_paths
	if sim_repos:
		r['similar_project_repos'] = sim_repos
	return r
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
def _persist(path, value):
	if path.exists() and _read(path) == value:
		return
	value['updated_at'] = _now()
	replace_bytes(path, _json(value))
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
def _persist_turn_recovery(root, conversation, suffix, build_receipt, *, platform=None, backend=None, clear_admission=False):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import canonicalize_root_dir
	root = canonicalize_root_dir(root)
	native = _native(root, conversation, platform=platform, backend=backend)
	turn = _active(native)
	if None is turn:
		raise ValueError('No active primary native turn to recover')
	key = _key(native, turn)
	# 2026-11-25
	# "Add PreToolUse canary probe to runtime snapshot validation and turn hook-crash audit":
	# https://github.com/dmitry-ai/harness/issues/251
	receipt, extra = build_receipt(root, key, turn, native)
	receipt_path = _folder(root) / f'{key}-{suffix}.json'
	with locked(_turn_lock(root, key)):
		replace_bytes(receipt_path, _json(receipt))
		path, value = _state(root, native, turn)
		if clear_admission:
			value.pop('admission_failure', None)
		_persist(path, value)
	rel_file = receipt_path.relative_to(root).as_posix() if receipt_path.is_relative_to(root) else str(receipt_path)
	return {**receipt, **extra(value), 'recovery_file': rel_file}
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
def _recoverable_step_status(turn, violations_key, covered_key, root=None, key=None):
	violations = list(turn.get(violations_key) or [])
	rec = _violation_recovery(root, key) if violations else {}
	covered = set(rec.get(covered_key) or [])
	unrecovered = [item for item in violations if item.get('step') not in covered]
	r = {'verified': not unrecovered, 'violations': violations}
	if violations and (not unrecovered):
		r['recovered_via_receipt'] = True
	return r
# 2026-11-21
# "Remove text-based explicit-project-root override from request binding":
# https://github.com/dmitry-ai/harness/issues/112
def _same_saved_request(old_req, cur_req, root):
	if old_req == cur_req:
		return True
	if not isinstance(old_req, dict) or not isinstance(cur_req, dict):
		return False
	if {k: v for k, v in old_req.items() if 'project_binding' != k} != {k: v for k, v in cur_req.items() if 'project_binding' != k}:
		return False
	old_b, cur_b = (old_req.get('project_binding'), cur_req.get('project_binding'))
	if not isinstance(old_b, dict) or not isinstance(cur_b, dict):
		return False
	# 2026-11-21
	# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
	# https://github.com/dmitry-ai/harness/issues/113
	from .path_registry import same_project_root
	old_kind, cur_kind = (old_b.get('kind'), cur_b.get('kind'))
	if 'explicit-project-root' != old_kind:
		if old_kind != cur_kind and not ({old_kind, cur_kind} <= {'antigravity-workspace-uris', 'antigravity-project-id'}):
			return False
		if {k: v for k, v in old_b.items() if k not in ('root', 'kind')} != {k: v for k, v in cur_b.items() if k not in ('root', 'kind')}:
			return False
	return same_project_root(old_b.get('root'), root) and same_project_root(cur_b.get('root'), root)
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def _state(root, native, turn, *, recovered=False, allow_extended=False, journal_directory=None, strict_journal=False):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	# 2026-11-21
	# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
	# https://github.com/dmitry-ai/harness/issues/113
	from .path_registry import canonicalize_root_dir, same_project_root
	root = canonicalize_root_dir(root)
	key = _key(native, turn)
	path = _folder(root) / (key + '.json')
	value = _read(path) if path.exists() else _new(root, native, turn, recovered=recovered, journal_directory=journal_directory)
	# 2026-11-23
	# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
	# https://github.com/dmitry-ai/harness/issues/132
	historical_done = bool('handed_off' == value.get('status') or (turn.get('completed') and value.get('status') in ('delivered', 'conflict')))
	# 2026-11-21
	# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
	# https://github.com/dmitry-ai/harness/issues/113
	active_validation = not recovered and not historical_done
	# 2026-11-03
	# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
	# https://github.com/dmitry-ai/harness/issues/41
	if 'instruction_snapshot' not in value and active_validation:
		value['instruction_snapshot'] = _instruction_snapshot(root, native, stage='existing-state-upgrade')
	if 'applicable_rules' not in value:
		value['applicable_rules'] = _policy()
	# 2026-10-24
	# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
	# https://github.com/dmitry-ai/harness/issues/17
	# 2026-11-03
	# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
	# https://github.com/dmitry-ai/harness/issues/41
	if 'git_optional_locks_env' not in value:
		value['git_optional_locks_env'] = os.environ.setdefault('GIT_OPTIONAL_LOCKS', '0')
	# 2026-11-10
	# "Isolate turn scratch answer files, allow pre-delivery response re-preparation, and enforce preemptive step/compaction budget stop":
	# https://github.com/dmitry-ai/harness/issues/49
	for name, check in (('exec5_check', lambda: _exec5_status(turn, root, key)), ('http_fetch_check', lambda: _http_fetch_status(turn, root, key)), ('compaction_check', lambda: _compaction_status(root, key, turn)), ('delegation_check', lambda: _delegation_status(root, turn)), ('budget_check', lambda: _budget_status(root, turn))):
		if active_validation or name not in value:
			value[name] = check()
	# 2026-11-22
	# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
	# https://github.com/dmitry-ai/harness/issues/123
	ex_file = _folder(root) / f'{key}-similar-exemptions.json'
	if ex_file.is_file():
		try:
			ex_loaded = _read(ex_file)
			ex_list = ex_loaded.get('exemptions') if isinstance(ex_loaded, dict) else ex_loaded
			if isinstance(ex_list, list):
				value['similar_project_exemptions'] = [it for it in ex_list if isinstance(it, dict)]
		except (OSError, ValueError):
			pass
	# 2026-11-03
	# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
	# https://github.com/dmitry-ai/harness/issues/41
	if active_validation:
		# 2026-11-22
		# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
		# https://github.com/dmitry-ai/harness/issues/123
		sim_paths, sim_repos = _similar_projects_metadata(root)
		if sim_paths:
			value['similar_projects'] = sim_paths
		else:
			value.pop('similar_projects', None)
		if sim_repos:
			value['similar_project_repos'] = sim_repos
		else:
			value.pop('similar_project_repos', None)
		# 2026-11-23
		# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
		# https://github.com/dmitry-ai/harness/issues/146
		value['issue_first_check'] = _issue_first_status(root, turn)
		# 2026-10-31
		# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
		# https://github.com/dmitry-ai/harness/issues/31
		# 2026-11-02
		# "Eliminate flashing Git console windows on Windows by enforcing CREATE_NO_WINDOW and skipping redundant Git subprocesses in journal-watch":
		# https://github.com/dmitry-ai/harness/issues/40
		value['code_lifecycle_check'] = _code_and_issue_lifecycle_status(root, turn, value)
		# 2026-11-23
		# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
		# https://github.com/dmitry-ai/harness/issues/138
		value['tdd_check'] = _tdd_status(root, turn)
	else:
		# 2026-10-31
		# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
		# https://github.com/dmitry-ai/harness/issues/31
		# 2026-11-23
		# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
		# https://github.com/dmitry-ai/harness/issues/138
		if 'code_lifecycle_check' not in value:
			value['code_lifecycle_check'] = {'verified': True, 'touched_repos': {}, 'issues': [], 'similar_projects': {'verified': True, 'peers': []}, 'violations': []}
		# 2026-11-23
		# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
		# https://github.com/dmitry-ai/harness/issues/146
		if not historical_done and 'issue_first_check' not in value:
			value['issue_first_check'] = {'verified': True, 'repos': {}, 'violations': []}
		# 2026-11-23
		# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
		# https://github.com/dmitry-ai/harness/issues/138
		# 2026-11-23
		# "Preserve historical delivered turn bytes when tdd_check is absent":
		# https://github.com/dmitry-ai/harness/issues/140
		if not historical_done and 'tdd_check' not in value:
			value['tdd_check'] = {'verified': True, 'scopes': {}, 'violations': []}
	# 2026-11-10
	# "Fix Antigravity executor/generation model mismatch in native-review-proof, decouple post-finalize deliverable reviews from initial Analysis.json, cache source grounding, and preserve journal recording on gate failure":
	# https://github.com/dmitry-ai/harness/issues/51
	# 2026-11-13
	# "Extract AnswerPreparationRunner class from prepare in completion.py, add typed gate_id readiness tracking, deduplicate native trace loading, and unify resolve_journal_dir":
	# https://github.com/dmitry-ai/harness/issues/57
	# 2026-11-14
	# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
	# https://github.com/dmitry-ai/harness/issues/60
	if False is value.get('readiness_check', {}).get('verified') and (not value.get('admission_failure')):
		if _gate_resolved(root, turn, value):
			value.pop('readiness_check', None)
	# 2026-11-19
	# "Remove Antigravity addons runtime health probing from Harness":
	# https://github.com/dmitry-ai/harness/issues/93
	if 'open' == value.get('status'):
		value.pop('addons_health', None)
	saved_directory = _directory(root, value['journal'])
	if strict_journal and None is not journal_directory and (saved_directory != _directory(root, journal_directory)):
		raise ValueError('The native turn already has a different journal; preserve its original binding')
	# 2026-11-21
	# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
	# https://github.com/dmitry-ai/harness/issues/113
	if not same_project_root(value.get('project_root'), root):
		raise ValueError('Completion state has a different native owner; preserved')
	for name, expected in [('platform', native['platform']), ('native_backend', native['native_backend']), ('conversation_id', native['conversation_id']), ('native_turn_id', turn['turn_id'])]:
		if value.get(name) != expected:
			raise ValueError('Completion state has a different native owner; preserved')
	# 2026-11-21
	# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
	# https://github.com/dmitry-ai/harness/issues/113
	if not (historical_done and journal.same_journal_identity(value.get('journal'), saved_directory)):
		value['journal'] = str(saved_directory)
	if not historical_done:
		value['project_root'] = str(root)
	# 2026-11-25
	# "Ensure atomic answer-prepare workflow alignment and safe open-turn reconciliation":
	# https://github.com/dmitry-ai/harness/issues/232
	from .reconcile_helpers import resolve_saved_turn_requests
	old, current = (value['requests'], turn['requests'])
	merged_requests = resolve_saved_turn_requests(root, native, turn, value, recovered=recovered, same_req_fn=_same_saved_request, journal_dir_fn=_directory)
	# 2026-11-21
	# "Remove text-based explicit-project-root override from request binding":
	# https://github.com/dmitry-ai/harness/issues/112
	if not (value.get('prepared') and len(current) > len(old)):
		value['requests'] = merged_requests
		r = (path, value)
	else:
		if not allow_extended:
			raise ValueError('A prepared answer does not cover the new native request; preserve it and reconcile the turn')
		value['uncovered_requests'] = current[len(old):]
		r = (path, value)
	return r
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def _active(native):
	if not native['primary']:
		r = None
	else:
		turn = next((turn for turn in native['turns'] if turn['turn_id'] == native['active_turn_id']), None)
		if None is turn or not turn['owned'] or turn['aborted']:
			# 2026-11-23
			# "Use native workspace priority and AST command parsing in request binding":
			# https://github.com/dmitry-ai/harness/issues/129
			from .platforms.request_binding import format_binding_diagnostic
			diag = native.get('binding_diagnostic') if isinstance(native.get('binding_diagnostic'), dict) else {}
			detail = format_binding_diagnostic(diag.get('expected_root'), diag.get('binding'), expected_job_id=diag.get('expected_job_id'))
			suffix = f' ({detail})' if detail else ''
			raise ValueError(f'No active native user turn belonging entirely to this project{suffix}')
		r = turn
	return r
# 2026-11-22
# "Auto-name Antigravity conversations from project journal step numbers":
# https://github.com/dmitry-ai/harness/issues/120
def format_conversation_journal_title(steps) -> str:
	ordered = sorted({st for st in (steps or ()) if int is type(st) and 1 <= st})
	return ', '.join((str(st) for st in ordered))
# 2026-11-22
# "Auto-name Antigravity conversations from project journal step numbers":
# https://github.com/dmitry-ai/harness/issues/120
# 2026-11-26
# "Harden follow-up launcher handoff and journal reservation integrity":
# https://github.com/dmitry-ai/harness/issues/269
def conversation_journal_steps(root, journal_directory, conversation_id: str) -> list[int]:
	from .journal_integrity import collect_conversation_journal_steps
	from .path_registry import canonicalize_root_dir
	cid = str(conversation_id or '').strip().lower()
	if not cid:
		r: list[int] = []
	else:
		root_p = canonicalize_root_dir(root)
		r = collect_conversation_journal_steps(_folder(root_p), _directory(root_p, journal_directory), cid, iter_groups_fn=journal.iter_answer_group_records, iter_res_fn=journal.iter_turn_reservations, read_fn=_read, same_j_fn=journal.same_journal_identity)
	return r
# 2026-11-22
# "Auto-name Antigravity conversations from project journal step numbers":
# https://github.com/dmitry-ai/harness/issues/120
def _sync_antigravity_conversation_title(root, native: dict, journal_directory=None, *, dry_run: bool=False) -> dict | None:
	if not isinstance(native, dict) or (not native.get('primary')):
		return None
	if 'antigravity' != platform_adapter_name(native.get('platform')):
		return None
	cid = str(native.get('conversation_id') or '').strip().lower()
	if not cid:
		return None
	steps = conversation_journal_steps(root, journal_directory, cid)
	title = format_conversation_journal_title(steps)
	if not title:
		return {'synced': False, 'changed': False, 'title': '', 'steps': [], 'conversation_id': cid, 'reason': 'no_journal_steps'}
	if dry_run:
		return {'synced': False, 'changed': False, 'dry_run': True, 'title': title, 'steps': steps, 'conversation_id': cid}
	try:
		from .platforms import antigravity as ag_mod
		res = ag_mod.update_conversation_title(cid, title, backend=native.get('native_backend'))
		return {**res, 'steps': steps}
	except Exception as exc:
		return {'synced': False, 'changed': False, 'title': title, 'steps': steps, 'conversation_id': cid, 'reason': 'sync_error', 'error': str(exc)}
# 2026-11-22
# "Auto-name Antigravity conversations from project journal step numbers":
# https://github.com/dmitry-ai/harness/issues/120
def sync_conversation_title(root, conversation=None, *, platform=None, backend=None, journal_directory=None, dry_run: bool=False) -> dict:
	from .path_registry import canonicalize_root_dir
	root_p = canonicalize_root_dir(root)
	native = _native(root_p, conversation, platform=platform, backend=backend)
	if not native.get('primary'):
		raise ValueError('A child executor has no primary conversation title to synchronize')
	eff_j = journal_directory
	if None is eff_j:
		t_dir = _folder(root_p)
		cid_low = str(native.get('conversation_id') or '').strip().lower()
		if t_dir.is_dir():
			for sf in sorted(t_dir.glob('*.json'), key=lambda p: p.stat().st_mtime_ns, reverse=True):
				# 2026-11-25
				# "Add auditable mechanical replacement recipe exemption for TDD and per-file issue gates":
				# https://github.com/dmitry-ai/harness/issues/239
				if sf.name.endswith(('-checkpoint-recovery.json', '-violation-recovery.json', '-similar-exemptions.json', '-ratchet-ok.json', '-mechanical-exempt.json')):
					continue
				try:
					st_obj = _read(sf)
				except (OSError, ValueError):
					continue
				if str(st_obj.get('conversation_id') or '').strip().lower() == cid_low and st_obj.get('journal'):
					eff_j = st_obj['journal']
					break
	jdir = _directory(root_p, eff_j)
	res = _sync_antigravity_conversation_title(root_p, native, jdir, dry_run=dry_run)
	if None is res:
		steps = conversation_journal_steps(root_p, jdir, native.get('conversation_id') or '')
		res = {'synced': False, 'changed': False, 'title': format_conversation_journal_title(steps), 'steps': steps, 'conversation_id': native.get('conversation_id'), 'reason': 'unsupported_platform'}
	return {**res, 'platform': native['platform'], 'journal': str(jdir)}
# 2026-11-23
# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
# https://github.com/dmitry-ai/harness/issues/132
# 2026-11-26
# "Harden follow-up launcher handoff and journal reservation integrity":
# https://github.com/dmitry-ai/harness/issues/269
def handoff_launcher_turn(launcher_root, target_root, job_id, *, conversation_id=None) -> list[dict]:
	from .journal_integrity import collect_handed_off_conversations, turn_matches_handoff
	from .path_registry import canonicalize_root_dir, same_project_root
	from .platforms.request_binding import _explicit
	if not launcher_root or not target_root:
		return []
	launcher_p = canonicalize_root_dir(launcher_root)
	target_p = canonicalize_root_dir(target_root)
	if same_project_root(launcher_p, target_p):
		return []
	t_dir = _folder(launcher_p)
	if not t_dir.is_dir():
		return []
	cid_filter = str(conversation_id or '').strip().lower() or None
	job_str = str(job_id or '').strip() or None
	if not cid_filter and not job_str:
		return []
	prior_cids = collect_handed_off_conversations(t_dir, target_p, read_fn=_read, same_root_fn=same_project_root)
	handed_off: list[dict] = []
	for sf in sorted(t_dir.glob('*.json')):
		# 2026-11-25
		# "Add auditable mechanical replacement recipe exemption for TDD and per-file issue gates":
		# https://github.com/dmitry-ai/harness/issues/239
		if sf.name.endswith(('-checkpoint-recovery.json', '-violation-recovery.json', '-similar-exemptions.json', '-ratchet-ok.json', '-mechanical-exempt.json')):
			continue
		try:
			st = _read(sf)
		except (OSError, ValueError):
			continue
		if 'open' != st.get('status') or _recorded(st):
			continue
		st_cid = str(st.get('conversation_id') or '').strip().lower()
		if None is not cid_filter and st_cid != cid_filter:
			continue
		if not turn_matches_handoff(st, st_cid, job_str, prior_cids, _explicit):
			continue
		key = str(st.get('key') or sf.stem)
		with locked(_turn_lock(launcher_p, key)):
			if not sf.is_file():
				continue
			try:
				cur = _read(sf)
			except (OSError, ValueError):
				continue
			if 'open' != cur.get('status') or _recorded(cur):
				continue
			cur_reqs = [r for r in (cur.get('requests') or ()) if isinstance(r, dict)]
			req_ids = [r['id'] for r in cur_reqs if r.get('id')]
			try:
				journal.release_turn_steps(_directory(launcher_p, cur.get('journal')), key, request_ids=req_ids)
			except (OSError, ValueError):
				pass
			cur.pop('reserved_journal_steps', None)
			cur['status'] = 'handed_off'
			cur['handed_off_to'] = {'project_root': str(target_p), 'job_id': job_str, 'handed_off_at': _now()}
			_persist(sf, cur)
			handed_off.append({'turn_key': key, 'conversation_id': cur.get('conversation_id'), 'launcher_root': str(launcher_p), 'target_root': str(target_p), 'job_id': job_str, 'status': 'handed_off'})
	return handed_off
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-21
# "Add idempotent Antigravity PreInvocation turn-begin hook and dry-run flag":
# https://github.com/dmitry-ai/harness/issues/116
def begin(root, conversation=None, *, platform=None, backend=None, watch=False, watch_dir=None, journal_directory=None, dry_run=False):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import canonicalize_root_dir
	root = canonicalize_root_dir(root)
	native = _native(root, conversation, platform=platform, backend=backend)
	turn = _active(native)
	if None is turn:
		r = {'role': 'child', 'journal_required': False, 'reason': 'The primary conversation owns the user journal'}
		# 2026-11-21
		# "Add idempotent Antigravity PreInvocation turn-begin hook and dry-run flag":
		# https://github.com/dmitry-ai/harness/issues/116
		if dry_run:
			r['dry_run'] = True
	elif dry_run:
		# 2026-11-21
		# "Add read-only answer-check pre-flight validation command to harness CLI":
		# https://github.com/dmitry-ai/harness/issues/117
		from .source_grounding import read_only_grounding
		with read_only_grounding():
			path, value = _state(root, native, turn, journal_directory=journal_directory, strict_journal=True)
		# 2026-11-23
		# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
		# https://github.com/dmitry-ai/harness/issues/146
		r = {'turn_key': value['key'], 'state': path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path), 'role': 'primary', 'journal_required': True, 'dry_run': True, 'status': value['status'], 'native_requests_sha256': _hash(_json(turn['requests'])), 'applicable_rules': value['applicable_rules'], 'git_optional_locks_env': value['git_optional_locks_env'], 'exec5_check': value['exec5_check'], 'http_fetch_check': value['http_fetch_check'], 'compaction_check': _compact_compaction_check(value['compaction_check']), 'delegation_check': value['delegation_check'], 'budget_check': value['budget_check'], 'issue_first_check': value.get('issue_first_check', {'verified': True, 'repos': {}, 'violations': []}), 'code_lifecycle_check': value['code_lifecycle_check'], 'tdd_check': value.get('tdd_check', {'verified': True, 'scopes': {}, 'violations': []}), 'rule_comprehension_verified': False, 'required_completion': value['required_completion'], 'execution_mode': 'foreground-only'}
		# 2026-11-22
		# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
		# https://github.com/dmitry-ai/harness/issues/123
		if value.get('similar_projects'):
			r['similar_projects'] = list(value['similar_projects'])
		if value.get('similar_project_repos'):
			r['similar_project_repos'] = list(value['similar_project_repos'])
	else:
		# 2026-11-23
		# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
		# https://github.com/dmitry-ai/harness/issues/132
		launcher_handoff: list[dict] = []
		ws_origin = native.get('workspace_root')
		if ws_origin:
			from .path_registry import project_paths, same_project_root
			if not same_project_root(ws_origin, root) and project_paths(root, exact_root=True).project_json.is_file():
				try:
					from .platforms.request_binding import native_project_id
					job_id = native_project_id(root)
					launcher_handoff = handoff_launcher_turn(ws_origin, root, job_id, conversation_id=native['conversation_id'])
				except (OSError, ValueError):
					launcher_handoff = []
		# 2026-11-21
		# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
		# https://github.com/dmitry-ai/harness/issues/109
		journal.ensure_project_journal_upgraded(root, selected=journal_directory)
		key = _key(native, turn)
		# 2026-11-26
		# "Persist emergency journal capture on Stop Gate fail-open and sync idle foreign reservations in turn-begin":
		# https://github.com/dmitry-ai/harness/issues/255
		native_reconciliation, foreign_reconciliation = reconcile_before_begin(root, native, turn, key, journal_directory, folder_fn=_folder, dir_fn=_directory, read_fn=_read, sync_fn=sync, key_fn=_key)
		with locked(_turn_lock(root, key)):
			path, value = _state(root, native, turn, journal_directory=journal_directory, strict_journal=True)
			# 2026-11-23
			# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
			# https://github.com/dmitry-ai/harness/issues/132
			if 'handed_off' != value.get('status'):
				# 2026-11-26
				# "Harden follow-up launcher handoff and journal reservation integrity":
				# https://github.com/dmitry-ai/harness/issues/269
				from .journal_integrity import sync_begin_turn_state
				sync_begin_turn_state(root, value, native, turn, native_reconciliation, dir_fn=_directory, recorded_fn=_recorded, reserve_fn=journal.reserve_turn_steps)
				if value['compaction_check'].get('occurred') and (not turn.get('completed')) and (value.get('status') not in ('delivered', 'conflict')):
					value['compaction_check']['index_file'] = _write_compaction_index_file(root, value['key'], turn, value['compaction_check'])
				_persist(path, value)
		# 2026-11-23
		# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
		# https://github.com/dmitry-ai/harness/issues/146
		result = {'turn_key': value['key'], 'state': path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path), 'role': 'primary', 'journal_required': True, 'status': value['status'], 'native_requests_sha256': _hash(_json(turn['requests'])), 'applicable_rules': value['applicable_rules'], 'git_optional_locks_env': value['git_optional_locks_env'], 'exec5_check': value['exec5_check'], 'http_fetch_check': value['http_fetch_check'], 'compaction_check': _compact_compaction_check(value['compaction_check']), 'delegation_check': value['delegation_check'], 'budget_check': value['budget_check'], 'issue_first_check': value.get('issue_first_check', {'verified': True, 'repos': {}, 'violations': []}), 'code_lifecycle_check': value['code_lifecycle_check'], 'tdd_check': value.get('tdd_check', {'verified': True, 'scopes': {}, 'violations': []}), 'rule_comprehension_verified': False, 'required_completion': value['required_completion']}
		# 2026-11-22
		# "Auto-name Antigravity conversations from project journal step numbers":
		# https://github.com/dmitry-ai/harness/issues/120
		if value.get('reserved_journal_steps'):
			result['reserved_journal_steps'] = list(value['reserved_journal_steps'])
		# 2026-11-23
		# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
		# https://github.com/dmitry-ai/harness/issues/132
		if value.get('handed_off_to'):
			result['handed_off_to'] = value['handed_off_to']
		if launcher_handoff:
			result['launcher_handoff'] = launcher_handoff
		# 2026-11-22
		# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
		# https://github.com/dmitry-ai/harness/issues/123
		if value.get('similar_projects'):
			result['similar_projects'] = list(value['similar_projects'])
		if value.get('similar_project_repos'):
			result['similar_project_repos'] = list(value['similar_project_repos'])
		# 2026-11-03
		# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
		# https://github.com/dmitry-ai/harness/issues/41
		result['execution_mode'] = 'foreground-only'
		# 2026-11-26
		# "Persist emergency journal capture on Stop Gate fail-open and sync idle foreign reservations in turn-begin":
		# https://github.com/dmitry-ai/harness/issues/255
		if foreign_reconciliation:
			result['foreign_reconciliation'] = foreign_reconciliation
		# 2026-11-22
		# "Auto-name Antigravity conversations from project journal step numbers":
		# https://github.com/dmitry-ai/harness/issues/120
		if None is not native_reconciliation:
			result['native_reconciliation'] = native_reconciliation
			current = next((item for item in (native_reconciliation.get('turns') or ()) if item.get('turn_key') == value['key']), None)
			if current:
				result['status'] = current['status']
		# 2026-11-22
		# "Auto-name Antigravity conversations from project journal step numbers":
		# https://github.com/dmitry-ai/harness/issues/120
		# 2026-11-23
		# "Unify tracked workspace detection in path_registry and add launcher-to-daily handoff":
		# https://github.com/dmitry-ai/harness/issues/132
		title_sync = None if 'handed_off' == value.get('status') else _sync_antigravity_conversation_title(root, native, value['journal'])
		if None is not title_sync:
			result['conversation_title_sync'] = title_sync
		r = result
	return r
# 2026-10-30
# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
# https://github.com/dmitry-ai/harness/issues/21
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
# 2026-11-21
# "Offload bulky compaction arrays to recovery index and add recover-checkpoint dry-run mode":
# https://github.com/dmitry-ai/harness/issues/119
def recover_checkpoint(root, conversation=None, *, platform=None, backend=None, dry_run=False):
	if dry_run:
		from .path_registry import canonicalize_root_dir
		from .source_grounding import read_only_grounding
		root_p = canonicalize_root_dir(root)
		with read_only_grounding():
			native = _native(root_p, conversation, platform=platform, backend=backend)
			turn = _active(native)
			if None is turn:
				raise ValueError('No active primary native turn to recover')
			key = _key(native, turn)
			comp = dict(turn.get('compaction') or {})
			comp_check = _compaction_status(root_p, key, turn)
			from collections import Counter
			raw_records = list(comp.get('pre_checkpoint_records') or [])
			file_index = _build_compaction_file_index(root_p, list(comp.get('pre_checkpoint_read_files') or []), list(comp.get('post_checkpoint_read_files') or []), list(comp.get('evicted_unreread_files') or []))
			file_index.sort(key=lambda it: (not it['reread_required_if_cited'], not it['evicted_unreread'], it['path']))
			tool_counts = dict(Counter((t for rec in raw_records for t in (rec.get('tools') or ()))))
			step_summary = [{'step': rec.get('step'), 'tools': list(rec.get('tools') or []), 'output_chars': sum((len(str(o)) for o in (rec.get('outputs') or [])))} for rec in raw_records[-10:]]
			return {
				'turn_key': key,
				'dry_run': True,
				'covered_checkpoint_step': comp.get('last_checkpoint_step'),
				'checkpoint_steps': list(comp.get('checkpoint_steps') or []),
				'file_index_count': len(file_index),
				'file_index': file_index[:30],
				'file_index_truncated': 30 < len(file_index),
				'pre_checkpoint_record_count': len(raw_records),
				'tool_counts': tool_counts,
				'step_summary': step_summary,
				'step_summary_truncated': 10 < len(raw_records),
				'compaction_check': _compact_compaction_check(comp_check),
			}
	from .path_registry import canonicalize_root_dir
	root_p = canonicalize_root_dir(root)
	native = _native(root_p, conversation, platform=platform, backend=backend)
	turn = _active(native)
	if None is turn:
		raise ValueError('No active primary native turn to recover')
	key = _key(native, turn)
	comp = dict(turn.get('compaction') or {})
	raw_records = list(comp.get('pre_checkpoint_records') or [])
	rec_dir = _folder(root_p) / f'{key}-recovery'
	compact_mode = 5 < len(raw_records)
	receipt_path = _folder(root_p) / f'{key}-checkpoint-recovery.json'
	with locked(_turn_lock(root_p, key)):
		rec_dir.mkdir(parents=True, exist_ok=True)
		indexed_records = []
		inline_records = []
		for rec in raw_records:
			st = rec.get('step')
			outs = list(rec.get('outputs') or [])
			step_file = rec_dir / f'step-{st}.txt'
			if outs:
				replace_bytes(step_file, ('\n--- OUTPUT ---\n'.join(outs) + '\n').encode('utf-8'))
			rel_step = step_file.relative_to(root_p).as_posix() if step_file.is_relative_to(root_p) else str(step_file)
			indexed_records.append({'step': st, 'tools': list(rec.get('tools') or []), 'output_file': rel_step if outs else None, 'output_preview': [o[:200] for o in outs[:2]]})
			if not compact_mode:
				inline_records.append({**rec, 'output_file': rel_step if outs else None})
		rel_dir = rec_dir.relative_to(root_p).as_posix() if rec_dir.is_relative_to(root_p) else str(rec_dir)
		receipt = {'turn_key': key, 'recovered_at': _now(), 'compact_mode': compact_mode, 'covered_checkpoint_step': comp.get('last_checkpoint_step'), 'checkpoint_steps': list(comp.get('checkpoint_steps') or []), 'pre_checkpoint_tool_steps': list(comp.get('pre_checkpoint_tool_steps') or []), 'pre_checkpoint_read_files': list(comp.get('pre_checkpoint_read_files') or []), 'post_checkpoint_read_files': list(comp.get('post_checkpoint_read_files') or []), 'evicted_unreread_files': list(comp.get('evicted_unreread_files') or []), 'recovery_dir': rel_dir}
		replace_bytes(receipt_path, _json(receipt))
		path, value = _state(root_p, native, turn)
		# 2026-11-03
		# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
		# https://github.com/dmitry-ai/harness/issues/43
		value.pop('admission_failure', None)
		idx_rel = _write_compaction_index_file(root_p, key, turn, value['compaction_check'], step_records=indexed_records)
		value['compaction_check']['index_file'] = idx_rel
		_persist(path, value)
	rel_file = receipt_path.relative_to(root_p).as_posix() if receipt_path.is_relative_to(root_p) else str(receipt_path)
	out = {
		'turn_key': key,
		'recovered_at': receipt['recovered_at'],
		'compact_mode': compact_mode,
		'covered_checkpoint_step': receipt['covered_checkpoint_step'],
		'checkpoint_steps': receipt['checkpoint_steps'],
		'recovery_dir': rel_dir,
		'recovery_file': rel_file,
		'index_file': idx_rel,
		'pre_checkpoint_record_count': len(raw_records),
		'compaction_check': _compact_compaction_check(value['compaction_check'], index_file=idx_rel),
	}
	if not compact_mode:
		out['pre_checkpoint_records'] = inline_records
	else:
		out['pre_checkpoint_records_preview'] = indexed_records[-5:]
	return out
# 2026-11-02
# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
# https://github.com/dmitry-ai/harness/issues/36
def recover_turn_violation(root, conversation=None, *, reason=None, platform=None, backend=None):
	# 2026-11-25
	# "Add PreToolUse canary probe to runtime snapshot validation and turn hook-crash audit":
	# https://github.com/dmitry-ai/harness/issues/251
	from .hook_crash_audit import build_violation_recovery_receipt
	return _persist_turn_recovery(root, conversation, 'violation-recovery', lambda rp, k, t, nat: build_violation_recovery_receipt(rp, k, t, reason, _now, native=nat), platform=platform, backend=backend)
# 2026-11-22
# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
# https://github.com/dmitry-ai/harness/issues/123
def similar_project_exempt(root, peer, reason, conversation=None, *, platform=None, backend=None):
	from .issue_lifecycle import similar_project_repo_slugs
	from .path_registry import canonicalize_root_dir, load_registry, project_paths
	reason_clean = (reason or '').strip()
	if 30 > len(reason_clean):
		raise ValueError('Exemption reason must be an explicit technical justification of at least 30 characters')
	root_p = canonicalize_root_dir(root)
	reg = load_registry()
	pp = project_paths(root_p, registry=reg, exact_root=True)
	allowed_peers: list[Path] = []
	seen_keys: set[str] = set()
	def _add_allowed(p: Path) -> None:
		cp = canonicalize_root_dir(p, registry=reg)
		if cp == root_p:
			return
		ck = cp.as_posix().lower()
		if ck not in seen_keys:
			seen_keys.add(ck)
			allowed_peers.append(cp)
	for sp in pp.similar_projects:
		_add_allowed(sp)
	for grp in reg.similar_project_groups:
		for mem in grp.get('members') or ():
			_add_allowed(Path(mem['project']))
	peer_raw = (peer or '').strip()
	if not peer_raw:
		raise ValueError('Select a declared --peer project root or GitHub owner/repo slug')
	peer_norm_path = None
	if '\\' in peer_raw or ':' in peer_raw or Path(peer_raw).is_absolute() or Path(peer_raw).is_dir():
		try:
			peer_norm_path = canonicalize_root_dir(peer_raw, registry=reg).as_posix().lower()
		except (OSError, ValueError):
			peer_norm_path = None
	matched_peer: Path | None = None
	matched_slugs: list[str] = []
	for cand in allowed_peers:
		cand_slugs = similar_project_repo_slugs(cand, registry=reg)
		slug_set = {s.lower() for s in cand_slugs}
		if peer_raw.lower() in slug_set or cand.as_posix().lower() == (peer_norm_path or peer_raw.replace('\\', '/').rstrip('/').lower()):
			matched_peer = cand
			matched_slugs = cand_slugs
			break
	if None is matched_peer:
		raise ValueError(f'Unknown or undeclared similar peer project: {peer_raw}')
	native = _native(root_p, conversation, platform=platform, backend=backend)
	turn = _active(native)
	if None is turn:
		raise ValueError('No active primary native turn to record similar-project exemption')
	key = _key(native, turn)
	ex_path = _folder(root_p) / f'{key}-similar-exemptions.json'
	entry = {'peer': peer_raw, 'peer_root': matched_peer.as_posix(), 'peer_repos': matched_slugs, 'reason': reason_clean, 'recorded_at': _now()}
	with locked(_turn_lock(root_p, key)):
		existing_items: list[dict] = []
		if ex_path.is_file():
			try:
				raw_loaded = _read(ex_path)
				raw_list = raw_loaded.get('exemptions') if isinstance(raw_loaded, dict) else raw_loaded
				if isinstance(raw_list, list):
					existing_items = [it for it in raw_list if isinstance(it, dict) and str(it.get('peer_root') or '').lower() != matched_peer.as_posix().lower()]
			except (OSError, ValueError):
				existing_items = []
		existing_items.append(entry)
		replace_bytes(ex_path, _json({'turn_key': key, 'exemptions': existing_items}))
		path, value = _state(root_p, native, turn)
		if value.get('code_lifecycle_check', {}).get('verified'):
			value.pop('admission_failure', None)
		_persist(path, value)
	rel_file = ex_path.relative_to(root_p).as_posix() if ex_path.is_relative_to(root_p) else str(ex_path)
	return {'turn_key': key, 'peer_root': matched_peer.as_posix(), 'peer_repos': matched_slugs, 'reason': reason_clean, 'exemption_file': rel_file, 'code_lifecycle_check': value['code_lifecycle_check']}
# 2026-11-23
# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
# https://github.com/dmitry-ai/harness/issues/138
def ratchet_ok(root, file_path, reason, conversation=None, *, platform=None, backend=None):
	from .path_registry import canonicalize_root_dir
	from .tdd_gate import validate_ratchet_reason
	file_clean = (file_path or '').strip()
	if not file_clean:
		raise ValueError('Provide --file identifying the test file whose expectation is intentionally changing')
	ok_r, err_r = validate_ratchet_reason(reason)
	if not ok_r:
		raise ValueError(err_r)
	reason_clean = ' '.join((reason or '').strip().split())
	root_p = canonicalize_root_dir(root)
	native = _native(root_p, conversation, platform=platform, backend=backend)
	turn = _active(native)
	if None is turn:
		raise ValueError('No active primary native turn to record RATCHET-OK approval')
	key = _key(native, turn)
	rc_path = _folder(root_p) / f'{key}-ratchet-ok.json'
	entry = {'file': file_clean, 'reason': reason_clean, 'recorded_at': _now()}
	with locked(_turn_lock(root_p, key)):
		existing_items: list[dict] = []
		if rc_path.is_file():
			try:
				raw_loaded = _read(rc_path)
				raw_list = raw_loaded.get('approvals') if isinstance(raw_loaded, dict) else raw_loaded
				if isinstance(raw_list, list):
					existing_items = [it for it in raw_list if isinstance(it, dict) and str(it.get('file') or '').replace('\\', '/').lower() != file_clean.replace('\\', '/').lower()]
			except (OSError, ValueError):
				existing_items = []
		existing_items.append(entry)
		replace_bytes(rc_path, _json({'turn_key': key, 'approvals': existing_items}))
	rel_file = rc_path.relative_to(root_p).as_posix() if rc_path.is_relative_to(root_p) else str(rc_path)
	return {'turn_key': key, 'file': file_clean, 'reason': reason_clean, 'receipt_file': rel_file, 'approvals': existing_items}
# 2026-11-23
# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
# https://github.com/dmitry-ai/harness/issues/138
def tdd_check_turn(root, conversation=None, *, platform=None, backend=None):
	from .path_registry import canonicalize_root_dir
	from .source_grounding import read_only_grounding
	root_p = canonicalize_root_dir(root)
	eff_plat = platform_name(platform)
	eff_conv = conversation or (os.environ.get('CODEX_THREAD_ID') if 'codex' == eff_plat else None)
	# 2026-11-24
	# "Cache runtime settings and deduplicate evidence validation in hot paths":
	# https://github.com/dmitry-ai/harness/issues/227
	with read_only_grounding(), skip_shell_violations():
		native = _native(root_p, eff_conv, platform=eff_plat, backend=backend)
		if native['primary']:
			role = 'primary'
			turn_obj = _active(native)
		else:
			role = 'child'
			turn_obj = _scan_child_trace_turn(root_p, eff_conv, native)
		turn_key = _key(native, turn_obj)
		tdd_chk = _tdd_status(root_p, turn_obj)
	return {'valid': bool(tdd_chk.get('verified', True)), 'read_only': True, 'role': role, 'turn_key': turn_key, 'tdd_check': tdd_chk, 'event_count': len(turn_obj.get('tdd_events') or [])}
# 2026-11-23
# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
# https://github.com/dmitry-ai/harness/issues/146
def issue_first_check_turn(root, conversation=None, *, platform=None, backend=None):
	from .path_registry import canonicalize_root_dir
	from .source_grounding import read_only_grounding
	root_p = canonicalize_root_dir(root)
	eff_plat = platform_name(platform)
	eff_conv = conversation or (os.environ.get('CODEX_THREAD_ID') if 'codex' == eff_plat else None)
	# 2026-11-24
	# "Cache runtime settings and deduplicate evidence validation in hot paths":
	# https://github.com/dmitry-ai/harness/issues/227
	with read_only_grounding(), skip_shell_violations():
		native = _native(root_p, eff_conv, platform=eff_plat, backend=backend)
		if native['primary']:
			role = 'primary'
			turn_obj = _active(native)
		else:
			role = 'child'
			turn_obj = _scan_child_trace_turn(root_p, eff_conv, native)
		turn_key = _key(native, turn_obj)
		if_chk = _issue_first_status(root_p, turn_obj)
	return {'valid': bool(if_chk.get('verified', True)), 'read_only': True, 'role': role, 'turn_key': turn_key, 'issue_first_check': if_chk, 'event_count': len(turn_obj.get('issue_first_events') or [])}
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
_norm_journal_text = journal.norm_journal_text
# 2026-11-23
# "Prepend JSON metadata headers to new journal responses":
# https://github.com/dmitry-ai/harness/issues/151
_norm_journal_response_text = journal.norm_journal_response_text
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
_find_orphan_or_overwritten_steps = journal.find_orphan_or_overwritten_steps
# 2026-11-23
# "Prepend JSON metadata headers to new journal responses":
# https://github.com/dmitry-ai/harness/issues/151
def _matches_recorded_response(recorded, raw_response: str, raw_sha: str) -> bool:
	if not isinstance(recorded, dict):
		return False
	if recorded.get('response_sha256') == raw_sha or recorded.get('body_sha256') == raw_sha:
		return True
	raw_prep = recorded.get('response_file') or ''
	if raw_prep:
		prep_file = journal.resolve_migrated_step_file(raw_prep)
		if prep_file.is_file():
			try:
				prep_text = prep_file.read_bytes().decode('utf-8')
				if _hash(prep_text.encode('utf-8')) == recorded.get('response_sha256'):
					from .metadata import strip_leading_metadata_header
					if _hash(strip_leading_metadata_header(prep_text).encode('utf-8')) == raw_sha:
						return True
			except (OSError, UnicodeDecodeError):
				pass
	return False
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-10
# "Isolate turn scratch answer files, allow pre-delivery response re-preparation, and enforce preemptive step/compaction budget stop":
# https://github.com/dmitry-ai/harness/issues/49
def _group(root, native, turn, response, directory, *, allow_reprepare=False):
	key = 'native-' + _key(native, turn)
	legacy = turn['turn_id']
	groups = journal.state_dir(directory) / 'answer-groups'
	native_ids = [req['id'] for req in turn['requests']]
	norm_turn_reqs = [_norm_journal_text(req['text']) for req in turn['requests']]
	# 2026-11-23
	# "Prepend JSON metadata headers to new journal responses":
	# https://github.com/dmitry-ai/harness/issues/151
	norm_turn_resp = _norm_journal_response_text(response)
	# 2026-11-20
	# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
	# https://github.com/dmitry-ai/harness/issues/101
	_, res_dir = journal.journal_pair_dirs(directory)
	matches = []
	# 2026-11-14
	# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
	# https://github.com/dmitry-ai/harness/issues/60
	for _, old in journal.iter_answer_group_records(directory):
		if old.get('request_ids') == native_ids:
			# 2026-11-02
			# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
			# https://github.com/dmitry-ai/harness/issues/36
			old_reqs = old.get('requests') or []
			reqs_ok = old_reqs == [req['text'] for req in turn['requests']] or [_norm_journal_text(x) for x in old_reqs] == norm_turn_reqs
			resp_ok = old.get('response_sha256') == _hash(response.encode('utf-8'))
			if not resp_ok and old.get('steps'):
				# 2026-11-21
				# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
				# https://github.com/dmitry-ai/harness/issues/109
				res_p = journal.step_file(res_dir, old['steps'][0], directory=directory)
				if res_p.is_file():
					try:
						disk_r = res_p.read_bytes().decode('utf-8')
						# 2026-11-23
						# "Prepend JSON metadata headers to new journal responses":
						# https://github.com/dmitry-ai/harness/issues/151
						resp_ok = _hash(disk_r.encode('utf-8')) == old.get('response_sha256') and _norm_journal_response_text(disk_r) == norm_turn_resp
					except (OSError, UnicodeDecodeError):
						pass
			if not reqs_ok or (not resp_ok and (not allow_reprepare)):
				raise ValueError('A journal for these exact native request IDs has different bytes; preserve the conflict')
			matches.append(old)
	if 1 < len(matches):
		raise ValueError('More than one journal group claims these native request IDs; preserve the ambiguity')
	if matches:
		r = (matches[0]['turn'], native_ids)
	elif re.fullmatch('[A-Za-z0-9_-]{1,100}', legacy) and (groups / (legacy + '.json')).exists():
		old = _read(groups / (legacy + '.json'))
		old_reqs = old.get('requests') or []
		reqs_ok = old_reqs == [req['text'] for req in turn['requests']] or [_norm_journal_text(x) for x in old_reqs] == norm_turn_reqs
		# 2026-11-23
		# "Prepend JSON metadata headers to new journal responses":
		# https://github.com/dmitry-ai/harness/issues/151
		resp_ok = old.get('response_sha256') == _hash(response.encode('utf-8'))
		if not resp_ok and old.get('steps'):
			res_p = journal.step_file(res_dir, old['steps'][0], directory=directory)
			if res_p.is_file():
				try:
					disk_r = res_p.read_bytes().decode('utf-8')
					resp_ok = _hash(disk_r.encode('utf-8')) == old.get('response_sha256') and _norm_journal_response_text(disk_r) == norm_turn_resp
				except (OSError, UnicodeDecodeError):
					pass
		if not reqs_ok or (not resp_ok and (not allow_reprepare)):
			raise ValueError('Existing native-turn journal has different bytes; preserve the conflict')
		r = (legacy, old.get('request_ids'))
	else:
		r = (key, native_ids)
	return r
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def _recorded(value):
	return next((receipt for receipt in (value.get('prepared'), value.get('journal_record'), value.get('delivery')) if isinstance(receipt, dict) and 'journal_steps' in receipt), None)
# 2026-10-31
# "Prevent intermediate subagent status replies from polluting the journal, enforce TEXT-1 language gate in completion, and codify background task timeouts":
# https://github.com/dmitry-ai/harness/issues/30
# 2026-11-13
# "Unify quote normalization, MarkdownIt link/quote traversal, locale checks, numeric corpus tokenization, and Evidence loading across response_grounding.py, completion.py, source_grounding.py, claims.py, and review.py":
# https://github.com/dmitry-ai/harness/issues/59
def _intermediate_or_language_issues(requests, response: str) -> list[str]:
	# 2026-11-23
	# "Detect unfinished background tasks in Antigravity turns and inherit unclosed TDD-FULL-GATE":
	# https://github.com/dmitry-ai/harness/issues/166
	from .platforms.trace_common import is_waiting_status_stub
	# 2026-11-23
	# "Configure default user locale for language-neutral commands in TEXT-1 and locale gate":
	# https://github.com/dmitry-ai/harness/issues/131
	from .runtime import default_user_locale
	from .source_grounding import verify_target_locale
	r = []
	if is_waiting_status_stub(response or ''):
		r.append('FILE-3 / REVIEW-1: Response is an intermediate subagent/task waiting status stub rather than a complete final response')
	req_raw = '\n'.join((req.get('text', '') if isinstance(req, dict) else str(req) for req in requests or []))
	for err in verify_target_locale(response or '', target_locale='und', container_text=req_raw, allow_explicit_english_request=True, min_target_ratio=0.01, min_alpha=20, default_locale=default_user_locale()):
		r.append(err['message'])
	return r
# 2026-11-20
# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
# https://github.com/dmitry-ai/harness/issues/101
def _same_turn_artifact_path(root: Path, saved_str: str | None, current_str: str, *, kind: str) -> bool:
	if saved_str == current_str:
		return True
	if not isinstance(saved_str, str) or not saved_str.strip():
		return False
	saved_p, cur_p = (Path(saved_str), Path(current_str))
	if saved_p.exists() or saved_p.name != cur_p.name:
		return False
	# 2026-11-21
	# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
	# https://github.com/dmitry-ai/harness/issues/113
	from .path_registry import canonicalize_root_dir, same_project_root
	canon_root = canonicalize_root_dir(root)
	if 'response' == kind:
		# 2026-11-21
		# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
		# https://github.com/dmitry-ai/harness/issues/109
		s_info, c_info = (journal.parse_step_file_path(saved_p), journal.parse_step_file_path(cur_p))
		return None is not s_info and None is not c_info and s_info[1] in ('res', '\u227a') and c_info[1] in ('res', '\u227a') and (s_info[2] == c_info[2]) and journal.same_journal_identity(s_info[0], c_info[0])
	# 2026-11-21
	# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
	# https://github.com/dmitry-ai/harness/issues/113
	if 'group' == kind and 'answer-groups' == saved_p.parent.name and 4 <= len(saved_p.parents) and 4 <= len(cur_p.parents) and ('.journal' == saved_p.parents[2].name):
		return any((same_project_root(anc, canon_root) for anc in saved_p.parents[3:7])) and any((same_project_root(anc, canon_root) for anc in cur_p.parents[3:7]))
	return False
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-03
# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
# https://github.com/dmitry-ai/harness/issues/41
# 2026-11-10
# "Isolate turn scratch answer files, allow pre-delivery response re-preparation, and enforce preemptive step/compaction budget stop":
# https://github.com/dmitry-ai/harness/issues/49
def _record(root, native, turn, response, directory, *, existing=None, purpose='publication', allow_reprepare=False):
	if purpose not in ('publication', 'observation'):
		raise ValueError('Choose publication admission or historical observation')
	directory = _directory(root, directory)
	# 2026-11-20
	# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
	# https://github.com/dmitry-ai/harness/issues/101
	req_dir, res_dir = journal.journal_pair_dirs(directory)
	from . import admission
	# 2026-11-23
	# "Prepend JSON metadata headers to new journal responses":
	# https://github.com/dmitry-ai/harness/issues/151
	from .metadata import build_journal_metadata, extract_leading_metadata_header, prepend_metadata_header, strip_leading_metadata_header
	clean_body_sha = _hash(strip_leading_metadata_header(response).encode('utf-8'))
	token, request_ids = _group(root, native, turn, response, directory, allow_reprepare=allow_reprepare)
	group_file = journal.state_dir(directory) / 'answer-groups' / (token + '.json')
	already_complete = group_file.exists() and 'complete' == _read(group_file).get('status')
	if not already_complete or allow_reprepare:
		# 2026-10-31
		# "Prevent intermediate subagent status replies from polluting the journal, enforce TEXT-1 language gate in completion, and codify background task timeouts":
		# https://github.com/dmitry-ai/harness/issues/30
		lang_issues = _intermediate_or_language_issues(turn['requests'], response)
		if lang_issues:
			raise ValueError('; '.join(lang_issues))
	if existing:
		if not already_complete:
			raise ValueError('Recorded answer-group receipt is missing or incomplete; preserve journal history')
		if _read(group_file).get('steps') != existing['journal_steps']:
			raise ValueError('Recorded answer-group steps changed; preserve journal history')
	# 2026-11-02
	# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
	# https://github.com/dmitry-ai/harness/issues/36
	effective_requests = [r['text'] for r in turn['requests']]
	effective_response = response
	adopt_steps = None
	adopted_existing = False
	reprepared_before_delivery = False
	g_data = None
	if already_complete:
		g_data = _read(group_file)
		g_reqs = g_data.get('requests') or []
		if [_norm_journal_text(x) for x in g_reqs] == [_norm_journal_text(x) for x in effective_requests]:
			effective_requests = list(g_reqs)
		if g_data.get('steps') and _hash(effective_response.encode('utf-8')) != g_data.get('response_sha256'):
			# 2026-11-21
			# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
			# https://github.com/dmitry-ai/harness/issues/109
			res_p = journal.step_file(res_dir, g_data['steps'][0], directory=directory)
			if res_p.is_file():
				try:
					disk_r = res_p.read_bytes().decode('utf-8')
					# 2026-11-23
					# "Prepend JSON metadata headers to new journal responses":
					# https://github.com/dmitry-ai/harness/issues/151
					if _hash(disk_r.encode('utf-8')) == g_data.get('response_sha256') and _norm_journal_response_text(disk_r) == _norm_journal_response_text(effective_response):
						effective_response = disk_r
				except (OSError, UnicodeDecodeError):
					pass
			# 2026-11-10
			# "Isolate turn scratch answer files, allow pre-delivery response re-preparation, and enforce preemptive step/compaction budget stop":
			# https://github.com/dmitry-ai/harness/issues/49
			if _hash(effective_response.encode('utf-8')) != g_data.get('response_sha256') and allow_reprepare:
				reprepared_before_delivery = True
	elif None is existing:
		adopt_steps, disk_reqs, disk_resp = _find_orphan_or_overwritten_steps(directory, effective_requests, effective_response, request_ids)
		if None is not adopt_steps:
			effective_requests = disk_reqs
			effective_response = disk_resp
			adopted_existing = True
	# 2026-11-23
	# "Prepend JSON metadata headers to new journal responses":
	# https://github.com/dmitry-ai/harness/issues/151
	if ((not already_complete and (not adopted_existing)) or reprepared_before_delivery) and None is extract_leading_metadata_header(effective_response)[0]:
		turn_key = _key(native, turn)
		target_steps = list(g_data['steps']) if reprepared_before_delivery and isinstance(g_data, dict) and g_data.get('steps') else journal.reserve_turn_steps(directory, turn_key, native['conversation_id'], request_ids)
		conv_steps = conversation_journal_steps(root, directory, native['conversation_id'])
		meta = build_journal_metadata(
			root,
			native,
			turn,
			journal_dir=directory,
			steps=target_steps,
			turn_key=turn_key,
			turn_state_path=_folder(root) / (turn_key + '.json'),
			group_file=group_file,
			conversation_steps=conv_steps,
		)
		effective_response = prepend_metadata_header(effective_response, meta)
	identity = admission.binding(directory, effective_requests, effective_response, token, request_ids)
	if already_complete and not reprepared_before_delivery:
		if purpose == 'publication':
			from .text_workflow import gate_requests
			gate_requests([root, directory], effective_requests, effective_response)
		steps = journal.verify_answer(directory, effective_requests, effective_response, token, request_ids)
		# 2026-11-22
		# "Auto-name Antigravity conversations from project journal step numbers":
		# https://github.com/dmitry-ai/harness/issues/120
		journal.release_turn_steps(directory, _key(native, turn), request_ids=request_ids)
		proof = _read(group_file).get('admission')
		if existing and existing.get('admission') != proof:
			raise ValueError('Recorded admission differs from the original answer group; preserve history')
		verification = admission.verify(proof, identity) if proof else {'status': 'legacy_proof_gap', 'scope': 'journal_and_native_identity_only'}
	else:
		capability = admission.capture([root, directory], effective_requests, effective_response, identity)
		# 2026-11-22
		# "Auto-name Antigravity conversations from project journal step numbers":
		# https://github.com/dmitry-ai/harness/issues/120
		steps = journal.record_answer(directory, effective_requests, effective_response, token, request_ids, adopt_steps=adopt_steps, admission=capability, allow_reprepare=reprepared_before_delivery, reserved_turn_key=_key(native, turn))
		proof = capability.reference
		verification = {'status': 'verified', 'scope': 'original_publication_admission' if purpose == 'observation' else 'current_publication_readiness'}
	for step, request in zip(steps, effective_requests):
		# 2026-11-21
		# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
		# https://github.com/dmitry-ai/harness/issues/109
		if journal.step_file(req_dir, step, directory=directory).read_bytes() != request.encode('utf-8'):
			raise ValueError('Recorded request read-back differs from native text')
		if journal.step_file(res_dir, step, directory=directory).read_bytes() != effective_response.encode('utf-8'):
			raise ValueError('Recorded response read-back differs from prepared text')
	# 2026-11-23
	# "Prepend JSON metadata headers to new journal responses":
	# https://github.com/dmitry-ai/harness/issues/151
	recorded = {'journal_steps': steps, 'response_sha256': _hash(effective_response.encode('utf-8')), 'body_sha256': clean_body_sha, 'response_file': str(journal.step_file(res_dir, steps[0], directory=directory)), 'group_file': str(group_file)}
	if existing:
		# 2026-11-20
		# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
		# https://github.com/dmitry-ai/harness/issues/101
		if existing.get('journal_steps') != recorded['journal_steps'] or existing.get('response_sha256') != recorded['response_sha256'] or (not _same_turn_artifact_path(root, existing.get('response_file'), recorded['response_file'], kind='response')) or (not _same_turn_artifact_path(root, existing.get('group_file'), recorded['group_file'], kind='group')):
			raise ValueError('Recorded answer receipt differs from its verified journal identity; preserve history')
		if existing.get('group_sha256') and existing['group_sha256'] != _hash(group_file.read_bytes()):
			raise ValueError('Recorded answer-group bytes changed; preserve history')
		return dict(existing), verification
	res_receipt = {**recorded, 'group_sha256': _hash(group_file.read_bytes()), 'recorded_at': _now(), 'reused_complete_journal_group': bool((already_complete and not reprepared_before_delivery) or adopted_existing), 'admission': proof}
	if reprepared_before_delivery:
		res_receipt['reprepared_before_delivery'] = True
	return res_receipt, verification
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def _unchanged(root, native, turn):
	latest = _native(root, native['conversation_id'], platform=native['platform'], backend=native['native_backend'])
	current = _active(latest)
	if None is current or _key(latest, current) != _key(native, turn) or current['requests'] != turn['requests']:
		raise ValueError('The active native turn or requests changed during preparation; readiness was not granted')
# 2026-11-13
# "Extract AnswerPreparationRunner class from prepare in completion.py, add typed gate_id readiness tracking, deduplicate native trace loading, and unify resolve_journal_dir":
# https://github.com/dmitry-ai/harness/issues/57
def _workflow_gate_resolved(root_p, turn, kind):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	wf_file = project_paths(root_p, exact_root=True).workflow_json
	if not wf_file.is_file():
		r = True
	elif 'workflow_adoption' == kind:
		from .workflow import load
		r = {req['id'] for req in turn.get('requests') or []}.issubset({req['id'] for req in load(root_p).get('requests') or []})
	else:
		from .review import approval_current
		from .workflow import load
		r = bool(approval_current(root_p, load(root_p)))
	return r
# 2026-11-01
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
# 2026-11-21
# "Add read-only answer-check pre-flight validation command to harness CLI":
# https://github.com/dmitry-ai/harness/issues/117
def _find_evicted_cited_files(root: Path, pp, turn_key: str | None, compaction_check: dict, response: str) -> list[str]:
	unreread_cited: list[str] = []
	if compaction_check.get('occurred') and compaction_check.get('evicted_unreread_files'):
		pre_cp_authored = False
		if turn_key:
			scratch_ans = pp.scratch_dir / f'answer-{turn_key}.md'
			post_cp_w_low = {str(w).replace('\\', '/').lower() for w in (compaction_check.get('post_checkpoint_written_files') or [])}
			if scratch_ans.is_file() and scratch_ans.resolve().as_posix().lower() not in post_cp_w_low:
				try:
					pre_cp_authored = scratch_ans.read_text(encoding='utf-8') == response
				except OSError:
					pre_cp_authored = False
		if not pre_cp_authored:
			from .source_grounding import extract_block_links, markdown_parser
			ev_map = {p.replace('\\', '/').lower(): p for p in compaction_check['evicted_unreread_files']}
			for blk in markdown_parser().parse(response):
				if 'inline' == blk.type:
					lpaths, _ = extract_block_links(blk, root, None)
					for rp in lpaths:
						rlow = rp.as_posix().lower()
						if rlow in ev_map and (rlow.endswith('/kb/source.md') or '/source/' in rlow or '/res/' in rlow or '/\u227a/' in rlow or '/kb/' in rlow) and (ev_map[rlow] not in unreread_cited):
							unreread_cited.append(ev_map[rlow])
			for ev_low, ev_orig in ev_map.items():
				m_res = re.search('/(?:res|\\u227a)/(?:\\d+[-\\u2013]\\d+/)?(\\d+\\.md)$', ev_low)
				if m_res and re.search(f'(?:\\bres|\\u227a)/(?:\\d+[-\\u2013]\\d+/)?{re.escape(m_res.group(1))}\\b', response, re.I) and (ev_orig not in unreread_cited):
					unreread_cited.append(ev_orig)
	return unreread_cited
# 2026-11-21
# "Add read-only answer-check pre-flight validation command to harness CLI":
# https://github.com/dmitry-ai/harness/issues/117
def _authored_nonquote_hrefs(content: str) -> list[str]:
	from .links import HTMLReferences, _bare_urls
	from .source_grounding import markdown_parser
	hrefs: list[str] = []
	quote_depth = 0
	html = HTMLReferences(authored_only=True)
	for block in markdown_parser().parse(content):
		if 'blockquote_open' == block.type:
			quote_depth += 1
		elif 'blockquote_close' == block.type:
			quote_depth = max(0, quote_depth - 1)
		elif 0 == quote_depth:
			if 'html_block' == block.type:
				html.feed(block.content)
			depth = 0
			for token in block.children or []:
				if 'link_open' == token.type:
					depth += 1
					if token.attrGet('href'):
						hrefs.append(token.attrGet('href'))
				elif 'link_close' == token.type:
					depth = max(0, depth - 1)
				elif 'html_inline' == token.type:
					html.feed(token.content)
				elif 'text' == token.type and 0 == depth:
					hrefs.extend(_bare_urls(token.content))
	return [*hrefs, *html.links]
# 2026-11-21
# "Add read-only answer-check pre-flight validation command to harness CLI":
# https://github.com/dmitry-ai/harness/issues/117
def _response_link_issues(root_p: Path, response: str, *, response_path: Path | None = None, scratch_dir: Path | None = None) -> list[str]:
	from urllib.parse import unquote, urldefrag, urlsplit
	# 2026-11-25
	# "Unify chat reply LINK-5 validation via chat_reply_link_issues helper":
	# https://github.com/dmitry-ai/harness/issues/230
	from .links import chat_reply_link_issues, heading_anchors, references
	# 2026-11-26
	# "Ban file:/// links for GitHub repositories and ground tagged GitHub URLs":
	# https://github.com/dmitry-ai/harness/issues/264
	errors: list[str] = list(chat_reply_link_issues(response, root=root_p))
	available_self = set(references(response)[1]) | heading_anchors(response)
	base_dirs = [root_p]
	if None is not response_path and '-' != str(response_path):
		try:
			rp_res = Path(response_path).resolve()
			scr_res = Path(scratch_dir).resolve() if None is not scratch_dir else None
			in_scratch = None is not scr_res and (rp_res == scr_res or rp_res.is_relative_to(scr_res))
			if rp_res.is_relative_to(root_p) and (not in_scratch):
				rp_parent = rp_res.parent
				if rp_parent not in base_dirs:
					base_dirs.append(rp_parent)
		except OSError:
			pass
	for href in dict.fromkeys(_authored_nonquote_hrefs(response)):
		if not href:
			continue
		if href.startswith('#'):
			if unquote(href[1:]) not in available_self:
				errors.append(f'LINK-4: Missing local anchor: {href}')
			continue
		parsed = urlsplit(href)
		windows_path = bool(re.match('^[A-Za-z]:[/\\\\]', href))
		if parsed.scheme and 'file' != parsed.scheme.lower() and (not windows_path):
			if parsed.scheme.lower() in ('http', 'https') and (not parsed.hostname or any((c.isspace() for c in href))):
				errors.append(f'LINK-4: Invalid HTTP URL: {href}')
			continue
		path_text = unquote(urldefrag(href)[0] if windows_path else parsed.path)
		if 'file' == parsed.scheme.lower():
			if parsed.netloc and 'localhost' != parsed.netloc:
				path_text = parsed.netloc + path_text if re.fullmatch('[A-Za-z]:', parsed.netloc) else f'//{parsed.netloc}{path_text}'
			if re.match('^/[A-Za-z]:/', path_text):
				path_text = path_text[1:]
		if not path_text:
			continue
		p_cand = Path(path_text)
		target = None
		if p_cand.is_absolute():
			resolved_c = p_cand.resolve()
			target = resolved_c if resolved_c.exists() else journal.resolve_migrated_step_file(resolved_c)
		else:
			for bdir in base_dirs:
				resolved_c = (bdir / p_cand).resolve()
				if resolved_c.exists():
					target = resolved_c
					break
				mig = journal.resolve_migrated_step_file(resolved_c)
				if mig.exists():
					target = mig
					break
		if None is target or (not target.exists()):
			errors.append(f'LINK-4: Missing local file: {href}')
			continue
		fragment = unquote(parsed.fragment)
		if target.is_dir():
			if fragment:
				errors.append(f'LINK-4: A directory link cannot have a document anchor: {href}')
			continue
		if not fragment:
			continue
		m_line = re.fullmatch('L(\\d+)(?:-L?(\\d+))?', fragment)
		if m_line:
			s_ln = int(m_line.group(1))
			e_ln = int(m_line.group(2) or s_ln)
			try:
				total_ln = max(1, len(target.read_text(encoding='utf-8', errors='replace').splitlines()))
			except OSError:
				total_ln = 0
			if 1 > s_ln or s_ln > e_ln or (0 < total_ln and e_ln > total_ln):
				errors.append(f'LINK-4: Line anchor #{fragment} is out of bounds (1..{total_ln}) for {href}')
		elif target.suffix.lower() in ('.md', '.html', '.htm'):
			try:
				other = target.read_text(encoding='utf-8')
				ids = set(references(other)[1]) | heading_anchors(other)
				if fragment not in ids:
					errors.append(f'LINK-4: Missing cross-file anchor: {href}')
			except (OSError, UnicodeDecodeError) as exc:
				errors.append(f'LINK-4: {target}: {exc}')
		elif '.json' == target.suffix.lower():
			try:
				from .evidence import resolve_pointer
				resolve_pointer(json.loads(target.read_text(encoding='utf-8')), fragment)
			except (OSError, KeyError, ValueError, IndexError, TypeError):
				errors.append(f'LINK-4: Missing JSON pointer: {href}')
	return errors
# 2026-11-21
# "Add read-only answer-check pre-flight validation command to harness CLI":
# https://github.com/dmitry-ai/harness/issues/117
def _scan_child_trace_turn(root_p: Path, eff_conv: str, native: dict) -> dict:
	if native.get('turns'):
		return native['turns'][-1]
	from .platforms.trace_common import init_turn_accumulator, merge_turn_accumulators, parse_tool_args, read_jsonl_objects, record_normalized_tool_effects
	from .shell_audit import extract_issue_actions_from_outputs
	seg = init_turn_accumulator(extra={'turn_id': f'child-{eff_conv}', 'start_step': 0, 'requests': [], 'owned': True, 'issue_actions': []})
	src_raw = str(native.get('source_file') or '').strip()
	src_file = Path(src_raw) if src_raw else None
	if None is not src_file and src_file.is_file():
		try:
			rows = read_jsonl_objects(src_file)
		except (OSError, ValueError):
			rows = []
		# 2026-11-23
		# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
		# https://github.com/dmitry-ai/harness/issues/138
		from .tdd_gate import _BG_TASK_FINISHED_RE, parse_command_outcome
		child_bg: dict[str, dict] = {}
		child_pending_tdd: dict[str, dict] = {}
		# 2026-11-23
		# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
		# https://github.com/dmitry-ai/harness/issues/146
		child_pending_issue: dict[str, tuple[int, str]] = {}
		for pos, row in enumerate(rows):
			if not isinstance(row, dict):
				continue
			step_idx = row.get('step_index') if isinstance(row.get('step_index'), int) else pos
			if 'CHECKPOINT' == row.get('type') or ('event_msg' == row.get('type') and 'context_compacted' == (row.get('payload') or {}).get('type')):
				seg['checkpoint_steps'].append(step_idx)
			# 2026-11-23
			# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
			# https://github.com/dmitry-ai/harness/issues/138
			if row.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and row.get('content'):
				m_fin = _BG_TASK_FINISHED_RE.search(str(row.get('content')))
				if m_fin and m_fin.group(1).strip() in child_bg:
					child_bg[m_fin.group(1).strip()]['outcome'] = parse_command_outcome(m_fin.group(2))
			calls = [c for c in row.get('tool_calls') or [] if isinstance(c, dict)]
			if calls:
				outs = []
				for cand in rows[pos + 1:]:
					if not isinstance(cand, dict):
						continue
					if cand.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
						break
					if 'GENERIC' == cand.get('type') and cand.get('content'):
						c_str = str(cand.get('content'))
						outs.append(c_str[:4000])
						for m_out in re.finditer('file:///+([A-Za-z]:/[^\\s"\\\'<>`]+?/\\.system_generated/steps/\\d+/output\\.txt)', c_str):
							seg['file_reads'].append((step_idx, m_out.group(1).replace('\\', '/')))
				seg['tool_steps'].append(step_idx)
				seg['tool_records'].append({'step': step_idx, 'tools': [c.get('name', '') for c in calls], 'outputs': outs})
				for act_item in extract_issue_actions_from_outputs(outs):
					seg['issue_actions'].append({**act_item, 'step': step_idx})
				for c_idx, call in enumerate(calls):
					raw_args = call.get('args', {})
					args = parse_tool_args(raw_args)
					args_text = json.dumps(args, ensure_ascii=False) if args or isinstance(raw_args, dict) else str(raw_args)
					matched = [outs[c_idx]] if c_idx < len(outs) else outs
					cev = record_normalized_tool_effects(root_p, step_idx, call.get('name', ''), raw_args, args_text, seg, track_turn_steps=True, cmd_outputs=matched)
					if cev and cev.get('outcome', {}).get('background_task_id'):
						child_bg[cev['outcome']['background_task_id']] = cev
			elif 'response_item' == row.get('type'):
				pay = row.get('payload') if isinstance(row.get('payload'), dict) else {}
				if pay.get('type') in ('function_call_output', 'custom_tool_call_output') and None is not pay.get('output'):
					c_id = pay.get('call_id')
					out_val = pay.get('output')
					out_str = out_val if isinstance(out_val, str) else json.dumps(out_val, ensure_ascii=False)
					# 2026-11-23
					# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
					# https://github.com/dmitry-ai/harness/issues/138
					if c_id in child_pending_tdd:
						child_pending_tdd[c_id]['outcome'] = parse_command_outcome(out_str)
					# 2026-11-23
					# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
					# https://github.com/dmitry-ai/harness/issues/146
					if c_id in child_pending_issue:
						from .issue_first_gate import build_issue_action_events
						ci_step, ci_cmd = child_pending_issue.pop(c_id)
						seg['issue_first_events'].extend(build_issue_action_events(ci_step, ci_cmd, [out_str]))
				elif pay.get('type') in ('function_call', 'custom_tool_call'):
					seg['tool_steps'].append(step_idx)
					raw_in = pay.get('arguments', pay.get('input', {}))
					raw_cmd = raw_in if isinstance(raw_in, str) else json.dumps(raw_in, ensure_ascii=False)
					p_name = str(pay.get('name') or '')
					seg['tool_records'].append({'step': step_idx, 'tools': [p_name], 'outputs': []})
					cev = record_normalized_tool_effects(root_p, step_idx, p_name, raw_in, raw_cmd, seg, track_turn_steps=True)
					# 2026-11-23
					# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
					# https://github.com/dmitry-ai/harness/issues/138
					if cev and pay.get('call_id'):
						child_pending_tdd[pay['call_id']] = cev
					# 2026-11-23
					# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
					# https://github.com/dmitry-ai/harness/issues/146
					if pay.get('call_id') and ('exec' == p_name or p_name.endswith(('exec_command', 'run_command'))):
						from .issue_first_gate import is_df_github_issue_command
						cp_args = parse_tool_args(raw_in)
						ceff_cmd = str(cp_args.get('CommandLine') or cp_args.get('cmd') or cp_args.get('command') or raw_cmd)
						if is_df_github_issue_command(ceff_cmd):
							child_pending_issue[pay['call_id']] = (step_idx, ceff_cmd)
	return merge_turn_accumulators([seg], allow_step_output_recovery=True)
# 2026-11-21
# "Add read-only answer-check pre-flight validation command to harness CLI":
# https://github.com/dmitry-ai/harness/issues/117
# 2026-11-24
# "Add blocked-report mode to answer-prepare for pre-finalize workflow blockers":
# https://github.com/dmitry-ai/harness/issues/213
def check_answer(root, response, conversation=None, *, response_path=None, platform=None, backend=None, journal_directory=None, blocked_report=False):
	if not isinstance(response, str) or not response.strip():
		raise ValueError('An exact nonempty UTF-8 candidate response is required')
	from check_markdown_slop import markdown_slop_issues
	from .causal_checks import unsupported_probability_claims
	from .path_registry import canonicalize_root_dir, project_paths
	from .source_grounding import read_only_grounding
	root_p = canonicalize_root_dir(root)
	pp = project_paths(root_p, exact_root=True)
	sha = _hash(response.encode('utf-8'))
	eff_plat = platform_name(platform)
	eff_conv = conversation or (os.environ.get('CODEX_THREAD_ID') if 'codex' == eff_plat else None)
	with read_only_grounding():
		native = None
		turn_obj = None
		value_obj = None
		role = 'standalone'
		turn_key = None
		if eff_conv:
			native = _native(root_p, eff_conv, platform=eff_plat, backend=backend)
			if native['primary']:
				role = 'primary'
				turn_obj = _active(native)
				_, value_obj = _state(root_p, native, turn_obj, journal_directory=journal_directory, strict_journal=True)
				turn_key = value_obj['key']
			else:
				role = 'child'
				turn_obj = _scan_child_trace_turn(root_p, eff_conv, native)
				turn_key = _key(native, turn_obj)
				value_obj = {'key': turn_key, 'platform': native['platform'], 'conversation_id': native['conversation_id'], 'exec5_check': _exec5_status(turn_obj, root_p, turn_key), 'http_fetch_check': _http_fetch_status(turn_obj, root_p, turn_key), 'compaction_check': _compaction_status(root_p, turn_key, turn_obj), 'delegation_check': _delegation_status(root_p, turn_obj)}
		else:
			turn_obj = {'turn_id': 'standalone', 'start_step': 0, 'requests': [], 'touched_files': [], 'issue_actions': [], 'exec5_violations': [], 'http_fetch_violations': [], 'compaction': {}, 'delegation': {}}
			value_obj = {'key': None, 'exec5_check': {'verified': True, 'violations': []}, 'http_fetch_check': {'verified': True, 'violations': []}, 'compaction_check': {'verified': True, 'occurred': False, 'evicted_unreread_files': [], 'unreread_analysis_sources': []}, 'delegation_check': {'verified': True, 'aa_partial_read_violations': []}}
		doc4_errs = markdown_slop_issues(response)
		link_errs = _response_link_issues(root_p, response, response_path=response_path, scratch_dir=pp.scratch_dir)
		prob_errs = [f'DOC-2: Unsupported causal probability basis: {item}' for item in unsupported_probability_claims(response)]
		requests_list = list(turn_obj.get('requests') or []) if 'primary' == role else []
		source_errs = response_source_and_kb_issues(root_p, response, requests_list, touched_files=turn_obj.get('touched_files'))
		lang_errs = _intermediate_or_language_issues(requests_list, response)
		exec5_chk = value_obj['exec5_check']
		http_chk = value_obj['http_fetch_check']
		comp_chk = value_obj['compaction_check']
		evicted_cited = _find_evicted_cited_files(root_p, pp, turn_key, comp_chk, response) if role in ('primary', 'child') else []
		del_chk = value_obj['delegation_check']
		# 2026-11-23
		# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
		# https://github.com/dmitry-ai/harness/issues/146
		issue_first_chk = _issue_first_status(root_p, turn_obj) if role in ('primary', 'child') else {'verified': True, 'repos': {}, 'violations': []}
		lifecycle_chk = _code_and_issue_lifecycle_status(root_p, turn_obj, value_obj if 'primary' == role else None, response=response)
		# 2026-11-23
		# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
		# https://github.com/dmitry-ai/harness/issues/138
		tdd_chk = _tdd_status(root_p, turn_obj) if role in ('primary', 'child') else {'verified': True, 'scopes': {}, 'violations': []}
		# 2026-11-24
		# "Add blocked-report mode to answer-prepare for pre-finalize workflow blockers":
		# https://github.com/dmitry-ai/harness/issues/213
		from .blocked_report import evaluate_check_workflow_errors
		wf_errs = evaluate_check_workflow_errors(root_p, pp, role, response, requests_list, turn_obj, value_obj, del_chk, blocked_report=bool(blocked_report), journal_directory=journal_directory, factual_kb_fn=_factual_kb_note_issues, is_deliv_fn=_is_client_deliverable_path, dir_fn=_directory)
		# 2026-11-23
		# "Extract PreToolUse and completion gates into priority plugin registry":
		# https://github.com/dmitry-ai/harness/issues/167
		from .gates import run_answer_gates
		# 2026-11-25
		# "Add PreToolUse canary probe to runtime snapshot validation and turn hook-crash audit":
		# https://github.com/dmitry-ai/harness/issues/251
		all_issues, checks = run_answer_gates({'role': role, 'blocked_report': bool(blocked_report), 'doc4_errs': doc4_errs, 'link_errs': link_errs, 'prob_errs': prob_errs, 'source_errs': source_errs, 'lang_errs': lang_errs, 'exec5_chk': exec5_chk, 'hook_crash_chk': _hook_crash_status(root_p, native, turn_obj, value_obj, response), 'http_chk': http_chk, 'comp_chk': comp_chk, 'evicted_cited': evicted_cited, 'del_chk': del_chk, 'issue_first_chk': issue_first_chk, 'lifecycle_chk': lifecycle_chk, 'tdd_chk': tdd_chk, 'wf_errs': wf_errs})
		return {'valid': not all_issues, 'read_only': True, 'role': role, 'turn_key': turn_key, 'response_sha256': sha, 'issue_count': len(all_issues), 'issues': all_issues, 'checks': checks}
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-13
# "Extract AnswerPreparationRunner class from prepare in completion.py, add typed gate_id readiness tracking, deduplicate native trace loading, and unify resolve_journal_dir":
# https://github.com/dmitry-ai/harness/issues/57
# 2026-11-24
# "Add blocked-report mode to answer-prepare for pre-finalize workflow blockers":
# https://github.com/dmitry-ai/harness/issues/213
def _prepare_once(root, response, conversation=None, *, platform=None, backend=None, watch=False, watch_dir=None, journal_directory=None, blocked_report=False):
	if not isinstance(response, str) or not response.strip():
		raise ValueError('An exact nonempty UTF-8 final response is required')
	# 2026-10-19
	# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
	# https://github.com/dmitry-ai/harness/issues/12
	from .causal_checks import unsupported_probability_claims
	issues = unsupported_probability_claims(response)
	if issues:
		raise ValueError('Unsupported causal probability basis: ' + '; '.join(issues))
	result = begin(root, conversation, platform=platform, backend=backend, watch=watch, watch_dir=watch_dir, journal_directory=journal_directory)
	if not result['journal_required']:
		raise ValueError('A child executor cannot prepare the primary user journal')
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import canonicalize_root_dir
	root_p = canonicalize_root_dir(root)
	with locked(_turn_lock(root_p, result['turn_key'])):
		native = _native(root_p, conversation, platform=platform, backend=backend)
		turn = _active(native)
		if None is turn or _key(native, turn) != result['turn_key'] or _hash(_json(turn['requests'])) != result['native_requests_sha256']:
			raise ValueError('The active native turn changed during preparation; no answer was recorded')
		return AnswerPreparationRunner(root_p, response, result, native, turn, blocked_report=blocked_report).run()
# 2026-11-24
# "Add deterministic reactive wait primitive for transient repository and journal contention":
# https://github.com/dmitry-ai/harness/issues/199
# 2026-11-24
# "Add blocked-report mode to answer-prepare for pre-finalize workflow blockers":
# https://github.com/dmitry-ai/harness/issues/213
def prepare(root, response, conversation=None, *, platform=None, backend=None, watch=False, watch_dir=None, journal_directory=None, wait_timeout: float=0.0, wait_poll: float=1.0, blocked_report: bool=False):
	from .repo_wait import run_with_transient_wait
	return run_with_transient_wait(Path(root), lambda: _prepare_once(root, response, conversation, platform=platform, backend=backend, watch=watch, watch_dir=watch_dir, journal_directory=journal_directory, blocked_report=blocked_report), wait_timeout=wait_timeout, poll_interval=wait_poll)
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def _conflict(root, path, value, native, turn, response, detail, *, retryable=False):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import canonicalize_root_dir
	root_p = canonicalize_root_dir(root)
	payload = response.encode('utf-8')
	evidence = write_immutable_bytes(_folder(root_p) / 'conflicts' / (value['key'] + '-' + _hash(payload) + '.txt'), payload, diff_error='Immutable native conflict evidence changed')
	if _recorded(value):
		value['journal_record'] = _recorded(value)
	# 2026-11-03
	# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
	# https://github.com/dmitry-ai/harness/issues/41
	prior_verified = value.get('delivery') if (value.get('delivery') or {}).get('verified') else value.get('prior_verified_delivery')
	if prior_verified:
		value['prior_verified_delivery'] = deepcopy(prior_verified)
	rel_evidence = evidence.relative_to(root_p).as_posix() if evidence.is_relative_to(root_p) else str(evidence)
	value['status'] = 'conflict'
	value['delivery'] = {'verified': False, 'native_response_sha256': _hash(payload), 'source_file': native['source_file'], 'final_step': turn['final_step'], 'native_requests': turn['requests'], 'conflict_evidence': rel_evidence, 'detail': detail, 'retryable': retryable}
	_persist(path, value)
	r = {'turn_key': value['key'], 'status': 'conflict', 'detail': detail, 'evidence': rel_evidence, 'retryable': retryable}
	return r
# 2026-10-30
# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
# https://github.com/dmitry-ai/harness/issues/21
# 2026-11-14
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
_strip_local_file_scheme = journal.strip_local_file_scheme
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-11-26
# "Exempt service finalization calls from PreToolUse TDD gate and add journal-sync --all-open":
# https://github.com/dmitry-ai/harness/issues/256
def sync(root, conversation=None, *, platform=None, backend=None, from_step=0, journal_directory=None, adopt_conflict=False, all_open=False, _preloaded_native=None):
	return sync_all_open(root, journal_directory=journal_directory, adopt_conflict=adopt_conflict, from_step=from_step, folder_fn=_folder, dir_fn=_directory, read_fn=_read, sync_fn=sync) if all_open else TurnJournalReconciler(root, conversation, platform=platform, backend=backend, from_step=from_step, journal_directory=journal_directory, adopt_conflict=adopt_conflict, preloaded_native=_preloaded_native).run()
# 2026-11-04
# "Scope research questions to active turn, distinguish factual KB notes from hypotheses, and reconcile unprepared chat deliveries":
# https://github.com/dmitry-ai/harness/issues/44
def reconcile_unprepared_delivery(root, conversation=None, *, platform=None, backend=None, from_step=0, journal_directory=None):
	return sync(root, conversation, platform=platform, backend=backend, from_step=from_step, journal_directory=journal_directory, adopt_conflict=True)
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-11-14
# "Unify declarative CLI routers, scratch-verified --consume-input/stdin loading, and read-back mutations in cli_common.py":
# https://github.com/dmitry-ai/harness/issues/69
# 2026-11-20
# "Remove retired journal-watch subsystem and prune delivered checkpoint recovery directories":
# https://github.com/dmitry-ai/harness/issues/105
def add_parser_arguments(parser, command):
	from .cli_common import add_arg_specs
	specs = [('project', {'type': Path}), ('--conversation', {'help': 'Actual current native conversation UUID; Codex can use CODEX_THREAD_ID'})]
	if 'recover-turn-violation' == command:
		specs.append(('--reason', {'help': 'Audit note for retrospective turn violation recovery'}))
	# 2026-11-22
	# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
	# https://github.com/dmitry-ai/harness/issues/123
	if 'similar-project-exempt' == command:
		specs.extend((('--peer', {'required': True, 'help': 'Declared similar project root or GitHub owner/repo slug'}), ('--reason', {'required': True, 'help': 'Technical justification (>= 30 chars) why peer changes do not apply'})))
	# 2026-11-23
	# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
	# https://github.com/dmitry-ai/harness/issues/138
	if 'ratchet-ok' == command:
		specs.extend((('--file', {'required': True, 'help': 'Relative path or filename of the tracked test file whose expectation is intentionally changing'}), ('--reason', {'required': True, 'help': 'Audited justification (>= 30 chars) citing the requirement/user decision behind the test change'})))
	# 2026-11-23
	# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
	# https://github.com/dmitry-ai/harness/issues/146
	if command not in ('recover-checkpoint', 'recover-turn-violation', 'similar-project-exempt', 'ratchet-ok', 'tdd-check', 'issue-first-check'):
		specs.append(('--journal', {'type': Path, 'help': 'User-selected journal; otherwise preserve the turn binding or use \ua66e/1 - Analysis'}))
	if command in ('turn-begin', 'answer-prepare'):
		specs.append(('--no-watch', {'action': 'store_true', 'help': 'Compatibility option; all completion operations are foreground-only'}))
	# 2026-11-21
	# "Add idempotent Antigravity PreInvocation turn-begin hook and dry-run flag":
	# https://github.com/dmitry-ai/harness/issues/116
	if 'turn-begin' == command:
		specs.append(('--dry-run', {'action': 'store_true', 'help': 'Validate native turn ownership and hygiene checks without writing receipts or upgrading journals'}))
	# 2026-11-22
	# "Auto-name Antigravity conversations from project journal step numbers":
	# https://github.com/dmitry-ai/harness/issues/120
	if 'sync-conversation-title' == command:
		specs.append(('--dry-run', {'action': 'store_true', 'help': 'Compute target journal-numbered conversation title without calling Antigravity UpdateConversationAnnotations'}))
	# 2026-11-21
	# "Offload bulky compaction arrays to recovery index and add recover-checkpoint dry-run mode":
	# https://github.com/dmitry-ai/harness/issues/119
	if 'recover-checkpoint' == command:
		specs.append(('--dry-run', {'action': 'store_true', 'help': 'Inspect read-only pre-checkpoint file SHA-256/line index and step summary without writing receipts or bypassing COMPACT-1'}))
	# 2026-11-21
	# "Add read-only answer-check pre-flight validation command to harness CLI":
	# https://github.com/dmitry-ai/harness/issues/117
	# 2026-11-24
	# "Add blocked-report mode to answer-prepare for pre-finalize workflow blockers":
	# https://github.com/dmitry-ai/harness/issues/213
	if 'answer-check' == command:
		specs.extend((('--response-file', {'type': Path, 'required': True, 'help': 'Candidate UTF-8 response file to validate, or - for stdin'}), ('--expected-sha256', {'help': 'Optional expected SHA-256 hex digest of response file'}), ('--blocked-report', {'action': 'store_true', 'help': 'Validate as a pre-finalize blocker report requiring continuation.md and forbidding H-*/M-* claims'})))
	# 2026-11-20
	# "Remove retired journal-watch subsystem and prune delivered checkpoint recovery directories":
	# https://github.com/dmitry-ai/harness/issues/105
	# 2026-11-24
	# "Add deterministic reactive wait primitive for transient repository and journal contention":
	# https://github.com/dmitry-ai/harness/issues/199
	# 2026-11-24
	# "Add blocked-report mode to answer-prepare for pre-finalize workflow blockers":
	# https://github.com/dmitry-ai/harness/issues/213
	if 'answer-prepare' == command:
		specs.extend((('--response-file', {'type': Path, 'required': True, 'help': 'Exact UTF-8 final response, or - for stdin'}), ('--consume-input', {'action': 'store_true'}), ('--expected-sha256', {'help': 'Optional expected SHA-256 hex digest of response file'}), ('--wait-timeout', {'type': float, 'default': 180.0, 'help': 'Seconds to wait reactively on transient repo/journal contention (default: 180)'}), ('--blocked-report', {'action': 'store_true', 'help': 'Record a pre-finalize blocker report in the journal without closing workflow review/finalize gates'})))
	if command in ('journal-sync', 'reconcile-unprepared-delivery'):
		specs.append(('--from-step', {'type': int, 'default': 0}))
	if 'journal-sync' == command:
		# 2026-11-26
		# "Exempt service finalization calls from PreToolUse TDD gate and add journal-sync --all-open":
		# https://github.com/dmitry-ai/harness/issues/256
		specs.extend((('--adopt-conflict', {'action': 'store_true', 'help': 'Adopt turns that experienced preparation or admission failures into the journal as recovered deliveries'}), ('--all-open', {'action': 'store_true', 'help': 'Reconcile all eligible idle open turn reservations across conversations in this project'})))
	add_arg_specs(parser, specs)
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def execute(args):
	if 'turn-begin' == args.command:
		# 2026-11-21
		# "Add idempotent Antigravity PreInvocation turn-begin hook and dry-run flag":
		# https://github.com/dmitry-ai/harness/issues/116
		r = begin(args.project, args.conversation, watch=not args.no_watch, journal_directory=args.journal, dry_run=bool(getattr(args, 'dry_run', False)))
	elif 'recover-checkpoint' == args.command:
		# 2026-11-21
		# "Offload bulky compaction arrays to recovery index and add recover-checkpoint dry-run mode":
		# https://github.com/dmitry-ai/harness/issues/119
		r = recover_checkpoint(args.project, args.conversation, dry_run=bool(getattr(args, 'dry_run', False)))
	# 2026-11-02
	# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
	# https://github.com/dmitry-ai/harness/issues/36
	elif 'recover-turn-violation' == args.command:
		r = recover_turn_violation(args.project, args.conversation, reason=args.reason)
	# 2026-11-22
	# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
	# https://github.com/dmitry-ai/harness/issues/123
	elif 'similar-project-exempt' == args.command:
		r = similar_project_exempt(args.project, args.peer, args.reason, args.conversation)
	# 2026-11-23
	# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
	# https://github.com/dmitry-ai/harness/issues/138
	elif 'ratchet-ok' == args.command:
		r = ratchet_ok(args.project, args.file, args.reason, args.conversation)
	elif 'tdd-check' == args.command:
		r = tdd_check_turn(args.project, args.conversation)
	# 2026-11-23
	# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
	# https://github.com/dmitry-ai/harness/issues/146
	elif 'issue-first-check' == args.command:
		r = issue_first_check_turn(args.project, args.conversation)
	# 2026-11-21
	# "Add read-only answer-check pre-flight validation command to harness CLI":
	# https://github.com/dmitry-ai/harness/issues/117
	# 2026-11-24
	# "Add blocked-report mode to answer-prepare for pre-finalize workflow blockers":
	# https://github.com/dmitry-ai/harness/issues/213
	elif 'answer-check' == args.command:
		from .cli_common import load_operation_input
		payload = load_operation_input(args, args.response_file)
		r = check_answer(args.project, payload.decode('utf-8'), args.conversation, response_path=args.response_file, journal_directory=args.journal, blocked_report=bool(getattr(args, 'blocked_report', False)))
	elif 'answer-prepare' == args.command:
		# 2026-11-14
		# "Unify declarative CLI routers, scratch-verified --consume-input/stdin loading, and read-back mutations in cli_common.py":
		# https://github.com/dmitry-ai/harness/issues/69
		# 2026-11-24
		# "Add blocked-report mode to answer-prepare for pre-finalize workflow blockers":
		# https://github.com/dmitry-ai/harness/issues/213
		from .cli_common import consume_scratch_input, load_operation_input
		payload = load_operation_input(args, args.response_file)
		result = prepare(args.project, payload.decode('utf-8'), args.conversation, watch=not args.no_watch, journal_directory=args.journal, wait_timeout=float(getattr(args, 'wait_timeout', 180.0)), blocked_report=bool(getattr(args, 'blocked_report', False)))
		r = consume_scratch_input(args, args.response_file, payload, result)
	# 2026-11-04
	# "Scope research questions to active turn, distinguish factual KB notes from hypotheses, and reconcile unprepared chat deliveries":
	# https://github.com/dmitry-ai/harness/issues/44
	elif 'reconcile-unprepared-delivery' == args.command:
		r = reconcile_unprepared_delivery(args.project, args.conversation, from_step=args.from_step, journal_directory=args.journal)
	elif 'journal-sync' == args.command:
		# 2026-11-26
		# "Exempt service finalization calls from PreToolUse TDD gate and add journal-sync --all-open":
		# https://github.com/dmitry-ai/harness/issues/256
		r = sync(args.project, args.conversation, from_step=args.from_step, journal_directory=args.journal, adopt_conflict=getattr(args, 'adopt_conflict', False), all_open=bool(getattr(args, 'all_open', False)))
	# 2026-11-22
	# "Auto-name Antigravity conversations from project journal step numbers":
	# https://github.com/dmitry-ai/harness/issues/120
	elif 'sync-conversation-title' == args.command:
		r = sync_conversation_title(args.project, args.conversation, journal_directory=args.journal, dry_run=bool(getattr(args, 'dry_run', False)))
	else:
		raise ValueError('Unknown completion operation')
	return r
