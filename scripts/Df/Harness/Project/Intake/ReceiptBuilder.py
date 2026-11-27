# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.path_registry import project_paths
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Project.Intake.IntakePathGuard import IntakePathGuard
from Df.Harness.Project.Intake.ReceiptValidator import ReceiptValidator
import json
import os
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ReceiptBuilder:
	# @used-by :func:`agent_tools.intake._receipt()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__prepare_receipt()`
	def __init__(self, project: Path, capture: Path, state: dict, files: dict[str, bytes], dirs: set[str]) -> None:
		self.__project, self.__capture, self.__state = (project, capture, state)
		self.__files, self.__dirs = (files, dirs)
	# @used-by :meth:`ReceiptBuilder.build()`
	def __scan_existing(self, evidence: Path, sizes: set[int]) -> dict[str, str]:
		r: dict[str, str] = {}
		for parent, children, names in os.walk(evidence, followlinks=False):
			children[:] = [name for name in children if not IntakePathGuard.is_linked(Path(parent) / name)]
			for name in names:
				path = Path(parent) / name
				if not IntakePathGuard.is_linked(path) and path.is_file() and (path.stat().st_size in sizes):
					r.setdefault(df_sha256(IntakePathGuard.read_stable(path)), path.relative_to(self.__project).as_posix())
		return r
	# @used-by :func:`agent_tools.intake._receipt()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__prepare_receipt()`
	def build(self) -> dict:
		pp = project_paths(self.__project, exact_root=True)
		ev_rel = pp.rel_to_root(pp.evidence_dir)
		source = json.loads(self.__files['source.json'].decode('utf-8-sig'))
		ReceiptValidator.validate_new_staging(self.__capture, source, self.__files, self.__dirs)
		snapshot = ReceiptValidator.verify_snapshot(self.__project, self.__state, source)
		known = self.__scan_existing(IntakePathGuard.within(self.__project, ev_rel), {len(p) for p in self.__files.values()})
		entries: list[dict] = []
		for name, payload in sorted(self.__files.items()):
			digest = df_sha256(payload)
			if digest not in known:
				suf = Path(name).suffix.lower()
				suf = suf if suf in ('.json', '.txt', '.xml', '.png', '.jpg', '.jpeg', '.webp') else suf + '.txt'
				known[digest] = f'{ev_rel}/Intake/objects/{digest}{suf}'
			entries.append({'original_relative_provenance': name, 'sha256': digest, 'bytes': len(payload), 'durable_file': known[digest], 'transform': 'identity'})
		return {'version': 1, 'capture_id': self.__capture.name, 'job_id': source['job_id'], 'status': 'prepared', 'original_directory_provenance': str(self.__capture), 'original_paths_are_provenance_only': True, 'snapshot': snapshot, 'entries': entries}
