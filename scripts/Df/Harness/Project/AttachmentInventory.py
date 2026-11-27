# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.storage import create_bytes
from Df.Harness.Upwork.AttachmentDownloader import AttachmentDownloader
import hashlib
from pathlib import Path
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class AttachmentInventory:
	# @used-by :func:`agent_tools.knowledge.sync_source_folder_attachments()`
	# @used-by :meth:`Df.Harness.Project.AttachmentKbSyncer.AttachmentKbSyncer.sync()`
	# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.build()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`Df.Harness.Workflow.AttachmentAuditor.AttachmentAuditor.issues()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	def __init__(self, project_root: Path | str) -> None:
		from agent_tools.path_registry import project_paths
		self.pp = project_paths(project_root, exact_root=True)
		self.root, self.kb_dir = (self.pp.root, self.pp.kb_dir)
		self.att_root, self.source_dir = (self.pp.evidence_dir / 'Attachments', self.pp.source_dir)
	# @used-by :meth:`AttachmentInventory.scan()`
	# @used-by :meth:`AttachmentInventory.sync()`
	def __evidence_entries(self, asset_evidence: list[dict] | None=None) -> list[tuple[Path, str | None]]:
		r: list[tuple[Path, str | None]] = []
		for item in asset_evidence or []:
			rel = item.get('file') if isinstance(item, dict) else None
			if rel and (self.kb_dir / rel).is_file():
				r.append((self.kb_dir / rel, item.get('sha256')))
		if self.att_root.is_dir():
			for sha_dir in sorted(self.att_root.iterdir()):
				if sha_dir.is_dir() and re.fullmatch('[0-9a-f]{64}', sha_dir.name):
					r.extend(((f, sha_dir.name) for f in sorted(sha_dir.iterdir()) if f.is_file()))
		return r
	# @used-by :meth:`AttachmentInventory.sync()`
	def __register_bytes(self, filename: str, payload: bytes, expected_sha: str | None, seen_digests: set[str], assets: list[dict]) -> None:
		digest = hashlib.sha256(payload).hexdigest()
		if expected_sha and digest != expected_sha:
			raise ValueError(f'Attachment changed after capture: {filename}')
		folder = self.att_root / digest
		target = AttachmentDownloader.attachment_path(folder, filename)
		folder.mkdir(parents=True, exist_ok=True)
		if not target.exists():
			create_bytes(target, payload)
		src_target = self.__resolve_source_target(target.name, payload)
		if not src_target.exists():
			create_bytes(src_target, payload)
		if digest not in seen_digests:
			seen_digests.add(digest)
			assets.append({'file': target.relative_to(self.kb_dir).as_posix(), 'sha256': digest, 'filename': target.name, 'source_file': src_target.relative_to(self.root).as_posix()})
	# @used-by :meth:`AttachmentInventory.__register_bytes()`
	def __resolve_source_target(self, name: str, payload: bytes) -> Path:
		self.source_dir.mkdir(parents=True, exist_ok=True)
		src_target = AttachmentDownloader.attachment_path(self.source_dir, name)
		if src_target.exists() and src_target.read_bytes() != payload:
			stem, suf, idx = (src_target.stem, src_target.suffix, 2)
			while True:
				cand = self.source_dir / f'{stem} ({idx}){suf}'
				if not cand.exists() or cand.read_bytes() == payload:
					src_target = cand
					break
				idx += 1
		return src_target
	# @used-by :meth:`AttachmentInventory.scan()`
	# @used-by :meth:`AttachmentInventory.sync()`
	def __source_entries(self) -> list[Path]:
		return [f for f in sorted(self.source_dir.iterdir()) if f.is_file()] if self.source_dir.is_dir() else []
	# @used-by :meth:`Df.Harness.Workflow.AttachmentAuditor.AttachmentAuditor.issues()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	def scan(self, asset_evidence: list[dict] | None=None) -> dict:
		attachments: list[dict] = []
		seen_sha: set[str] = set()
		for target, hint_sha in self.__evidence_entries(asset_evidence):
			sha = hint_sha or hashlib.sha256(target.read_bytes()).hexdigest()
			if sha not in seen_sha:
				seen_sha.add(sha)
				attachments.append({'filename': target.name, 'sha256': sha, 'evidence_path': target})
		source_by_sha: dict[str, list[Path]] = {}
		missing_evidence: list[tuple[Path, str]] = []
		for f in self.__source_entries():
			sha = hashlib.sha256(f.read_bytes()).hexdigest()
			source_by_sha.setdefault(sha, []).append(f)
			if not (self.att_root / sha / f.name).is_file():
				missing_evidence.append((f, sha))
			if sha not in seen_sha:
				seen_sha.add(sha)
				attachments.append({'filename': f.name, 'sha256': sha, 'evidence_path': f})
		return {'attachments': attachments, 'missing_evidence': missing_evidence, 'source_by_sha': source_by_sha}
	# @used-by :func:`agent_tools.knowledge.sync_source_folder_attachments()`
	# @used-by :meth:`Df.Harness.Project.AttachmentKbSyncer.AttachmentKbSyncer.sync()`
	# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.build()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	def sync(self, saved_attachments: list[dict] | None=None, asset_evidence: list[dict] | None=None) -> list[dict]:
		r: list[dict] = []
		seen_digests: set[str] = set()
		for item in saved_attachments or []:
			src_path = Path(item['path'])
			fname = item.get('filename') or item.get('name') or src_path.name
			self.__register_bytes(fname, src_path.read_bytes(), item.get('sha256'), seen_digests, r)
		for target, expected_sha in self.__evidence_entries(asset_evidence):
			self.__register_bytes(target.name, target.read_bytes(), expected_sha, seen_digests, r)
		for f in self.__source_entries():
			self.__register_bytes(f.name, f.read_bytes(), None, seen_digests, r)
		return r
