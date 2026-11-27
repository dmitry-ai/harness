# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.completion_core import dfh_hash, dfh_journal_dir, dfh_journal_lock, dfh_native_scan, dfh_now, dfh_persist, dfh_read_meta, dfh_recorded, dfh_sync_antigravity_conversation_title, dfh_turn_key, dfh_turn_lock, dfh_turns_folder
from Df.Harness.lib.completion_record import dfh_record
from Df.Harness.lib.completion_state import dfh_conflict, dfh_load_turn_state
from Df.Harness.lib.journal_core import dfh_norm_journal_response_text, dfh_resolve_migrated_step_file
from Df.Harness.lib.journal_records import dfh_matching_group_response
from Df.Harness.lib.journal_reservations import dfh_release_turn_steps
from Df.Harness.lib.journal_sync_ops import dfh_resolve_sync_provenance
from Df.Harness.lib.journal_upgrade import dfh_ensure_project_journal_upgraded
from Df.Harness.lib.path_resolve import dfh_load_registry
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir
from Df.Harness.lib.storage import dfh_locked
import os
import shutil
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class JournalReconciler:
	# @used-by :func:`Df.Harness.lib.completion_commands.dfh_sync()`
	# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_open_turn_reconciles_safely_and_trims_stale_reservation()`
	# @used-by :meth:`test_turn_completion.TurnJournalReconcilerTests.test_compacted_status5_steps_single_pass_authorize_and_group_helpers()`
	def __init__(self, root: str | Path, conversation: str | None=None, *, platform: str | None=None, backend: Any=None, from_step: int=0, journal_directory: Any=None, adopt_conflict: bool=False, preloaded_native: dict | None=None, _ops: dict[str, Any] | None=None) -> None:
		if int is not type(from_step) or 0 > from_step:
			raise ValueError('Native from-step must be a nonnegative integer')
		self.__ops = _ops or {}
		self.root = dfh_canonicalize_root_dir(root, dfh_load_registry())
		native_fn = self.__ops.get('native') or (lambda r, c, **kw: dfh_native_scan(r, c, ops=self.__ops, **kw))
		self.native = preloaded_native if None is not preloaded_native else native_fn(self.root, conversation, platform=platform, backend=backend)
		self.from_step = from_step
		self.journal_directory = journal_directory
		self.adopt_conflict = adopt_conflict
	# @used-by :meth:`JournalReconciler.__complete_turn_delivery()`
	def __build_delivery(self, value: dict, turn: dict, recorded: dict, sha: str, provenance: str, preparation_verified: bool) -> dict[str, Any]:
		now_fn = self.__ops.get('now') or dfh_now
		delivery: dict[str, Any] = {**recorded, 'verified': True, 'source_file': self.native['source_file'], 'final_step': turn['final_step'], 'completion_step': turn['completion_step'], 'native_response_sha256': sha, 'completion_provenance': provenance, 'preparation_verified': preparation_verified, 'exec5_check': value['exec5_check']}
		previous_delivery = value.get('delivery') or {}
		prior_verified = value.get('prior_verified_delivery') or {}
		if 'delivered' == value['status'] and all((previous_delivery.get(name) == expected for name, expected in delivery.items())):
			r = previous_delivery
		elif prior_verified and all((prior_verified.get(name) == expected for name, expected in delivery.items() if 'verified_at' != name)):
			r = prior_verified
		else:
			delivery['verified_at'] = now_fn()
			r = delivery
		return r
	# @used-by :meth:`JournalReconciler.__complete_turn_delivery()`
	def __cleanup_adopted_conflict(self, value: dict) -> None:
		value.pop('admission_failure', None)
		if (value.get('delivery') or {}).get('conflict_evidence'):
			raw_ce = Path(value['delivery']['conflict_evidence'])
			conflict_file = raw_ce if raw_ce.is_absolute() else (self.root / raw_ce)
			if conflict_file.is_file():
				try:
					conflict_file.unlink()
				except OSError:
					pass
	# @used-by :meth:`JournalReconciler.__try_record_turn()`
	def __complete_turn_delivery(self, path: Path, value: dict, turn: dict, recorded: dict, sha: str, admission_check: dict) -> dict[str, Any]:
		if self.adopt_conflict:
			self.__cleanup_adopted_conflict(value)
		if not dfh_recorded(value):
			value['recovered_after_delivery'] = not bool(value['prepared']) and (not recorded['reused_complete_journal_group'])
		if self.adopt_conflict:
			value['recovered_after_delivery'] = True
		provenance = dfh_resolve_sync_provenance(value, adopt_conflict=self.adopt_conflict)
		prep_verified = bool(value['prepared']) and value.get('readiness_check', {}).get('verified', True) and (not self.adopt_conflict)
		value['journal_record'] = recorded
		value['delivery'] = self.__build_delivery(value, turn, recorded, sha, provenance, prep_verified)
		value.pop('prior_verified_delivery', None)
		value.pop('reserved_journal_steps', None)
		value['status'] = 'delivered'
		if self.adopt_conflict:
			value['readiness_check'] = {'verified': True, 'checked_at': (self.__ops.get('now') or dfh_now)(), 'detail': 'Adopted into journal via --adopt-conflict'}
		(self.__ops.get('persist') or (lambda p, v: dfh_persist(p, v, ops=self.__ops)))(path, value)
		dfh_release_turn_steps((self.__ops.get('directory') or dfh_journal_dir)(self.root, value['journal']), value['key'], request_ids=[req['id'] for req in turn['requests']])
		self.__prune_delivered_checkpoint_recovery(value['key'])
		return {'turn_key': value['key'], 'status': 'delivered', 'delivery_verified': True, 'journal_steps': recorded['journal_steps'], 'completion_provenance': provenance, 'preparation_verified': prep_verified, 'recovered_after_delivery': value['recovered_after_delivery'], 'exec5_check': value['exec5_check'], 'admission_verification': admission_check}
	# @used-by :meth:`JournalReconciler.__complete_turn_delivery()`
	def __prune_delivered_checkpoint_recovery(self, key: str) -> None:
		folder = (self.__ops.get('folder') or dfh_turns_folder)(self.root)
		rec_dir = folder / f'{key}-recovery'
		if rec_dir.is_dir() and (not os.path.islink(rec_dir)):
			shutil.rmtree(rec_dir, ignore_errors=True)
		rec_file = folder / f'{key}-checkpoint-recovery.json'
		if rec_file.is_file() and (not os.path.islink(rec_file)):
			try:
				rec_file.unlink()
			except OSError:
				pass
	# @used-by :meth:`JournalReconciler.run()`
	def __reconcile_turn(self, turn: dict) -> dict[str, Any]:
		state_fn = self.__ops.get('state') or (lambda r, n, t, **kw: dfh_load_turn_state(r, n, t, ops=self.__ops, **kw))
		path, value = state_fn(self.root, self.native, turn, recovered=True, allow_extended=True, journal_directory=self.journal_directory)
		response = turn['response']
		sha = (self.__ops.get('hash') or dfh_hash)(response.encode('utf-8'))
		if 'handed_off' == value.get('status'):
			r = {'turn_key': value['key'], 'status': 'handed_off', 'handed_off_to': value.get('handed_off_to'), 'delivery_verified': False, 'journal_steps': [], 'recovered_after_delivery': False}
		elif value.get('uncovered_requests') and (not self.adopt_conflict):
			r = self.__record_conflict(path, value, turn, response, 'Prepared answer does not cover newly received native requests')
		elif not dfh_recorded(value) and (value.get('admission_failure') or False is value.get('readiness_check', {}).get('verified')) and (not self.adopt_conflict):
			r = self.__record_conflict(path, value, turn, response, 'A prior preparation/admission gate failed; recovery cannot grant publication approval')
		else:
			r = self.__try_record_turn(path, value, turn, response, sha)
		return r
	# @used-by :meth:`JournalReconciler.__reconcile_turn()`
	# @used-by :meth:`JournalReconciler.__try_record_turn()`
	def __record_conflict(self, path: Path, value: dict, turn: dict, response: str, detail: str, *, retryable: bool=False) -> dict[str, Any]:
		conflict_fn = self.__ops.get('conflict') or (lambda r_p, p, v, n, t, resp, d, **kw: dfh_conflict(r_p, p, v, n, t, resp, d, ops=self.__ops, **kw))
		return conflict_fn(self.root, path, value, self.native, turn, response, detail, retryable=retryable)
	# @used-by :meth:`JournalReconciler.__try_record_turn()`
	def __resolve_effective_response(self, value: dict, turn: dict, response: str, sha: str) -> tuple[str, str | None]:
		effective_response, conflict_detail = (response, None)
		dir_fn = self.__ops.get('directory') or dfh_journal_dir
		if not value['prepared']:
			matched = dfh_matching_group_response(dir_fn(self.root, value['journal']), [req['id'] for req in turn['requests']], response)
			if None is not matched:
				effective_response = matched
		elif value['prepared']['response_sha256'] != sha:
			raw_prep = value['prepared'].get('response_file') or ''
			prep_file = dfh_resolve_migrated_step_file(raw_prep) if raw_prep else Path()
			prep_text = prep_file.read_bytes().decode('utf-8') if prep_file.is_file() else ''
			if prep_text and dfh_norm_journal_response_text(prep_text) == dfh_norm_journal_response_text(response):
				effective_response = prep_text
			elif not self.adopt_conflict:
				conflict_detail = 'Prepared and delivered response bytes differ'
		return (effective_response, conflict_detail)
	# @used-by :meth:`JournalReconciler.run()`
	def __sync_delivered_title(self, results: list[dict]) -> None:
		if any(('delivered' == item.get('status') for item in results)):
			j_hint = self.journal_directory
			if None is j_hint:
				folder = (self.__ops.get('folder') or dfh_turns_folder)(self.root)
				read_fn = self.__ops.get('read') or dfh_read_meta
				for item in reversed(results):
					st_p = folder / (item['turn_key'] + '.json')
					if st_p.is_file():
						try:
							j_hint = read_fn(st_p).get('journal')
							if j_hint:
								break
						except (OSError, ValueError):
							pass
			dfh_sync_antigravity_conversation_title(self.root, self.native, j_hint, ops=self.__ops)
	# @used-by :meth:`JournalReconciler.__reconcile_turn()`
	def __try_record_turn(self, path: Path, value: dict, turn: dict, response: str, sha: str) -> dict[str, Any]:
		record_fn = self.__ops.get('record') or (lambda r_p, n, t, resp, d, **kw: dfh_record(r_p, n, t, resp, d, ops=self.__ops, **kw))
		conflict_res, recorded, admission_check = (None, None, None)
		try:
			eff_resp, conflict_detail = self.__resolve_effective_response(value, turn, response, sha)
			if None is not conflict_detail:
				conflict_res = self.__record_conflict(path, value, turn, response, conflict_detail)
			else:
				recorded, admission_check = record_fn(self.root, self.native, turn, eff_resp, value['journal'], existing=dfh_recorded(value), purpose='observation')
		except (OSError, ValueError) as exc:
			conflict_res = self.__record_conflict(path, value, turn, response, str(exc), retryable=isinstance(exc, OSError) and (not isinstance(exc, FileNotFoundError)))
		if None is not conflict_res:
			r = conflict_res
		elif 'legacy_proof_gap' == admission_check['status'] and value['status'] in ('delivered', 'conflict'):
			r = {'turn_key': value['key'], 'status': value['status'], 'delivery_verified': bool(value.get('delivery', {}).get('verified')), 'journal_steps': recorded['journal_steps'], 'completion_provenance': value.get('delivery', {}).get('completion_provenance'), 'preparation_verified': value.get('delivery', {}).get('preparation_verified', False), 'recovered_after_delivery': value['recovered_after_delivery'], 'exec5_check': value['exec5_check'], 'admission_verification': admission_check}
		else:
			r = self.__complete_turn_delivery(path, value, turn, recorded, sha, admission_check)
		return r
	# @used-by :func:`Df.Harness.lib.completion_commands.dfh_sync()`
	# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_open_turn_reconciles_safely_and_trims_stale_reservation()`
	# @used-by :meth:`test_turn_completion.TurnJournalReconcilerTests.test_compacted_status5_steps_single_pass_authorize_and_group_helpers()`
	def run(self) -> dict[str, Any]:
		if not self.native['primary']:
			raise ValueError('A child executor has no primary user journal to synchronize')
		if not any((turn['owned'] for turn in self.native['turns'])):
			raise ValueError('Native conversation has no user turns owned by this project')
		dfh_ensure_project_journal_upgraded(self.root, selected=self.journal_directory)
		eligible = [turn for turn in self.native['turns'] if turn['owned'] and turn['completed'] and (not turn['aborted']) and turn['start_step'] >= self.from_step]
		if not eligible:
			r = {'valid': True, 'conversation_id': self.native['conversation_id'], 'source_file': self.native['source_file'], 'turns': [], 'pending_native_turn': self.native['active_turn_id'], 'private_reasoning_retained': False}
		else:
			results: list[dict] = []
			lock_fn = self.__ops.get('locked') or dfh_locked
			key_fn = self.__ops.get('key') or dfh_turn_key
			with lock_fn(dfh_journal_lock(self.root, ops=self.__ops)):
				for turn in eligible:
					with lock_fn(dfh_turn_lock(self.root, key_fn(self.native, turn), ops=self.__ops)):
						results.append(self.__reconcile_turn(turn))
			self.__sync_delivered_title(results)
			r = {'valid': not any(('conflict' == item['status'] for item in results)), 'conversation_id': self.native['conversation_id'], 'source_file': self.native['source_file'], 'turns': results, 'retryable': any((item.get('retryable') for item in results)), 'pending_native_turn': self.native['active_turn_id'], 'private_reasoning_retained': False}
		return r