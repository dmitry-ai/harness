# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from urllib.parse import urldefrag, urlsplit
from Df.Harness.Project.Diagnostics import Diagnostics
import re
_DEMO_RE = re.compile('(?i)(?:\\u0434\\u0435\\u043c\\u043e-\\u0437\\u0430\\u043f\\u0438\\u0441|\\u0434\\u0435\\u043c\\u043e-\\u0441\\u0442\\u0440\\u0430\\u043d\\u0438\\u0446|\\u0448\\u0430\\u0431\\u043b\\u043e\\u043d\\w+\\s+\\u0437\\u0430\\u0433\\u043b\\u0443\\u0448\\u043a|\\u043f\\u0443\\u0441\\u0442\\w+\\s+\\u0441\\u0442\\u0440\\u0430\\u043d\\u0438\\u0446|demo\\s+post|placeholder\\s+page|thin\\s+content)')
_EXTRAP_RE = re.compile('(?i)(?:\\u043d\\u0430\\s+(?:\\u0432\\u0441\\u0451\\u043c\\s+)?\\u0441\\u0430\\u0439\\u0442\\u0435|\\u043f\\u043e\\u043b\\u043d\\u043e\\u0441\\u0442\\u044c\\u044e\\s+\\u043e\\u0442\\u0441\\u0443\\u0442\\u0441\\u0442\\u0432\\u0443|\\u043e\\u0442\\u0441\\u0443\\u0442\\u0441\\u0442\\u0432\\u0443\\u044e\\u0442\\s+\\u0441\\u0445\\u0435\\u043c\\u044b\\s+`?(?:Product|Offer|Article)|absent\\s+across\\s+the\\s+entire\\s+site|no\\s+(?:Product|Offer|Article)\\s+schema\\s+on\\s+the\\s+site)')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ScopeCoverageAuditor:
	# @used-by :meth:`Df.Harness.Analysis.ClaimGraph.ClaimGraph.__check_verified_claim()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	def __init__(self, issues: list[dict]) -> None:
		self.__issues = issues
	# @used-by :meth:`ScopeCoverageAuditor.check()`
	def __sample_paths(self, claim: dict) -> set[str]:
		items = (claim.get('scope') or {}).get('sample') or ()
		urls = [s.strip() for s in items if isinstance(s, str) and (s.strip().startswith(('http://', 'https://')) or s.strip().startswith('/')) and 'example.invalid' not in s]
		return {urlsplit(urldefrag(s)[0]).path.rstrip('/') or '/' for s in urls}
	# @used-by :meth:`Df.Harness.Analysis.ClaimGraph.ClaimGraph.__check_verified_claim()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	def check(self, field: str, claim: dict, obs_urls: set[str]) -> None:
		observed_paths = {urlsplit(urldefrag(u)[0]).path.rstrip('/') or '/' for u in obs_urls if u}
		sample_paths = self.__sample_paths(claim)
		essence = str(claim.get('essence', ''))
		if observed_paths and all((p.lower().endswith(('sitemap.xml', 'robots.txt')) for p in observed_paths)):
			if {p for p in sample_paths if not p.lower().endswith(('sitemap.xml', 'robots.txt'))} or _DEMO_RE.search(essence):
				self.__issues.append(Diagnostics().problem('claim.sitemap_insufficient', field + '/evidence', 'A sitemap.xml/robots.txt observation only proves URL listing in XML, not the HTTP status, content or markup of target pages; collect the target page URLs or CMS JSON first', claim_id=claim.get('id')))
		if sample_paths and (len(observed_paths) < len(sample_paths) or (any((p not in ('/', '/sitemap.xml', '/robots.txt') for p in sample_paths)) and observed_paths.issubset({'/', '/sitemap.xml', '/robots.txt'}))):
			self.__issues.append(Diagnostics().problem('claim.unobserved_sample', field + '/scope/sample', 'Verified claim scope.sample lists page URLs that were not observed in primary evidence; collect every sampled URL or narrow scope.sample', claim_id=claim.get('id')))
		non_sitemap = {p for p in observed_paths if not p.lower().endswith(('sitemap.xml', 'robots.txt'))}
		if 1 >= len(non_sitemap) and _EXTRAP_RE.search(essence):
			self.__issues.append(Diagnostics().problem('claim.scope_extrapolation', field + '/scope', 'Homepage/single-page/sitemap observations alone cannot verify site-wide absence of Product/Offer/Article structured data; observe representative product/article pages or keep status limited', claim_id=claim.get('id')))