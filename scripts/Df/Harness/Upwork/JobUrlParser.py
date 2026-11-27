# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
from urllib.parse import urldefrag, urlsplit
_NUXT_WRAPPERS = ('Reactive', 'ShallowReactive', 'Ref', 'EmptyRef', 'Set', 'ShallowRef')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class JobUrlParser:
	# @used-by :meth:`JobUrlParser.resolve_nuxt_devalue()`
	@classmethod
	def __resolve_value(cls, arr: list, val, nxt: set[int]):
		if not isinstance(val, (list, dict)):
			r = val
		elif isinstance(val, dict):
			r = {k: cls.resolve_nuxt_devalue(arr, v, nxt) if isinstance(v, int) else v for k, v in val.items()}
		elif 2 == len(val) and isinstance(val[0], str) and (val[0] in _NUXT_WRAPPERS):
			r = cls.resolve_nuxt_devalue(arr, val[1], nxt)
		else:
			r = [cls.resolve_nuxt_devalue(arr, x, nxt) if isinstance(x, int) else x for x in val]
		return r
	# @used-by :func:`agent_tools.upwork_data.canonical_job_url()`
	# @used-by :meth:`Df.Harness.Upwork.ClientMetadataExtractor.ClientMetadataExtractor.__collect_group()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__build_result()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__fetch_related_jobs()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__resolve_target()`
	# @used-by :meth:`Df.Harness.Upwork.KbProjectMdFormatter.KbProjectMdFormatter.render()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectDirResolver.ProjectDirResolver.__matches_job()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__run_configure()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@classmethod
	def canonical_job_url(cls, url_or_id: str) -> str:
		return f'https://upwork.com/jobs/{cls.normalize_job_id(url_or_id)}'
	# @used-by :func:`agent_tools.upwork_data.extract_upwork_job_url_id()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@staticmethod
	def extract_upwork_job_url_id(url: str, *, allow_query_or_fragment: bool=False) -> str | None:
		r = None
		if isinstance(url, str) and url.strip():
			base, frag = urldefrag(url.strip())
			parsed = urlsplit(base)
			segments = parsed.path.split('/')
			ok_host = parsed.scheme.lower() in ('http', 'https') and (parsed.hostname or '').lower() in ('upwork.com', 'www.upwork.com')
			ok_path = (not parsed.username) and (not parsed.password) and ('.' not in segments) and ('..' not in segments)
			ok_qf = allow_query_or_fragment or ((not frag) and (not parsed.query))
			if ok_host and ok_path and ok_qf:
				m = re.match('^/(?:jobs/|freelance-jobs/(?:apply/)?)(?:[^/]*?_)?(~0[12][0-9a-zA-Z]+)/?$', parsed.path)
				if m:
					r = m.group(1)
		return r
	# @used-by :func:`agent_tools.upwork_data.normalize_job_id()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__fetch_related_jobs()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.extract()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectDirResolver.ProjectDirResolver.resolve_or_create()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.initialize()`
	# @used-by :meth:`Df.Harness.Upwork.TabSelector.TabSelector.__matches_job()`
	# @used-by :meth:`Df.Harness.Workflow.WorkflowResumer.WorkflowResumer.__apply()`
	# @used-by :meth:`JobUrlParser.canonical_job_url()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	# @used-by :meth:`test_resume_exports.ResumeExportTests.test_native_requests_preserve_exact_bytes_and_current_job_scope()`
	@staticmethod
	def normalize_job_id(url_or_id: str) -> str:
		match = re.search('(~0[12][0-9a-zA-Z]+)', url_or_id.strip())
		if not match:
			raise ValueError(f'Cannot extract Upwork job ID (~02...) from: {url_or_id}')
		return match.group(1)
	# @used-by :func:`agent_tools.upwork_data.resolve_nuxt_devalue()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__fetch_related_jobs()`
	# @used-by :meth:`Df.Harness.Upwork.PageDecoder.PageDecoder.decode()`
	# @used-by :meth:`JobUrlParser.__resolve_value()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@classmethod
	def resolve_nuxt_devalue(cls, arr: list, idx: int=0, seen: set[int] | None=None):
		seen_set = set() if None is seen else seen
		if not isinstance(idx, int) or 0 > idx or idx >= len(arr) or (idx in seen_set):
			r = arr[idx] if isinstance(idx, int) and 0 <= idx < len(arr) else idx
		else:
			r = cls.__resolve_value(arr, arr[idx], seen_set | {idx})
		return r
