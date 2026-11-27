# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.json_io import df_json_dict_load
from Df.Harness.Project.Diagnostics import Diagnostics
from Df.Harness.Project.Rename.ProjectRenamer import ProjectRenamer
from agent_tools.path_registry import project_paths
import re
_REG_SUFFIX_RE = re.compile(r'\s+-\s+U\.P\.\d{4}\.\d{2}\.\d{2}$')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class DriftAuditor:
	# @used-by :func:`agent_tools.project_drift.domain_drift_issues()`
	# @used-by :meth:`Df.Harness.Project.CardSyncAuditor.CardSyncAuditor.audit()`
	# @used-by :meth:`Df.Harness.Project.FinalizeDriftGuard.FinalizeDriftGuard.require()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	def __init__(self, root: Path | str, analysis_value: dict) -> None:
		self.__root = root
		self.__analysis_value = analysis_value
	# @used-by :meth:`DriftAuditor.audit()`
	def __title_mismatches(self, pp, expected_domain: str) -> list[str]:
		r: list[str] = []
		data = df_json_dict_load(pp.registrations_json)
		if None is not data:
			exp_low = expected_domain.casefold()
			for plat, entry in sorted(data.items()):
				if isinstance(entry, dict) and (entry.get('complete') or 'registered' == entry.get('status')):
					pname = str(entry.get('project_name') or '').strip()
					if pname and _REG_SUFFIX_RE.sub('', pname).strip().casefold() != exp_low:
						r.append(f'{plat}:{pname}')
		return r
	# @used-by :func:`agent_tools.project_drift.domain_drift_issues()`
	# @used-by :meth:`Df.Harness.Project.CardSyncAuditor.CardSyncAuditor.audit()`
	# @used-by :meth:`Df.Harness.Project.FinalizeDriftGuard.FinalizeDriftGuard.require()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	def audit(self) -> list[dict]:
		pp = project_paths(self.__root, exact_root=True)
		pj = df_json_dict_load(pp.project_json)
		r: list[dict] = []
		if None is not pj and isinstance(self.__analysis_value, dict) and (not pj.get('domain_drift_exempt')):
			expected, basis_id = ProjectRenamer.resolve_promotable_target_domain(self.__analysis_value, min_probability=75)
			if None is not expected:
				folder_label = pp.root.name.split(' - ', 1)[-1].strip()
				mismatches = [f'folder "{folder_label}"'] if folder_label.casefold() != expected.casefold() else []
				mismatches.extend(self.__title_mismatches(pp, expected))
				if mismatches:
					actual = ', '.join(mismatches)
					msg = f'Project {actual} disagrees with resolved target domain "{expected}" ({basis_id}); run harness.py rename-project "{pp.root.as_posix()}" --domain {expected} or set domain_drift_exempt in \ua616/project.json'
					r.append(Diagnostics().problem('project.domain_drift', pp.rel_to_root(pp.project_json), msg, file=pp.project_json))
		return r