# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.path_registry import project_paths
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Project.Intake.IntakePathGuard import IntakePathGuard
import json
from pathlib import Path
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ReceiptValidator:
	# @used-by :func:`agent_tools.intake._validate_receipt()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ManifestPrimaryVerifier.ManifestPrimaryVerifier.__check_intake()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__apply_drain()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__prepare_receipt()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__unlink_and_mark_drained()`
	def __init__(self, receipt: dict, capture: Path, project: Path, state: dict) -> None:
		self.__receipt, self.__capture, self.__project, self.__state = (receipt, capture, project, state)
	# @used-by :meth:`ReceiptValidator.validate_new_staging()`
	@staticmethod
	def __declared_attachments(capture: Path, source: dict, files: dict[str, bytes]) -> set[str]:
		r: set[str] = set()
		for asset in source.get('saved_attachments') or []:
			path = IntakePathGuard.plain(asset['path'])
			if not path.is_relative_to(capture):
				raise ValueError('Source attachment belongs outside this staging capture')
			relative = path.relative_to(capture).as_posix()
			if not relative.startswith('attachments/') or df_sha256(files[relative]) != asset['sha256']:
				raise ValueError('A captured attachment is missing or changed')
			r.add(relative)
		return r
	# @used-by :meth:`ReceiptValidator.verify_snapshot()`
	@staticmethod
	def __verify_permanent_assets(kb_dir: Path, evidence: Path, source: dict, saved: dict) -> None:
		assets, permanent = (source.get('saved_attachments') or [], saved.get('asset_evidence') or [])
		if sorted((x['sha256'] for x in assets)) != sorted((x['sha256'] for x in permanent)):
			raise ValueError('The permanent snapshot does not retain every attachment')
		for asset in permanent:
			target = IntakePathGuard.within(kb_dir, asset['file'])
			if not target.is_relative_to(evidence) or df_sha256(IntakePathGuard.read_stable(target)) != asset['sha256']:
				raise ValueError('A permanent attachment is missing or changed; staging is preserved')
	# @used-by :func:`agent_tools.intake._validate_receipt()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ManifestPrimaryVerifier.ManifestPrimaryVerifier.__check_intake()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__apply_drain()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__prepare_receipt()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__unlink_and_mark_drained()`
	def validate(self) -> None:
		pp = project_paths(self.__project, exact_root=True)
		rec = self.__receipt
		bad_hdr = not isinstance(rec, dict) or 1 != rec.get('version') or rec.get('capture_id') != self.__capture.name or (rec.get('job_id') != self.__state['job_id']) or (rec.get('original_directory_provenance') != str(self.__capture)) or (rec.get('status') not in ('prepared', 'drained'))
		if bad_hdr:
			raise ValueError('Unknown/manual intake receipt is preserved')
		names: set[str] = set()
		evidence_dir = IntakePathGuard.within(self.__project, pp.rel_to_root(pp.evidence_dir))
		for entry in rec['entries']:
			name = entry['original_relative_provenance']
			IntakePathGuard.within(self.__capture, name)
			target = IntakePathGuard.within(self.__project, entry['durable_file'])
			raw = IntakePathGuard.read_stable(target)
			if name in names or not re.fullmatch('[0-9a-f]{64}', entry['sha256']) or (not target.is_relative_to(evidence_dir)) or ('identity' != entry['transform']) or (len(raw) != entry['bytes']) or (df_sha256(raw) != entry['sha256']):
				raise ValueError('A permanent intake object is missing or changed; staging is preserved')
			names.add(name)
		original = next((x for x in rec['entries'] if 'source.json' == x['original_relative_provenance']))
		source = json.loads(IntakePathGuard.read_stable(IntakePathGuard.within(self.__project, original['durable_file'])).decode('utf-8-sig'))
		if self.verify_snapshot(self.__project, self.__state, source) != rec['snapshot']:
			raise ValueError('The permanent snapshot changed during intake; staging is preserved')
	# @used-by :func:`agent_tools.intake._validate_new()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptBuilder.ReceiptBuilder.build()`
	@classmethod
	def validate_new_staging(cls, capture: Path, source: dict, files: dict[str, bytes], dirs: set[str]) -> None:
		if not isinstance(source, dict) or source.get('job_id') != '~' + IntakePathGuard.CAPTURE_NAME.fullmatch(capture.name)[1]:
			raise ValueError('Capture directory and source job IDs differ')
		if source.get('cookies'):
			raise ValueError('Capture contains transport credentials; automatic evidence archive is deferred')
		declared = cls.__declared_attachments(capture, source, files)
		for name in files:
			path = Path(name)
			if not (name in ('source.json', 'site.json', 'request.txt', 'products.json_limit=250') or name in declared or (1 == len(path.parts) and path.suffix.lower() in IntakePathGuard.WEB_SUFFIXES)):
				raise ValueError(f'Unknown/manual file is preserved: {name}')
		if dirs - {'attachments'}:
			raise ValueError('Unknown/manual staging directories are preserved')
	# @used-by :func:`agent_tools.intake._snapshot()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptBuilder.ReceiptBuilder.build()`
	# @used-by :meth:`ReceiptValidator.validate()`
	@classmethod
	def verify_snapshot(cls, project: Path, state: dict, source: dict) -> dict:
		pp = project_paths(project, exact_root=True)
		if not isinstance(source, dict) or source.get('job_id') != state['job_id']:
			raise ValueError('The capture source does not match the initialized project')
		snapshot = IntakePathGuard.within(project, state['snapshot'])
		evidence = IntakePathGuard.within(project, pp.rel_to_root(pp.evidence_dir))
		kb_dir = IntakePathGuard.within(project, pp.rel_to_root(pp.kb_dir))
		if not snapshot.is_relative_to(evidence):
			raise ValueError('The initialized snapshot must belong to project Evidence')
		payload = IntakePathGuard.read_stable(snapshot)
		saved = json.loads(payload.decode('utf-8-sig'))
		clean = {k: v for k, v in source.items() if k not in ('saved_attachments', 'cookies')}
		if not isinstance(saved, dict) or {k: v for k, v in saved.items() if 'asset_evidence' != k} != clean:
			raise ValueError('The permanent snapshot differs from this capture; staging is preserved')
		cls.__verify_permanent_assets(kb_dir, evidence, source, saved)
		return {'file': snapshot.relative_to(project).as_posix(), 'sha256': df_sha256(payload), 'transform': 'Drop transport saved_attachments/cookies; add verified project asset_evidence.'}
