# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.runtime import request_day, settings
from agent_tools.storage import locked, replace_bytes
from Df.Harness.Project.LabelValidator import LabelValidator
from Df.Harness.Upwork.JobUrlParser import JobUrlParser
import json
from pathlib import Path
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ProjectDirResolver:
	# @used-by :func:`agent_tools.upwork_project.resolve_or_create_project_dir()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.initialize()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_project_management_classes()`
	def __init__(self, job_id: str, domain_or_topic: str, date_str=None, daily_root=None, *, default_daily_root=None) -> None:
		self.__job_id, self.__domain_or_topic, self.__date_str = (job_id, domain_or_topic, date_str)
		self.__daily_root, self.__default_daily_root = (daily_root, default_daily_root)
	# @used-by :meth:`ProjectDirResolver.__resolve_or_make_new()`
	@staticmethod
	def __find_existing(parent: Path, job_id: str) -> tuple[Path | None, list[int]]:
		numbers: list[int] = []
		found: Path | None = None
		for child in parent.iterdir():
			match = re.match('^(\\d+) - ', child.name)
			if not (child.is_dir() and match):
				continue
			numbers.append(int(match[1]))
			if ProjectDirResolver.__matches_job(child, job_id):
				found = child
				break
		return (found, numbers)
	# @used-by :meth:`ProjectDirResolver.__find_existing()`
	@staticmethod
	def __matches_job(child: Path, job_id: str) -> bool:
		state_path = child / '\ua616/project.json'
		matched_state = False
		if state_path.is_file():
			try:
				matched_state = json.loads(state_path.read_text(encoding='utf-8')).get('job_id') == job_id
			except Exception:
				matched_state = False
		urls = (JobUrlParser.canonical_job_url(job_id), f'https://www.upwork.com/jobs/{job_id}')
		return matched_state or any((ov.is_file() and any((u in ov.read_text(encoding='utf-8') for u in urls)) for ov in (child / 'readme.md', child / '.md')))
	# @used-by :meth:`ProjectDirResolver.resolve_or_create()`
	@staticmethod
	def __resolve_indexed(daily: Path, rel_entry: str) -> Path:
		r: Path | None = None
		cand = (daily / str(rel_entry)).resolve()
		if cand.is_relative_to(daily):
			from agent_tools.path_registry import _path_key, load_registry
			reg = load_registry()
			ck = _path_key(cand)
			if not cand.is_dir() and ck in reg.relocations:
				reloc = Path(reg.relocations[ck]).resolve()
				if reloc.is_dir():
					r = reloc
			elif cand.is_dir():
				r = cand
		if None is r:
			raise ValueError('Project registry points to a missing or external directory')
		return r
	# @used-by :meth:`ProjectDirResolver.resolve_or_create()`
	def __resolve_or_make_new(self, daily: Path, day, job_id: str, label: str, index: dict, index_file: Path) -> Path:
		from agent_tools.knowledge import json_bytes
		parent = daily / f'{day.year:04d}' / f'{day.month:02d}' / f'{day.day:02d}'
		parent.mkdir(parents=True, exist_ok=True)
		found, numbers = self.__find_existing(parent, job_id)
		target = found if None is not found else (parent / f'{max(numbers, default=0) + 1} - {label}')
		if None is found:
			target.mkdir(exist_ok=False)
		index[job_id] = target.relative_to(daily).as_posix()
		replace_bytes(index_file, json_bytes(index))
		return target
	# @used-by :func:`agent_tools.upwork_project.resolve_or_create_project_dir()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.initialize()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_project_management_classes()`
	def resolve_or_create(self) -> Path:
		from agent_tools.path_registry import store_path
		job_id, label, day = (JobUrlParser.normalize_job_id(self.__job_id), LabelValidator(self.__domain_or_topic).validate(kind='safe'), request_day(self.__date_str))
		default_daily = Path(self.__default_daily_root).resolve() if None is not self.__default_daily_root else (Path(settings()['workspace_root']).resolve() / settings()['daily_root'])
		daily = Path(self.__daily_root).resolve() if None is not self.__daily_root else default_daily
		state = store_path('upwork_projects_dir') if daily == default_daily and (not (daily / '\ua616/data/projects.json').exists()) else daily / '\ua616/data'
		with locked(state / 'projects.lock'):
			index_file = state / 'projects.json'
			index = json.loads(index_file.read_text(encoding='utf-8')) if index_file.exists() else {}
			r = self.__resolve_indexed(daily, index[job_id]) if job_id in index else self.__resolve_or_make_new(daily, day, job_id, label, index, index_file)
		return r
