# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from urllib.parse import urlsplit
from Df.Harness.Project.LabelValidator import LabelValidator
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class DomainNormalizer:
	# @used-by :func:`agent_tools.project_labels.normalize_domain_host()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.resolve_promotable_target_domain()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_diagnostics_and_label_classes()`
	def __init__(self, url_or_host: str | None) -> None:
		self.__raw = url_or_host
	# @used-by :func:`Df.Core.lib.text.filter.df_translit()`
	# @used-by :func:`agent_tools.project_labels.normalize_domain_host()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.InlineCalcVerifier.InlineCalcVerifier.__process_match()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.resolve_promotable_target_domain()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_diagnostics_and_label_classes()`
	def normalize(self) -> str | None:
		r = None
		if isinstance(self.__raw, str) and self.__raw.strip():
			raw = self.__raw.strip()
			host = urlsplit(raw).hostname if '://' in raw else raw
			if isinstance(host, str) and host.strip():
				cand = host.strip().rstrip('.').lower()
				cand = cand[4:] if cand.startswith('www.') else cand
				if LabelValidator.is_valid_domain(cand):
					r = cand
		return r