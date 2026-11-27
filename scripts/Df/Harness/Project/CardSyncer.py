# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import nullcontext
from pathlib import Path
from Df.Core.lib.sha256 import df_sha256
from Df.Core.lib.text.n.normalize import df_normalize
from agent_tools.storage import locked, replace_bytes
import json
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class CardSyncer:
	# @used-by :func:`agent_tools.project_card.sync_block()`
	# @used-by :meth:`Df.Harness.Project.Intake.IntakeIndexer.IntakeIndexer.rebuild()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.__sync_selected()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.sync_initial()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def __init__(self, root, target, key: str, content: str, position: str='after-title', *, check: bool=False, source=None, attributes=None) -> None:
		self.__root = Path(root).resolve()
		self.__target = (self.__root / target).resolve()
		self.__key = key
		self.__content = content
		self.__position = position
		self.__check = check
		self.__source = source
		self.__attributes = attributes
		self.__base = {'target': str(self.__target), 'block': key}
	# @used-by :meth:`CardSyncer.__compute_payload()`
	def __build_block(self, newline: bytes) -> tuple[bytes, bytes, bytes]:
		start = f'<!-- upwork-init:{self.__key}:start -->'.encode()
		end = f'<!-- upwork-init:{self.__key}:end -->'.encode()
		body = df_normalize(self.__content).rstrip('\n').encode().replace(b'\n', newline)
		return (start, end, start + newline + newline + body + newline + end + newline)
	# @used-by :meth:`CardSyncer.__write_result()`
	def __build_metadata(self, sha: str) -> dict:
		r: dict = {'sha256': sha, 'source': str(self.__source) if None is not self.__source else None}
		if None is not self.__attributes:
			r['data'] = self.__attributes
		return r
	# @used-by :meth:`CardSyncer.__read_state()`
	def __check_receipt_entry(self, receipts: object) -> tuple[dict, dict | None, dict | None]:
		if not isinstance(receipts, dict):
			r: tuple[dict, dict | None, dict | None] = ({}, None, self.__conflict('Malformed publication receipt; preserved'))
		else:
			entry = receipts.get(str(self.__target), {})
			if not isinstance(entry, dict) or not isinstance(entry.get('managed_blocks', {}), dict):
				r = ({}, None, self.__conflict('Malformed block ownership receipt; preserved'))
			else:
				owned = entry.get('managed_blocks', {}).get(self.__key)
				bad_own = None is not owned and (not isinstance(owned, dict) or not re.fullmatch('[a-f0-9]{64}', str(owned.get('sha256', ''))))
				r = (entry, None, self.__conflict('Malformed block ownership hash; preserved')) if bad_own else (entry, owned, None)
		return r
	# @used-by :meth:`CardSyncer.sync()`
	def __compute_payload(self, previous: bytes, owned: dict | None) -> tuple[bytes | None, bytes, dict | None]:
		newline = b'\r\n' if b'\r\n' in previous else b'\n'
		start, end, block = self.__build_block(newline)
		if previous.count(start) or previous.count(end):
			payload, err = self.__replace_existing(previous, start, end, newline, block, owned)
		else:
			payload, err = self.__insert_new(previous, newline, block, owned)
		return (payload, block, err)
	# @used-by :meth:`CardSyncer.__check_receipt_entry()`
	# @used-by :meth:`CardSyncer.__insert_new()`
	# @used-by :meth:`CardSyncer.__read_state()`
	# @used-by :meth:`CardSyncer.__replace_existing()`
	# @used-by :meth:`CardSyncer.__write_files()`
	# @used-by :meth:`CardSyncer.__write_result()`
	def __conflict(self, detail: str) -> dict:
		return {**self.__base, 'status': 'conflict', 'detail': detail}
	# @used-by :meth:`CardSyncer.__insert_new()`
	def __insert_offset(self, previous: bytes) -> int:
		offset = 3 if previous.startswith(b'\xef\xbb\xbf') else 0
		if 'append' == self.__position:
			offset = len(previous)
		elif 'after-title' == self.__position and previous[offset:].startswith(b'# '):
			eol = previous.find(b'\n', offset)
			offset = eol + 1 if 0 <= eol else len(previous)
		return offset
	# @used-by :meth:`CardSyncer.__compute_payload()`
	def __insert_new(self, previous: bytes, newline: bytes, block: bytes, owned: dict | None) -> tuple[bytes | None, dict | None]:
		if owned and previous:
			r: tuple[bytes | None, dict | None] = (None, self.__conflict('Previously published block was removed; manual text preserved'))
		else:
			offset = self.__insert_offset(previous)
			prefix, suffix = (previous[:offset], previous[offset:])
			before = newline * 2 if prefix and (not prefix.endswith(newline)) else (newline if prefix and (not prefix.endswith(newline * 2)) else b'')
			after = newline if suffix and (not suffix.startswith(newline)) else b''
			r = (prefix + before + block + after + suffix, None)
		return r
	# @used-by :meth:`CardSyncer.sync()`
	def __read_state(self, receipt_path: Path) -> tuple[dict, dict, dict | None, bytes, dict | None]:
		receipts, entry, owned, previous, err = ({}, {}, None, b'', None)
		try:
			raw = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {}
			entry, owned, err = self.__check_receipt_entry(raw)
			if None is err:
				receipts = raw
				previous = self.__target.read_bytes() if self.__target.exists() else b''
				previous.decode('utf-8-sig')
		except (OSError, UnicodeError, json.JSONDecodeError) as exc:
			err = self.__conflict(f'Cannot read existing publication safely: {type(exc).__name__}')
		return (receipts, entry, owned, previous, err)
	# @used-by :meth:`CardSyncer.__compute_payload()`
	def __replace_existing(self, previous: bytes, start: bytes, end: bytes, newline: bytes, block: bytes, owned: dict | None) -> tuple[bytes | None, dict | None]:
		if 1 != previous.count(start) or 1 != previous.count(end) or previous.index(start) > previous.index(end):
			r: tuple[bytes | None, dict | None] = (None, self.__conflict('Malformed or repeated managed markers; surrounding text preserved'))
		else:
			first, last = (previous.index(start), previous.index(end) + len(end))
			if previous[last:last + len(newline)] == newline:
				last += len(newline)
			current = previous[first:last]
			if current != block and (not owned or df_sha256(current) != owned['sha256']):
				r = (None, self.__conflict('Managed block was manually changed or is unowned; reconcile explicitly'))
			else:
				r = (previous[:first] + block + previous[last:], None)
		return r
	# @used-by :meth:`CardSyncer.sync()`
	def __validate_inputs(self) -> None:
		if not self.__target.is_relative_to(self.__root):
			raise ValueError('Managed KB block must stay inside the project')
		if self.__position not in ('start', 'after-title', 'append') or not re.fullmatch('[a-z][a-z0-9-]*', self.__key):
			raise ValueError('Known block position and a lowercase block key required')
		if not isinstance(self.__content, str) or '<!-- upwork-init:' in self.__content:
			raise ValueError('Managed block content must be text without reserved markers')
		from agent_tools.links import readable_link_issues
		issues = readable_link_issues(self.__content)
		if issues:
			raise ValueError('\n'.join(issues))
	# @used-by :meth:`CardSyncer.__write_result()`
	def __write_files(self, payload: bytes, changed: bool, receipt_changed: bool, metadata: dict, receipts: dict, entry: dict, receipt_path: Path) -> dict | None:
		if changed:
			replace_bytes(self.__target, payload)
		if self.__target.read_bytes() != payload:
			r: dict | None = self.__conflict('Publication read-back differs; inspect the target before retrying')
		else:
			if receipt_changed:
				entry.setdefault('managed_blocks', {})[self.__key] = metadata
				receipts[str(self.__target)] = entry
				replace_bytes(receipt_path, (json.dumps(receipts, ensure_ascii=False, indent=2) + '\n').encode())
			r = None
		return r
	# @used-by :meth:`CardSyncer.sync()`
	def __write_result(self, previous: bytes, payload: bytes, block: bytes, owned: dict | None, receipts: dict, entry: dict, receipt_path: Path) -> dict:
		sha = df_sha256(block)
		metadata = self.__build_metadata(sha)
		changed, receipt_changed = (payload != previous, owned != metadata)
		if self.__check:
			r = {**self.__base, 'status': 'stale' if changed or receipt_changed else 'unchanged', 'sha256': sha, 'detail': 'Read-only comparison; no files written'}
		else:
			current_disk = self.__target.read_bytes() if self.__target.exists() else b''
			if current_disk != previous:
				r = self.__conflict('Target changed during publication; external edit preserved')
			else:
				err = self.__write_files(payload, changed, receipt_changed, metadata, receipts, entry, receipt_path)
				r = err if None is not err else {**self.__base, 'status': 'published' if changed else 'unchanged', 'sha256': sha}
		return r
	# @used-by :func:`agent_tools.project_card.sync_block()`
	# @used-by :meth:`Df.Harness.Project.Intake.IntakeIndexer.IntakeIndexer.rebuild()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.__sync_selected()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.sync_initial()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def sync(self) -> dict:
		self.__validate_inputs()
		from agent_tools.path_registry import project_paths
		pp = project_paths(self.__root, exact_root=True)
		with nullcontext() if self.__check else locked(pp.data_dir / 'render.lock'):
			receipts, entry, owned, previous, err = self.__read_state(pp.rendered_json)
			if None is not err:
				r = err
			else:
				payload, block, perr = self.__compute_payload(previous, owned)
				r = perr if None is not perr else self.__write_result(previous, payload, block, owned, receipts, entry, pp.rendered_json)
		return r