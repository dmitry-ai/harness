# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
from Df.Harness.Path.ProjectPaths import ProjectPaths
from Df.Harness.lib.path_resolve import dfh_load_registry, dfh_project_paths
from Df.Harness.lib.path_schema import dfh_discover_overlay_file
from Df.Harness.lib.path_template import dfh_path_key
import glob
import json
import os
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class PathReporter:
	# @used-by :func:`agent_tools.path_registry.paths_report()`
	# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_paths_and_uri()`
	def __init__(self, project: str | Path | None=None, *, expand: str | None=None, check: bool=False, registry: Any=None) -> None:
		self.__project = project
		self.__expand = expand
		self.__check = check
		self.__reg = registry or dfh_load_registry()
	# @used-by :meth:`PathReporter.run()`
	def __build_project_report(self, issues: list[dict[str, str]]) -> dict[str, Any]:
		try:
			pp = dfh_project_paths(self.__project, registry=self.__reg)
			if self.__check:
				for sp in pp.similar_projects:
					msg = f'Missing similar_projects target directory: {sp.as_posix()}'
					if (not sp.is_dir()) and all((it.get('message') != msg for it in issues)):
						issues.append({'file': (pp.overlay_file or self.__reg.source_path).as_posix(), 'message': msg})
			r = pp.to_dict(check_exists=True)
			if None is not self.__expand:
				r['expanded'] = pp.expand(self.__expand)
			r['registry_file'] = self.__reg.source_path.as_posix()
			if self.__check:
				r['valid'], r['issues'] = (not issues, issues)
		except (OSError, ValueError) as exc:
			if not self.__check:
				raise
			r = {'issues': [*issues, {'file': str(self.__project), 'message': str(exc)}], 'registry_file': self.__reg.source_path.as_posix(), 'valid': False}
		return r
	# @used-by :meth:`PathReporter.run()`
	def __check_similar_groups(self, issues: list[dict[str, str]]) -> None:
		reg = self.__reg
		anchor_abs = Path(os.path.abspath(reg.anchor_code))
		for grp in reg.similar_project_groups:
			for mem in grp['members']:
				m_proj = Path(mem['project'])
				if not m_proj.is_dir():
					issues.append({'file': reg.source_path.as_posix(), 'message': f"Missing similar_projects member directory in group '{grp['id']}': {m_proj.as_posix()}"})
				for aff in mem['affiliated_paths']:
					aff_p = Path(os.path.abspath(aff))
					aff_ok = aff_p.exists() or (reg.has_synthetic_primary and aff_p.is_relative_to(anchor_abs) and (reg.source_path.parent / aff_p.relative_to(anchor_abs)).exists())
					if not aff_ok:
						issues.append({'file': reg.source_path.as_posix(), 'message': f"Missing similar_projects affiliated path in group '{grp['id']}': {aff_p.as_posix()}"})
	# @used-by :meth:`PathReporter.__discover_overlays()`
	def __collect_check_roots(self, issues: list[dict[str, str]]) -> list[Path]:
		reg = self.__reg
		roots = [Path(r_str).resolve() for r_str in reg.overlay_discovery_roots if Path(r_str).is_dir()]
		for g_str in reg.overlay_discovery_globs:
			roots.extend((Path(m).resolve() for m in sorted(glob.glob(g_str)) if Path(m).is_dir()))
		idx_str, daily_str = (reg.harness_stores.get('upwork_projects_index'), reg.resolved_variables.get('UPWORK_DAILY_ROOT'))
		if isinstance(idx_str, str) and isinstance(daily_str, str) and Path(idx_str).is_file() and Path(daily_str).is_dir():
			try:
				entries = json.loads(Path(idx_str).read_text(encoding='utf-8'))
				if isinstance(entries, dict):
					roots.extend(((Path(daily_str) / rel).resolve() for rel in entries.values() if isinstance(rel, str) and (Path(daily_str) / rel).is_dir()))
			except (OSError, ValueError) as exc:
				issues.append({'file': idx_str, 'message': str(exc)})
		return roots
	# @used-by :meth:`PathReporter.run()`
	def __discover_overlays(self, issues: list[dict[str, str]]) -> list[dict[str, Any]]:
		discovered: list[dict[str, Any]] = []
		seen: set[str] = set()
		for rp in self.__collect_check_roots(issues):
			rk = dfh_path_key(rp)
			if rk in seen:
				continue
			seen.add(rk)
			try:
				ov = dfh_discover_overlay_file(rp, self.__reg)
				if None is not ov:
					pp_i = ProjectPaths(rp, registry=self.__reg)
					if self.__check:
						for sp in pp_i.similar_projects:
							if not sp.is_dir():
								issues.append({'file': ov.as_posix(), 'message': f'Missing similar_projects target directory: {sp.as_posix()}'})
					discovered.append({'fs_version': pp_i.fs_version, 'journal_version': pp_i.journal_version, 'overlay_file': ov.as_posix(), 'profile': pp_i.profile, 'project_root': pp_i.root.as_posix(), 'similar_projects': [p.as_posix() for p in pp_i.similar_projects]})
			except (OSError, ValueError) as exc:
				issues.append({'file': rp.as_posix(), 'message': str(exc)})
		return discovered
	# @used-by :func:`agent_tools.path_registry.paths_report()`
	# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_paths_and_uri()`
	def run(self) -> dict[str, Any]:
		issues: list[dict[str, str]] = []
		if self.__check:
			self.__check_similar_groups(issues)
		discovered = self.__discover_overlays(issues) if self.__check or None is self.__project else []
		if None is not self.__project:
			r = self.__build_project_report(issues)
		else:
			reg = self.__reg
			r = {'discovered_overlays': discovered, 'harness_stores': deepcopy(reg.harness_stores), 'issues': issues, 'profiles': list(reg.project_profiles), 'registry_file': reg.source_path.as_posix(), 'relocations': dict(reg.relocations), 'similar_projects': [deepcopy(g) for g in reg.similar_project_groups], 'tools': deepcopy(reg.tools), 'valid': not issues, 'variables': dict(reg.resolved_variables), 'workspace_overrides': deepcopy(reg.workspace_overrides)}
			if None is not self.__expand:
				r['expanded'] = reg.expand(self.__expand)
		return r
