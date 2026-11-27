# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Project.Diagnostics import Diagnostics
from Df.Harness.Project.DriftAuditor import DriftAuditor
from Df.Harness.lib.project import dfh_resolve_overview_md
import re
_CLIENT_NAME_RE = re.compile('(?:client|author|artist|owner|customer|founder|\\u043a\\u043b\\u0438\\u0435\\u043d\\u0442|\\u0430\\u0432\\u0442\\u043e\\u0440|\\u0445\\u0443\\u0434\\u043e\\u0436\\u043d\\u0438\\u043a|\\u0432\\u043b\\u0430\\u0434\\u0435\\u043b\\u0435\\u0446|\\u0437\\u0430\\u043a\\u0430\\u0437\\u0447\\u0438\\u043a|\\u043e\\u0441\\u043d\\u043e\\u0432\\u0430\\u0442\\u0435\\u043b\\u044c)[^.]{0,40}?\\b[A-Z\\u0410-\\u042f\\u0401][a-z\\u0430-\\u044f\\u0451]{1,25}\\s+[A-Z\\u0410-\\u042f\\u0401][a-z\\u0430-\\u044f\\u0451]{1,25}\\b', re.IGNORECASE)
_NAME_UNKNOWN_RE = re.compile('#\\s*1\\.1\\s+(?:Name|\\u0418\\u043c\\u044f)\\s*\\r?\\n\\s*(?:unknown|\\u043d\\u0435\\u0438\\u0437\\u0432\\u0435\\u0441\\u0442\\u043d\\u043e)\\b', re.IGNORECASE)
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class CardSyncAuditor:
	# @used-by :func:`agent_tools.project_drift.analysis_card_sync_issues()`
	# @used-by :meth:`Df.Harness.Workflow.AnalysisCardAuditor.AnalysisCardAuditor.issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	# @used-by :meth:`test_upwork_v2_root_card.UpworkV2RootCardTests.test_legacy_v2_readme_fallback_works_across_card_consumers()`
	def __init__(self, pp, value: dict, *, drift_fn=None) -> None:
		self.__pp = pp
		self.__value = value
		self.__drift_fn = drift_fn
	# @used-by :meth:`CardSyncAuditor.__identity_mismatches()`
	def __established_identity(self) -> bool:
		return any((isinstance(c, dict) and ('verified' == c.get('verification_status') or 80 <= (c.get('probability_percent') or 0)) and _CLIENT_NAME_RE.search(c.get('essence') or '') for c in self.__value.get('identity') or ()))
	# @used-by :meth:`CardSyncAuditor.audit()`
	def __identity_mismatches(self) -> list[dict]:
		r: list[dict] = []
		if self.__established_identity():
			for proj_file in (self.__pp.manual_kb_dir / 'Project.md', self.__pp.kb_dir / 'Project.md'):
				if proj_file.is_file() and _NAME_UNKNOWN_RE.search(proj_file.read_text(encoding='utf-8')):
					rel_proj = self.__pp.rel_to_root(proj_file)
					r.append(Diagnostics().problem('kb.identity_mismatch', rel_proj, f'Established client identity in Analysis.json is not synced to {rel_proj} (# 1.1 Name is still unknown)', file=proj_file))
		return r
	# 2026-11-28 "Use .md root card via v2_upwork profile": https://github.com/dmitry-ai/harness/issues/415
	# @used-by :func:`agent_tools.project_drift.analysis_card_sync_issues()`
	# @used-by :meth:`Df.Harness.Workflow.AnalysisCardAuditor.AnalysisCardAuditor.issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	# @used-by :meth:`test_upwork_v2_root_card.UpworkV2RootCardTests.test_legacy_v2_readme_fallback_works_across_card_consumers()`
	def audit(self) -> list[dict]:
		from Df.Harness.Project.WebsiteCardSyncer import WebsiteCardSyncer
		drift_fn = (lambda r, v: DriftAuditor(r, v).audit()) if None is self.__drift_fn else self.__drift_fn
		r: list[dict] = []
		overview_file = dfh_resolve_overview_md(self.__pp)
		website = WebsiteCardSyncer(self.__pp.root, self.__value, check=True).sync()
		if website['status'] not in ('published', 'unchanged'):
			r.append(Diagnostics().problem('project.website', self.__pp.rel_to_root(overview_file), 'Publish the explicit evidenced client/target website selection, or null if unidentified', file=overview_file))
		r.extend(self.__identity_mismatches())
		r.extend(drift_fn(self.__pp.root, self.__value))
		return r