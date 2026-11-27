# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.path_registry import project_paths, store_path
from agent_tools.runtime import settings
from agent_tools.storage import create_bytes, locked, replace_bytes
from contextlib import nullcontext
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Project.Intake.IntakeIndexer import IntakeIndexer
from Df.Harness.Project.Intake.IntakePathGuard import IntakePathGuard
from Df.Harness.Project.Intake.ReceiptBuilder import ReceiptBuilder
from Df.Harness.Project.Intake.ReceiptValidator import ReceiptValidator
from Df.Harness.Upwork.JobUrlParser import JobUrlParser
import json
import os
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class CaptureCommitter:
	# @used-by :func:`agent_tools.intake.commit_capture()`
	# @used-by :meth:`CaptureCommitter.drain_incoming()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_init()`
	def __init__(self, capture, *, incoming_root=None, daily_root=None, apply: bool=False, create_bytes_fn=None, index_fn=None, rename_fn=None, default_daily_root=None) -> None:
		self.__capture = Path(capture)
		self.__incoming = Path(store_path('incoming_dir') if None is incoming_root else incoming_root)
		self.__default_daily = Path(settings()['workspace_root']) / settings()['daily_root'] if None is default_daily_root else Path(default_daily_root)
		self.__daily = self.__default_daily if None is daily_root else Path(daily_root)
		self.__apply = apply
		self.__create_bytes_fn = create_bytes if None is create_bytes_fn else create_bytes_fn
		self.__index_fn = (lambda p: IntakeIndexer(p).rebuild()) if None is index_fn else index_fn
		self.__rename_fn = os.rename if None is rename_fn else rename_fn
		self.__active_receipt: dict | None = None
		self.__active_capture: Path = self.__capture
	# @used-by :meth:`CaptureCommitter.__run_locked()`
	def __apply_drain(self, project: Path, capture: Path, state: dict, manifest: Path, receipt: dict, files: dict[str, bytes]) -> None:
		if not manifest.exists():
			for entry in receipt['entries']:
				target = IntakePathGuard.within(project, entry['durable_file'])
				if not target.exists():
					target.parent.mkdir(parents=True, exist_ok=True)
					self.__create_bytes_fn(target, files[entry['original_relative_provenance']])
			ReceiptValidator(receipt, capture, project, state).validate()
			manifest.parent.mkdir(parents=True, exist_ok=True)
			self.__create_bytes_fn(manifest, IntakePathGuard.json_bytes(receipt))
		self.__index_fn(project)
		self.remaining(receipt, capture)
		self.__retire_entries(capture, receipt)
		self.__unlink_and_mark_drained(project, capture, state, manifest, receipt)
	# @used-by :meth:`CaptureCommitter.remaining()`
	@staticmethod
	def __match_remaining_entry(entry: dict, capture: Path, files: dict[str, bytes], out: dict) -> None:
		name = entry['original_relative_provenance']
		retired = IntakePathGuard.retired_path(capture, name).relative_to(capture).as_posix()
		if name in files and retired in files:
			raise ValueError('Concurrent replacement is preserved alongside retired evidence')
		for cand in (name, retired):
			if cand in files:
				if df_sha256(files[cand]) != entry['sha256']:
					raise ValueError('Concurrent staging change; every remaining file is preserved')
				out[cand] = entry
	# @used-by :meth:`CaptureCommitter.__run_locked()`
	def __prepare_receipt(self, project: Path, capture: Path, state: dict, manifest: Path) -> tuple[dict, dict[str, bytes]]:
		if manifest.exists():
			receipt = json.loads(IntakePathGuard.read_stable(manifest).decode('utf-8-sig'))
			ReceiptValidator(receipt, capture, project, state).validate()
			files: dict[str, bytes] = {}
		else:
			files, dirs = IntakePathGuard.inventory(capture)
			receipt = ReceiptBuilder(project, capture, state, files, dirs).build()
		return (receipt, files)
	# @used-by :meth:`CaptureCommitter.__apply_drain()`
	def __retire_entries(self, capture: Path, receipt: dict) -> None:
		for entry in receipt['entries']:
			name = entry['original_relative_provenance']
			orig = IntakePathGuard.within(capture, name)
			if orig.exists():
				if df_sha256(IntakePathGuard.read_stable(orig)) != entry['sha256']:
					raise ValueError('Concurrent staging change; drain deferred')
				self.__rename_fn(orig, IntakePathGuard.retired_path(capture, name))
	# @used-by :meth:`CaptureCommitter.commit()`
	def __run_commit(self, report: dict) -> dict:
		incoming, daily = (IntakePathGuard.plain(self.__incoming), IntakePathGuard.plain(self.__daily))
		capture = IntakePathGuard.plain(self.__capture if self.__capture.is_absolute() else incoming / self.__capture)
		self.__active_capture = capture
		report['capture'] = str(capture)
		if capture.parent != incoming:
			raise ValueError('Only one immediate managed incoming capture may be drained')
		project, _ = self.resolve_project(capture, daily, default_daily_root=self.__default_daily)
		pp = project_paths(project, exact_root=True)
		report['project'] = str(project)
		lock_ctx = locked(IntakePathGuard.within(project, f'{pp.rel_to_root(pp.data_dir)}/init.lock')) if self.__apply else nullcontext()
		with lock_ctx:
			r = self.__run_locked(project, capture, pp, report)
		return r
	# @used-by :meth:`CaptureCommitter.__run_commit()`
	def __run_locked(self, project: Path, capture: Path, pp, report: dict) -> dict:
		state = json.loads(IntakePathGuard.read_stable(IntakePathGuard.within(project, pp.rel_to_root(pp.project_json))).decode('utf-8-sig'))
		if not isinstance(state, dict) or True is not state.get('initialized') or state.get('job_id') != '~' + IntakePathGuard.CAPTURE_NAME.fullmatch(capture.name)[1]:
			raise ValueError('Project initialization changed; staging is preserved')
		kb_rel, ev_rel = (pp.rel_to_root(pp.kb_dir), pp.rel_to_root(pp.evidence_dir))
		manifest = IntakePathGuard.within(project, f'{ev_rel}/Intake/{capture.name}.json')
		receipt, files = self.__prepare_receipt(project, capture, state, manifest)
		self.__active_receipt = receipt
		report.update(manifest=str(manifest), files=len(receipt['entries']), bytes=sum((x['bytes'] for x in receipt['entries'])), evidence_index=str(IntakePathGuard.within(project, f'{kb_rel}/Intake.md')), durable_inputs={x['original_relative_provenance']: str(IntakePathGuard.within(project, x['durable_file'])) for x in receipt['entries'] if x['original_relative_provenance'] in ('source.json', 'site.json', 'request.txt')})
		self.remaining(receipt, capture)
		if not self.__apply:
			r = {**report, 'status': 'planned'}
		else:
			self.__apply_drain(project, capture, state, manifest, receipt, files)
			r = {**report, 'status': 'drained', 'drained': True}
		return r
	# @used-by :meth:`CaptureCommitter.__apply_drain()`
	def __unlink_and_mark_drained(self, project: Path, capture: Path, state: dict, manifest: Path, receipt: dict) -> None:
		self.remaining(receipt, capture)
		ReceiptValidator(receipt, capture, project, state).validate()
		for entry in receipt['entries']:
			rem = self.remaining(receipt, capture)
			retired = IntakePathGuard.retired_path(capture, entry['original_relative_provenance'])
			if retired.relative_to(capture).as_posix() in rem:
				retired.unlink()
		if capture.exists():
			_, dirs = IntakePathGuard.inventory(capture)
			for rel in sorted(dirs, key=lambda x: len(Path(x).parts), reverse=True):
				IntakePathGuard.within(capture, rel).rmdir()
			capture.rmdir()
		if 'drained' != receipt['status']:
			receipt['status'] = 'drained'
			replace_bytes(manifest, IntakePathGuard.json_bytes(receipt))
	# @used-by :func:`agent_tools.intake.commit_capture()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_init()`
	def commit(self) -> dict:
		report = {'capture': str(self.__capture), 'status': 'retained', 'drained': False}
		try:
			r = self.__run_commit(report)
		except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
			if self.__apply and None is not self.__active_receipt:
				try:
					self.restore(self.__active_receipt, self.__active_capture, rename_fn=self.__rename_fn)
				except (OSError, ValueError):
					pass
			r = {**report, 'reason': str(exc)}
		return r
	# @used-by :func:`agent_tools.intake.drain_incoming()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__run_intake_drain()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_intake_classes()`
	@classmethod
	def drain_incoming(cls, capture=None, *, incoming_root=None, daily_root=None, apply: bool=False, commit_fn=None) -> dict:
		incoming = IntakePathGuard.plain(store_path('incoming_dir') if None is incoming_root else incoming_root)
		paths = [Path(capture)] if None is not capture else sorted(incoming.iterdir()) if incoming.exists() else []
		fn = (lambda p: cls(p, incoming_root=incoming, daily_root=daily_root, apply=apply).commit()) if None is commit_fn else (lambda p: commit_fn(p, incoming_root=incoming, daily_root=daily_root, apply=apply))
		captures = [fn(path) for path in paths]
		return {'applied': apply, 'complete': all((x['status'] in ('planned', 'drained') for x in captures)), 'captures': captures, 'retained': sum(('retained' == x['status'] for x in captures))}
	# @used-by :func:`agent_tools.intake._remaining()`
	# @used-by :meth:`CaptureCommitter.__apply_drain()`
	# @used-by :meth:`CaptureCommitter.__run_locked()`
	# @used-by :meth:`CaptureCommitter.__unlink_and_mark_drained()`
	@classmethod
	def remaining(cls, receipt: dict, capture: Path) -> dict:
		files, dirs = IntakePathGuard.inventory(capture)
		allowed_dirs = {parent.as_posix() for e in receipt['entries'] for parent in Path(e['original_relative_provenance']).parents if parent != Path('.')}
		if dirs - allowed_dirs:
			raise ValueError('New/manual staging directory appeared; staging is preserved')
		r: dict = {}
		for entry in receipt['entries']:
			cls.__match_remaining_entry(entry, capture, files, r)
		if set(files) != set(r):
			raise ValueError('New/manual staging files appeared; staging is preserved')
		return r
	# @used-by :func:`agent_tools.intake._project()`
	# @used-by :meth:`CaptureCommitter.__run_commit()`
	@staticmethod
	def resolve_project(capture: Path, daily: Path, *, default_daily_root=None) -> tuple[Path, dict]:
		match = IntakePathGuard.CAPTURE_NAME.fullmatch(capture.name)
		if not match:
			raise ValueError('Unknown/manual capture directory is preserved')
		job_id = JobUrlParser.normalize_job_id('~' + match[1])
		default_daily = Path(settings()['workspace_root']) / settings()['daily_root'] if None is default_daily_root else Path(default_daily_root)
		reg_file = store_path('upwork_projects_index') if daily.resolve() == default_daily.resolve() and (not (daily / 'ꘖ/data/projects.json').exists()) else IntakePathGuard.within(daily, 'ꘖ/data/projects.json')
		registry = json.loads(IntakePathGuard.read_stable(reg_file).decode('utf-8-sig'))
		if not isinstance(registry, dict) or job_id not in registry:
			raise ValueError('Capture has no registered project; staging is preserved')
		project = IntakePathGuard.within(daily, registry[job_id])
		pp = project_paths(project, exact_root=True)
		state = json.loads(IntakePathGuard.read_stable(IntakePathGuard.within(project, pp.rel_to_root(pp.project_json))).decode('utf-8-sig'))
		if not isinstance(state, dict) or state.get('job_id') != job_id or True is not state.get('initialized'):
			raise ValueError('Project initialization is incomplete; staging is preserved')
		return (project, state)
	# @used-by :func:`agent_tools.intake._restore()`
	# @used-by :meth:`CaptureCommitter.commit()`
	@staticmethod
	def restore(receipt: dict, capture: Path, *, rename_fn=None) -> None:
		rfn = os.rename if None is rename_fn else rename_fn
		for entry in receipt['entries']:
			orig = IntakePathGuard.within(capture, entry['original_relative_provenance'])
			retired = IntakePathGuard.retired_path(capture, entry['original_relative_provenance'])
			if retired.exists() and (not orig.exists()):
				rfn(retired, orig)
