# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.sha256 import df_sha256, df_sha256_file, df_sha256_text
from Df.Harness.lib.storage import dfh_create_bytes, dfh_data_dir_for, dfh_locked, dfh_replace_bytes
import json
import re
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
# @used-by :mod:`agent_tools.snapshot`
class DraftSnapshotter:
	__TURN_ID_RE = re.compile(r'[A-Za-z0-9_-]{1,80}')
	# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
	# @used-by :meth:`test_df_harness_s11_final_338.DfHarnessS11Final338Tests.test_draft_snapshotter_and_facade_cover_capture_verify_and_errors()`
	def __init__(self, source: Path, turn: str) -> None:
		self.__source = Path(source)
		self.__turn = turn
	# @used-by :meth:`DraftSnapshotter.snapshot()`
	def __capture_new(self, source: Path, archive: Path, saved: Path, previous: Path) -> Path:
		data = source.read_bytes()
		dfh_create_bytes(saved, data)
		receipt = json.dumps({'source': str(source), 'turn': self.__turn, 'sha256': df_sha256(data)}, ensure_ascii=False, indent=2).encode('utf-8')
		dfh_create_bytes(archive / 'snapshot.json', receipt)
		if source.read_bytes() != data:
			raise ValueError('Source changed during capture; snapshot retained for inspection')
		dfh_replace_bytes(previous, data)
		if previous.read_bytes() != data or saved.read_bytes() != data:
			raise OSError('Snapshot read-back failed')
		return saved
	# @used-by :meth:`DraftSnapshotter.snapshot()`
	def __validate_inputs(self) -> Path:
		source = self.__source.resolve(strict=True)
		if 'draft.md' != source.name:
			raise ValueError('Expected an explicit draft.md path')
		if not DraftSnapshotter.__TURN_ID_RE.fullmatch(self.__turn):
			raise ValueError('Turn ID must contain 1..80 ASCII letters, digits, _ or -')
		return source
	# @used-by :meth:`DraftSnapshotter.snapshot()`
	@staticmethod
	def __verify_existing(source: Path, archive: Path, saved: Path, previous: Path) -> Path:
		receipt = json.loads((archive / 'snapshot.json').read_text(encoding='utf-8'))
		if receipt['source'] != str(source):
			raise ValueError('Snapshot belongs to a different source')
		if df_sha256_file(saved) != receipt['sha256']:
			raise ValueError('Snapshot changed after capture')
		if previous.read_bytes() != saved.read_bytes():
			raise ValueError('draft.prev.md changed; preserve both versions before continuing')
		return saved
	# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
	# @used-by :meth:`test_df_harness_s11_final_338.DfHarnessS11Final338Tests.test_draft_snapshotter_and_facade_cover_capture_verify_and_errors()`
	def snapshot(self) -> Path:
		source = self.__validate_inputs()
		snapshots = dfh_data_dir_for(source) / '.draft-snapshots'
		source_id = df_sha256_text(str(source).casefold())[:24]
		archive = snapshots / self.__turn / source_id
		archive.mkdir(parents=True, exist_ok=True)
		saved = archive / 'draft.md'
		previous = source.with_name('draft.prev.md')
		with dfh_locked(snapshots / 'writer.lock'):
			r = DraftSnapshotter.__verify_existing(source, archive, saved, previous) if saved.exists() else self.__capture_new(source, archive, saved, previous)
		return r
