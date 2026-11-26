# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Analysis.RedFlagRenderer import RedFlagRenderer
from agent_tools.storage import create_bytes, locked, replace_bytes
import json
START = b'<!-- upwork-init:red-flags:start -->'
END = b'<!-- upwork-init:red-flags:end -->'
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RedFlagSyncer:
	# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def __init__(self, root: Path | str, value: dict) -> None:
		self.__root = root
		self.__value = value
	# @used-by :meth:`RedFlagSyncer.__sync_locked()`
	def __build_block(self, newline: bytes, analysis_rel: str) -> tuple[bytes, bytes]:
		rendered = RedFlagRenderer(self.__value, project_card=True, analysis_rel=analysis_rel).render()
		title, content = rendered.split('\n\n', 1) if rendered else ('', '')
		heading = (title + '\n\n').encode('utf-8').replace(b'\n', newline) if title else b''
		cbytes = content.encode('utf-8').replace(b'\n', newline)
		block = START + newline + newline + cbytes + END + newline if cbytes else b''
		return (heading, block)
	# @used-by :meth:`RedFlagSyncer.__sync_locked()`
	def __extract_body(self, original: bytes, newline: bytes, block: bytes, heading: bytes, receipt: dict, target: Path) -> tuple[bytes, dict | None]:
		if START not in original and END not in original:
			r: tuple[bytes, dict | None] = (original, None)
		elif 1 != original.count(START) or 1 != original.count(END) or original.index(START) > original.index(END):
			r = (original, {'status': 'conflict', 'target': str(target), 'detail': 'Malformed Red Flags block; card preserved'})
		else:
			start, end = (original.index(START), original.index(END) + len(END))
			ending = newline if receipt.get('heading') else newline * 2
			end += len(ending) if original[end:end + len(ending)] == ending else (len(newline) if original[end:end + len(newline)] == newline else 0)
			current = original[start:end]
			if current != block and df_sha256(current) != receipt.get('block_sha256'):
				r = (original, {'status': 'conflict', 'target': str(target), 'detail': 'Red Flags block was manually edited; reconcile it explicitly'})
			else:
				start, err = self.__strip_heading(original, start, current, block, heading, receipt, target)
				r = (original[:start] + original[end:], err)
		return r
	# @used-by :meth:`RedFlagSyncer.__sync_locked()`
	def __separator(self, body: bytes, block: bytes, newline: bytes) -> bytes:
		if not block or body in (b'', b'\xef\xbb\xbf') or body.endswith(newline * 2):
			r = b''
		elif body.endswith(newline):
			r = newline
		else:
			r = newline * 2
		return r
	# @used-by :meth:`RedFlagSyncer.__extract_body()`
	def __strip_heading(self, original: bytes, start: int, current: bytes, block: bytes, heading: bytes, receipt: dict, target: Path) -> tuple[int, dict | None]:
		prev_heading = receipt.get('heading', '').encode('utf-8')
		err: dict | None = None
		if prev_heading:
			if not original[:start].endswith(prev_heading):
				err = {'status': 'conflict', 'target': str(target), 'detail': 'Red Flags heading was manually edited; reconcile it explicitly'}
			else:
				start -= len(prev_heading)
				sep = receipt.get('separator', '').encode('utf-8')
				if sep and original[:start].endswith(sep):
					start -= len(sep)
		elif heading and original[:start].endswith(heading) and (current == block):
			start -= len(heading)
		return (start, err)
	# @used-by :meth:`RedFlagSyncer.sync()`
	def __sync_locked(self, target: Path, state_dir: Path, analysis_rel: str) -> dict:
		original = target.read_bytes()
		original.decode('utf-8-sig')
		newline = b'\r\n' if b'\r\n' in original else b'\n'
		heading, block = self.__build_block(newline, analysis_rel)
		state_file = state_dir / 'red-flags.json'
		receipt = json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else {}
		body, err = self.__extract_body(original, newline, block, heading, receipt, target)
		if None is not err:
			r = err
		else:
			sep = self.__separator(body, block, newline)
			payload = body + sep + heading + block if block else body
			self.__write_card(target, state_dir, state_file, original, payload, block, heading, sep)
			r = {'status': 'unchanged' if payload == original else 'published', 'target': str(target), 'sha256': df_sha256(payload)}
		return r
	# @used-by :meth:`RedFlagSyncer.__sync_locked()`
	def __write_card(self, target: Path, state_dir: Path, state_file: Path, original: bytes, payload: bytes, block: bytes, heading: bytes, sep: bytes) -> None:
		if payload != original:
			archive = state_dir / 'red-flags-history' / (df_sha256(original) + '.md')
			archive.parent.mkdir(parents=True, exist_ok=True)
			if not archive.exists():
				create_bytes(archive, original)
			if target.read_bytes() != original:
				raise ValueError('Project card changed during publication; reread and reconcile')
			replace_bytes(target, payload)
		if target.read_bytes() != payload:
			raise OSError('Project card failed read-back verification')
		metadata = {'block_sha256': df_sha256(block), 'heading': heading.decode('utf-8'), 'separator': sep.decode('utf-8')}
		replace_bytes(state_file, (json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
	# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def sync(self) -> dict:
		from Df.Harness.Analysis.Validator import Validator
		from Df.Harness.Project.IssueValidator import IssueValidator
		from agent_tools.path_registry import project_paths
		IssueValidator(Validator(self.__value).issues()).require_valid()
		pp = project_paths(self.__root, exact_root=True)
		target = pp.path('overview_md', pp.root / '.md')
		if 'red_flags' not in self.__value:
			r = {'status': 'unassessed', 'target': str(target)}
		else:
			analysis_rel = pp.rel_to_root(pp.kb_dir / 'Analysis.json')
			with locked(pp.data_dir / 'red-flags.lock'):
				r = self.__sync_locked(target, pp.data_dir, analysis_rel)
		return r