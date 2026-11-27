# 2026-10-17 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Project.Intake.CaptureCommitter import CaptureCommitter
from Df.Harness.Project.Intake.IntakeIndexer import IntakeIndexer
from Df.Harness.Project.Intake.IntakePathGuard import IntakePathGuard
from Df.Harness.Project.Intake.ReceiptBuilder import ReceiptBuilder
from Df.Harness.Project.Intake.ReceiptValidator import ReceiptValidator
import os
from pathlib import Path
from .path_registry import store_path
from .runtime import HARNESS_META, PRIMARY, settings
from .storage import create_bytes
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
INCOMING = store_path('incoming_dir')
DAILY = Path(settings()['workspace_root']) / settings()['daily_root']
CAPTURE_NAME = IntakePathGuard.CAPTURE_NAME
INDEX_MARKER = IntakePathGuard.INDEX_MARKER
WEB_SUFFIXES = IntakePathGuard.WEB_SUFFIXES
# @used-by :mod:`agent_tools.intake`
def _bytes(value):
	return IntakePathGuard.json_bytes(value)
# @used-by :mod:`agent_tools.intake`
def _hash(payload):
	return df_sha256(payload)
# @used-by :func:`commit_capture()`
# @used-by :meth:`test_intake.IntakeTests.test_concurrent_edit_after_copy_is_preserved_and_not_silently_replanned()`
# @used-by :mod:`agent_tools.intake`
def _index(project):
	IntakeIndexer(project).rebuild()
# @used-by :mod:`agent_tools.intake`
def _inventory(capture):
	return IntakePathGuard.inventory(capture)
# @used-by :mod:`agent_tools.intake`
def _linked(path):
	return IntakePathGuard.is_linked(path)
# @used-by :mod:`agent_tools.intake`
def _plain(path):
	return IntakePathGuard.plain(path)
# @used-by :mod:`agent_tools.intake`
def _project(capture, daily):
	return CaptureCommitter.resolve_project(capture, daily, default_daily_root=DAILY)
# @used-by :mod:`agent_tools.intake`
def _read(path):
	return IntakePathGuard.read_stable(path)
# @used-by :mod:`agent_tools.intake`
def _receipt(project, capture, state, files, dirs):
	return ReceiptBuilder(project, capture, state, files, dirs).build()
# @used-by :mod:`agent_tools.intake`
def _remaining(receipt, capture):
	return CaptureCommitter.remaining(receipt, capture)
# @used-by :mod:`agent_tools.intake`
def _restore(receipt, capture):
	CaptureCommitter.restore(receipt, capture, rename_fn=os.rename)
# @used-by :meth:`test_intake.IntakeTests.test_concurrent_replacement_during_retirement_keeps_both_versions()`
# @used-by :mod:`agent_tools.intake`
def _retired(capture, name):
	return IntakePathGuard.retired_path(capture, name)
# @used-by :mod:`agent_tools.intake`
def _snapshot(project, state, source):
	return ReceiptValidator.verify_snapshot(project, state, source)
# @used-by :mod:`agent_tools.intake`
def _validate_new(capture, source, files, dirs):
	ReceiptValidator.validate_new_staging(capture, source, files, dirs)
# @used-by :mod:`agent_tools.intake`
def _validate_receipt(receipt, capture, project, state):
	ReceiptValidator(receipt, capture, project, state).validate()
# @used-by :mod:`agent_tools.intake`
def _within(root, relative):
	return IntakePathGuard.within(root, relative)
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :func:`drain_incoming()`
# @used-by :meth:`test_intake.IntakeTests.commit()`
# @used-by :mod:`agent_tools.intake`
def commit_capture(capture, *, incoming_root=None, daily_root=None, apply=False):
	return CaptureCommitter(capture, incoming_root=INCOMING if None is incoming_root else incoming_root, daily_root=DAILY if None is daily_root else daily_root, apply=apply, create_bytes_fn=create_bytes, index_fn=_index, rename_fn=os.rename, default_daily_root=DAILY).commit()
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :mod:`agent_tools.intake`
def drain_incoming(capture=None, *, incoming_root=None, daily_root=None, apply=False):
	return CaptureCommitter.drain_incoming(capture, incoming_root=INCOMING if None is incoming_root else incoming_root, daily_root=DAILY if None is daily_root else daily_root, apply=apply, commit_fn=commit_capture)
__all__ = ['CAPTURE_NAME', 'DAILY', 'HARNESS_META', 'INCOMING', 'INDEX_MARKER', 'PRIMARY', 'WEB_SUFFIXES', '_bytes', '_hash', '_index', '_inventory', '_linked', '_plain', '_project', '_read', '_receipt', '_remaining', '_restore', '_retired', '_snapshot', '_validate_new', '_validate_receipt', '_within', 'commit_capture', 'create_bytes', 'drain_incoming', 'os']
