# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Upwork.AttachmentDownloader import AttachmentDownloader
from Df.Harness.Upwork.JobUrlParser import JobUrlParser
from urllib.parse import urlsplit
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class TabSelector:
	# @used-by :func:`agent_tools.upwork_extract.select_tab()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__resolve_target()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
	def __init__(self, tabs: list[dict], job_id: str, tab_id: str | None=None) -> None:
		self.__tabs = tabs
		self.__job_id = job_id
		self.__tab_id = tab_id
	# @used-by :meth:`TabSelector.select()`
	def __matches_job(self, tab: dict) -> bool:
		path = urlsplit(tab['url']).path
		try:
			r = path.startswith('/jobs/') and JobUrlParser.normalize_job_id(path) == self.__job_id
		except ValueError:
			r = False
		return r
	# @used-by :func:`agent_tools.upwork_extract.select_tab()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__resolve_target()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
	def select(self) -> dict:
		candidates = [t for t in self.__tabs if 'page' == t.get('type') and AttachmentDownloader.upwork_host(t.get('url', ''))]
		candidates = [t for t in candidates if t.get('id') == self.__tab_id] if self.__tab_id else [t for t in candidates if self.__matches_job(t)]
		if 1 != len(candidates):
			raise ValueError('Select one exact Upwork job tab with --tab-id; no arbitrary account fallback')
		return candidates[0]
