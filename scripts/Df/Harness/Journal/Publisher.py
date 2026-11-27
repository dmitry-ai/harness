# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.journal_core import TURN_RESERVATIONS_FILE, dfh_digest, dfh_journal_pair_dirs, dfh_same_journal_identity, dfh_state_dir, dfh_step_file
from Df.Harness.lib.journal_integrity_ops import dfh_prune_overlapping_reservations
from Df.Harness.lib.journal_records import dfh_get_existing_step_ids, dfh_publish_step, dfh_validate_payload
from Df.Harness.lib.journal_reservations import dfh_read_turn_reservations, dfh_reserved_step_ids, dfh_write_turn_reservations
from Df.Harness.lib.storage import dfh_create_bytes, dfh_locked, dfh_replace_bytes
import json
import re
import uuid
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class Publisher:
	# @used-by :func:`Df.Harness.lib.completion_record._commit_or_verify_journal_group()`
	# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
	# @used-by :func:`agent_tools.journal.record_answer()`
	def __init__(self, directory: str | Path, requests: list[str], response: str, turn: str, request_ids: list[str] | None=None, *, adopt_steps: list[int] | None=None, admission: Any=None, admission_roots: Any=None, allow_reprepare: bool=False, reserved_turn_key: str | None=None, ops: dict[str, Any] | None=None) -> None:
		self.__directory = directory
		self.__requests = requests
		self.__response = response
		self.__turn = turn
		self.__request_ids = request_ids
		self.__adopt_steps = adopt_steps
		self.__admission = admission
		self.__admission_roots = admission_roots
		self.__allow_reprepare = allow_reprepare
		self.__reserved_turn_key = reserved_turn_key
		self.__ops = ops or {}
	# @used-by :meth:`Publisher.__load_or_create_group()`
	def __create_new_group(self, directory: Path, file: Path, proof: dict, eff_res_key: str) -> dict:
		steps_to_use = self.__resolve_steps(directory, eff_res_key)
		group = {'admission': proof, 'journal': str(directory), 'request_ids': self.__request_ids, 'requests': self.__requests, 'response_sha256': dfh_digest(self.__response.encode()), 'status': 'pending', 'steps': steps_to_use, 'tokens': [uuid.uuid4().hex for _ in self.__requests], 'turn': self.__turn, 'version': 1}
		self.__ops.get('create_bytes', dfh_create_bytes)(file, json.dumps(group, ensure_ascii=False, indent=2).encode())
		return group
	# @used-by :meth:`Publisher.__load_or_create_group()`
	def __load_existing_group(self, directory: Path, file: Path, res_dir: Path, proof: dict) -> dict:
		group = json.loads(file.read_text(encoding='utf-8'))
		if not dfh_same_journal_identity(group.get('journal'), directory) or group.get('requests') != self.__requests or group.get('request_ids') != self.__request_ids:
			raise ValueError('Answer group differs from its original journal/requests/response; preserve it')
		if group.get('response_sha256') != dfh_digest(self.__response.encode()):
			if not self.__allow_reprepare:
				raise ValueError('Answer group differs from its original journal/requests/response; preserve it')
			group['response_sha256'] = dfh_digest(self.__response.encode())
			group['admission'] = proof
			group['status'] = 'pending'
			for st in group.get('steps') or []:
				res_file = dfh_step_file(res_dir, st, directory=directory)
				if res_file.exists():
					dfh_replace_bytes(res_file, self.__response.encode('utf-8'))
		return group
	# @used-by :meth:`Publisher.run()`
	def __load_or_create_group(self, directory: Path, file: Path, res_dir: Path, proof: dict, eff_res_key: str) -> dict:
		return self.__load_existing_group(directory, file, res_dir, proof) if file.exists() else self.__create_new_group(directory, file, proof, eff_res_key)
	# @used-by :meth:`Publisher.run()`
	def __prepare_context(self) -> tuple[Path, dict, Path, Path, Path, Path, str]:
		from Df.Harness.lib.admission_ops import dfh_admission_binding, dfh_capture_admission, dfh_require_current_admission
		self.__validate_inputs()
		directory = Path(self.__directory).resolve()
		identity = dfh_admission_binding(directory, self.__requests, self.__response, self.__turn, self.__request_ids)
		roots = [Path(p).resolve() for p in (self.__admission_roots or (directory,))]
		capability = dfh_capture_admission(roots, self.__requests, self.__response, identity) if None is self.__admission else self.__admission
		proof = dfh_require_current_admission(capability, identity)
		journal_state = dfh_state_dir(directory)
		groups = journal_state / 'answer-groups'
		req_dir, res_dir = dfh_journal_pair_dirs(directory)
		for path in (req_dir, res_dir, groups):
			path.mkdir(parents=True, exist_ok=True)
		eff_res_key = self.__reserved_turn_key if None is not self.__reserved_turn_key else (self.__turn[7:] if self.__turn.startswith('native-') else self.__turn)
		return (directory, proof, journal_state, req_dir, res_dir, groups / (self.__turn + '.json'), eff_res_key)
	# @used-by :meth:`Publisher.run()`
	def __prune_reservations(self, directory: Path, journal_state: Path, eff_res_key: str, group: dict) -> None:
		if (journal_state / TURN_RESERVATIONS_FILE).is_file():
			reservations = dfh_read_turn_reservations(directory)
			if dfh_prune_overlapping_reservations(reservations, eff_res_key, set(self.__request_ids or ()), set(group.get('steps') or ())):
				dfh_write_turn_reservations(directory, reservations)
	# @used-by :meth:`Publisher.__create_new_group()`
	def __resolve_steps(self, directory: Path, eff_res_key: str) -> list[int]:
		if None is not self.__adopt_steps:
			if not isinstance(self.__adopt_steps, list) or len(self.__adopt_steps) != len(self.__requests) or any((int is not type(x) or 1 > x for x in self.__adopt_steps)):
				raise ValueError('Adopted journal steps must match the exact request list')
			r = list(self.__adopt_steps)
		else:
			existing_ids = dfh_get_existing_step_ids(directory)
			reservations = dfh_read_turn_reservations(directory)
			cand_entry = reservations.get(eff_res_key)
			if None is cand_entry and None is not self.__request_ids:
				cand_entry = next((e for e in reservations.values() if e.get('request_ids') == self.__request_ids), None)
			cand_steps = list(cand_entry.get('steps') or ()) if isinstance(cand_entry, dict) else []
			cand_rids = cand_entry.get('request_ids') if isinstance(cand_entry, dict) else None
			if self.__valid_reserved_steps(cand_steps, cand_rids, existing_ids):
				r = cand_steps
			else:
				start = max(existing_ids | dfh_reserved_step_ids(directory, exclude_turn=eff_res_key), default=0) + 1
				r = list(range(start, start + len(self.__requests)))
		return r
	# @used-by :meth:`Publisher.run()`
	def __sync_step(self, directory: Path, journal_state: Path, req_dir: Path, res_dir: Path, group: dict, step: int, request: str, token: str) -> None:
		if 'complete' == group['status']:
			for folder_dir, text in [(req_dir, request), (res_dir, self.__response)]:
				if dfh_step_file(folder_dir, step, directory=directory).read_bytes() != text.encode():
					raise ValueError('Completed answer group changed; journal is preserved')
		else:
			self.__write_pending_step(directory, journal_state, req_dir, res_dir, step, request, token)
	# @used-by :meth:`Publisher.__prepare_context()`
	def __validate_inputs(self) -> None:
		if not re.fullmatch('[A-Za-z0-9_-]{1,100}', self.__turn) or (not isinstance(self.__requests, list)) or (not self.__requests):
			raise ValueError('Stable turn ID and nonempty exact request list required')
		for request in self.__requests:
			dfh_validate_payload(request, self.__response)
		if None is not self.__request_ids and (len(self.__request_ids) != len(self.__requests) or any((not isinstance(x, str) or (not x) for x in self.__request_ids))):
			raise ValueError('Request IDs must match the exact request list')
	# @used-by :meth:`Publisher.__resolve_steps()`
	def __valid_reserved_steps(self, cand_steps: list, cand_rids: Any, existing_ids: set[int]) -> bool:
		ok_len = bool(cand_steps) and len(cand_steps) == len(self.__requests) and len(set(cand_steps)) == len(cand_steps)
		ok_vals = all((int is type(x) and 1 <= x and x not in existing_ids for x in cand_steps))
		return ok_len and ok_vals and (None is self.__request_ids or cand_rids == self.__request_ids)
	# @used-by :meth:`Publisher.__sync_step()`
	def __write_pending_step(self, directory: Path, journal_state: Path, req_dir: Path, res_dir: Path, step: int, request: str, token: str) -> None:
		receipt = journal_state / f'{step}.json'
		state = {'journal': str(directory), 'request': request, 'request_sha256': dfh_digest(request.encode()), 'response': self.__response, 'response_sha256': dfh_digest(self.__response.encode()), 'status': 'pending', 'step': step, 'token': token, 'version': 2}
		pub = self.__ops.get('publish', dfh_publish_step)
		if receipt.exists():
			if json.loads(receipt.read_text(encoding='utf-8')) != state:
				raise ValueError('Reserved answer step belongs to another payload; preserved')
			pub(directory, step, state, recovering=True)
		else:
			req, res = (dfh_step_file(req_dir, step, directory=directory), dfh_step_file(res_dir, step, directory=directory))
			if req.exists() and res.exists():
				if req.read_bytes() != request.encode() or res.read_bytes() != self.__response.encode():
					raise ValueError('Answer-group step is occupied; preserved')
			else:
				self.__ops.get('create_bytes', dfh_create_bytes)(receipt, json.dumps(state, ensure_ascii=False, indent=2).encode())
				pub(directory, step, state, recovering=True)
	# @used-by :func:`Df.Harness.lib.completion_record._commit_or_verify_journal_group()`
	# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
	# @used-by :func:`agent_tools.journal.record_answer()`
	def run(self) -> list[int]:
		directory, proof, journal_state, req_dir, res_dir, file, eff_res_key = self.__prepare_context()
		with dfh_locked(journal_state / 'writer.lock'):
			group = self.__load_or_create_group(directory, file, res_dir, proof, eff_res_key)
			for step, request, token in zip(group['steps'], self.__requests, group['tokens']):
				self.__sync_step(directory, journal_state, req_dir, res_dir, group, step, request, token)
			if 'complete' != group['status']:
				group['status'] = 'complete'
				dfh_replace_bytes(file, json.dumps(group, ensure_ascii=False, indent=2).encode())
			self.__prune_reservations(directory, journal_state, eff_res_key, group)
		return group['steps']
