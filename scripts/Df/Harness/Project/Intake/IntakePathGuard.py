# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.sha256 import df_sha256
import json
import os
from pathlib import Path
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class IntakePathGuard:
	CAPTURE_NAME = re.compile('^(0[12][A-Za-z0-9]+)-([A-Za-z0-9-]{8,})$')
	INDEX_MARKER = '<!-- upwork-intake:generated v1 -->\n'
	WEB_SUFFIXES = {'.html', '.htm', '.json', '.xml', '.mjs', '.js', '.css', '.txt', '.png', '.jpg', '.jpeg', '.webp'}
	# @used-by :func:`agent_tools.intake._inventory()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__prepare_receipt()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__unlink_and_mark_drained()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.remaining()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_intake_classes()`
	@classmethod
	def inventory(cls, capture: Path) -> tuple[dict[str, bytes], set[str]]:
		result, dirs = ({}, set())
		if capture.exists():
			for parent, children, names in os.walk(capture, followlinks=False):
				parent_p = cls.plain(parent)
				for name in children:
					dirs.add(cls.plain(parent_p / name).relative_to(capture).as_posix())
				for name in names:
					path = cls.plain(parent_p / name)
					if not path.is_file():
						raise ValueError(f'Non-file staging material is preserved: {path}')
					result[path.relative_to(capture).as_posix()] = cls.read_stable(path)
		return (result, dirs)
	# @used-by :func:`agent_tools.intake._linked()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptBuilder.ReceiptBuilder.__scan_existing()`
	# @used-by :meth:`IntakePathGuard.plain()`
	@staticmethod
	def is_linked(path: Path) -> bool:
		return path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())
	# @used-by :func:`agent_tools.intake._bytes()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__apply_drain()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__unlink_and_mark_drained()`
	@staticmethod
	def json_bytes(value) -> bytes:
		return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
	# @used-by :func:`agent_tools.intake._plain()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__run_commit()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.drain_incoming()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.__declared_attachments()`
	# @used-by :meth:`IntakePathGuard.inventory()`
	# @used-by :meth:`IntakePathGuard.read_stable()`
	# @used-by :meth:`IntakePathGuard.within()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_intake_classes()`
	@classmethod
	def plain(cls, path) -> Path:
		resolved = Path(os.path.abspath(path))
		if any((cls.is_linked(p) for p in (resolved, *resolved.parents))):
			raise ValueError(f'Linked path is preserved: {resolved}')
		return resolved
	# @used-by :func:`agent_tools.intake._read()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__prepare_receipt()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__retire_entries()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__run_locked()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.resolve_project()`
	# @used-by :meth:`Df.Harness.Project.Intake.IntakeIndexer.IntakeIndexer.__render_lines()`
	# @used-by :meth:`Df.Harness.Project.Intake.IntakeIndexer.IntakeIndexer.rebuild()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptBuilder.ReceiptBuilder.__scan_existing()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.__verify_permanent_assets()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.validate()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.verify_snapshot()`
	# @used-by :meth:`IntakePathGuard.inventory()`
	@classmethod
	def read_stable(cls, path) -> bytes:
		clean = cls.plain(path)
		before = clean.stat()
		payload = clean.read_bytes()
		after = clean.stat()
		if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
			raise ValueError(f'Concurrent file change; staging is preserved: {clean}')
		return payload
	# @used-by :func:`agent_tools.intake._retired()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__match_remaining_entry()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__retire_entries()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__unlink_and_mark_drained()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.restore()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_intake_classes()`
	@classmethod
	def retired_path(cls, capture: Path, name: str) -> Path:
		return cls.within(capture, name).with_name('.intake-retired-' + df_sha256(name.encode('utf-8'))[:24])
	# @used-by :func:`agent_tools.intake._within()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__apply_drain()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__retire_entries()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__run_commit()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__run_locked()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__unlink_and_mark_drained()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.resolve_project()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.restore()`
	# @used-by :meth:`Df.Harness.Project.Intake.IntakeIndexer.IntakeIndexer.__render_lines()`
	# @used-by :meth:`Df.Harness.Project.Intake.IntakeIndexer.IntakeIndexer.rebuild()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptBuilder.ReceiptBuilder.build()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.__verify_permanent_assets()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.validate()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.verify_snapshot()`
	# @used-by :meth:`IntakePathGuard.retired_path()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_intake_classes()`
	@classmethod
	def within(cls, root: Path, relative) -> Path:
		rel = Path(str(relative).replace('\\', '/'))
		if rel.is_absolute() or '..' in rel.parts or (not rel.parts):
			raise ValueError('Evidence path must be relative and remain inside its owner')
		target = cls.plain(root / rel)
		if not target.is_relative_to(root):
			raise ValueError('Evidence path escapes its owner')
		return target
