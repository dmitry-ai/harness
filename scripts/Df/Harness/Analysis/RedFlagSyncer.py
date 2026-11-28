# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Analysis.RedFlagRenderer import RedFlagRenderer
from Df.Harness.lib.project import dfh_resolve_overview_md
from agent_tools.storage import create_bytes, locked, replace_bytes
import json
import re
START = b'<!-- upwork-init:red-flags:start -->'
END = b'<!-- upwork-init:red-flags:end -->'
_HEADING_RE = re.compile(b'(?:^|\\r?\\n)(# Red Flags(?:\\r?\\n|$))')
_NEXT_H1_RE = re.compile(b'\\r?\\n# [^#]')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RedFlagSyncer:
	# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def __init__(self, root: Path | str, value: dict) -> None:
		self.__root = root
		self.__value = value
	# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
	# @used-by :meth:`RedFlagSyncer.__sync_locked()`
	def __build_section(self, newline: bytes, analysis_rel: str) -> bytes:
		rendered = RedFlagRenderer(self.__value, project_card=True, analysis_rel=analysis_rel).render()
		return rendered.encode('utf-8').replace(b'\n', newline) if rendered else b''
	# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
	# @used-by :meth:`RedFlagSyncer.__sync_locked()`
	def __extract_body(self, original: bytes, newline: bytes, section: bytes, receipt: dict, target: Path) -> tuple[bytes, dict | None]:
		if START in original or END in original:
			r = self.__extract_legacy(original, newline, receipt, target)
		else:
			r = self.__extract_heading_section(original, section, receipt, target)
		return r
	# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
	# @used-by :meth:`RedFlagSyncer.__extract_body()`
	def __extract_heading_section(self, original: bytes, section: bytes, receipt: dict, target: Path) -> tuple[bytes, dict | None]:
		bom = 3 if original.startswith(b'\xef\xbb\xbf') else 0
		hits = list(_HEADING_RE.finditer(original[bom:]))
		owned_len = int(receipt.get('section_len') or 0)
		body_hint = str(receipt.get('body_hint') or '').encode('utf-8')
		if not hits:
			err = {'status': 'conflict', 'target': str(target), 'detail': 'Red Flags heading was manually edited; reconcile it explicitly'} if 0 < owned_len and body_hint and body_hint in original else None
			r: tuple[bytes, dict | None] = (original, err)
		elif 1 < len(hits):
			r = (original, {'status': 'conflict', 'target': str(target), 'detail': 'Malformed duplicate Red Flags heading; card preserved'})
		else:
			r = self.__slice_heading_match(original, bom + hits[0].start(1), section, receipt, owned_len, target)
		return r
	# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
	# @used-by :meth:`RedFlagSyncer.__extract_body()`
	def __extract_legacy(self, original: bytes, newline: bytes, receipt: dict, target: Path) -> tuple[bytes, dict | None]:
		if 1 != original.count(START) or 1 != original.count(END) or original.index(START) > original.index(END):
			r: tuple[bytes, dict | None] = (original, {'status': 'conflict', 'target': str(target), 'detail': 'Malformed Red Flags block; card preserved'})
		else:
			start, end = (original.index(START), original.index(END) + len(END))
			ending = newline if receipt.get('heading') else newline * 2
			end += len(ending) if original[end:end + len(ending)] == ending else (len(newline) if original[end:end + len(newline)] == newline else 0)
			if df_sha256(original[start:end]) != receipt.get('block_sha256'):
				r = (original, {'status': 'conflict', 'target': str(target), 'detail': 'Red Flags block was manually edited; reconcile it explicitly'})
			else:
				start, err = self.__strip_legacy_heading(original, start, receipt, target)
				r = (original[:start] + original[end:], err)
		return r
	# @used-by :meth:`RedFlagSyncer.__sync_locked()`
	def __separator(self, body: bytes, section: bytes, newline: bytes) -> bytes:
		if not section or body in (b'', b'\xef\xbb\xbf') or body.endswith(newline * 2):
			r = b''
		elif body.endswith(newline):
			r = newline
		else:
			r = newline * 2
		return r
	# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
	# @used-by :meth:`RedFlagSyncer.__extract_heading_section()`
	def __slice_heading_match(self, original: bytes, h_start: int, section: bytes, receipt: dict, owned_len: int, target: Path) -> tuple[bytes, dict | None]:
		owned_end = h_start + owned_len
		nl = b'\r\n' if b'\r\n' in original else b'\n'
		sep = receipt.get('separator', '').encode('utf-8').replace(b'\r\n', b'\n').replace(b'\n', nl)
		cut = h_start - len(sep) if sep and original[:h_start].endswith(sep) else h_start
		if 0 < owned_len and owned_end <= len(original) and df_sha256(original[h_start:owned_end]) == receipt.get('section_sha256'):
			r: tuple[bytes, dict | None] = (original[:cut] + original[owned_end:], None)
		else:
			nxt = _NEXT_H1_RE.search(original, h_start + 11)
			sec_end = (nxt.start() + (2 if original[nxt.start():].startswith(b'\r\n') else 1)) if nxt else len(original)
			cand = original[h_start:sec_end]
			cand_norm = cand.replace(b'\r\n', b'\n').rstrip(b'\n') + b'\n'
			norm_ok = bool(receipt.get('norm_sha256')) and df_sha256(cand_norm) == receipt.get('norm_sha256')
			r = (original[:cut] + original[sec_end:], None) if cand == section or norm_ok else (original, {'status': 'conflict', 'target': str(target), 'detail': 'Red Flags block was manually edited; reconcile it explicitly'})
		return r
	# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
	# @used-by :meth:`RedFlagSyncer.__extract_legacy()`
	def __strip_legacy_heading(self, original: bytes, start: int, receipt: dict, target: Path) -> tuple[int, dict | None]:
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
		return (start, err)
	# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
	# @used-by :meth:`RedFlagSyncer.sync()`
	def __sync_locked(self, target: Path, state_dir: Path, analysis_rel: str) -> dict:
		original = target.read_bytes()
		original.decode('utf-8-sig')
		newline = b'\r\n' if b'\r\n' in original else b'\n'
		section = self.__build_section(newline, analysis_rel)
		state_file = state_dir / 'red-flags.json'
		receipt = json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else {}
		body, err = self.__extract_body(original, newline, section, receipt, target)
		if None is not err:
			r = err
		else:
			sep = self.__separator(body, section, newline)
			payload = body + sep + section if section else body
			self.__write_card(target, state_dir, state_file, original, payload, section, sep)
			r = {'status': 'unchanged' if payload == original else 'published', 'target': str(target), 'sha256': df_sha256(payload)}
		return r
	# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
	# @used-by :meth:`RedFlagSyncer.__sync_locked()`
	def __write_card(self, target: Path, state_dir: Path, state_file: Path, original: bytes, payload: bytes, section: bytes, sep: bytes) -> None:
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
		sec_lines = section.decode('utf-8').splitlines() if section else []
		body_hint = next((ln for ln in sec_lines[1:] if ln.strip()), '')
		norm_sha = df_sha256(section.replace(b'\r\n', b'\n'))
		metadata = {'body_hint': body_hint, 'format': 'heading-section', 'norm_sha256': norm_sha, 'section_len': len(section), 'section_sha256': df_sha256(section), 'separator': sep.decode('utf-8')}
		replace_bytes(state_file, (json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
	# 2026-11-28 "Use .md root card via v2_upwork profile": https://github.com/dmitry-ai/harness/issues/415
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
		target = dfh_resolve_overview_md(pp)
		if 'red_flags' not in self.__value:
			r = {'status': 'unassessed', 'target': str(target)}
		else:
			analysis_rel = pp.rel_to_root(pp.kb_dir / 'Analysis.json')
			with locked(pp.data_dir / 'red-flags.lock'):
				r = self.__sync_locked(target, pp.data_dir, analysis_rel)
		return r