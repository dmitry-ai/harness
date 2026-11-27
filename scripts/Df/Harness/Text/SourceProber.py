# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import urldefrag
from Df.Harness.Research.Collector import Collector
from Df.Harness.Text.Finding import Finding
from Df.Harness.lib.research import dfh_json_data
from Df.Harness.lib.text_claims import dfh_text_digest
from Df.Harness.lib.text_sources import dfh_source_attempt, dfh_source_urls
from Df.Harness.lib.text_workflow import dfh_text_folder
from agent_tools.storage import write_immutable_bytes
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class SourceProber:
	# @used-by :func:`agent_tools.text_sources.probe_links()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__handle_lint()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_claims_sources_and_cli_runner_classes()`
	def __init__(self, root, candidate: str, *, fetcher=None) -> None:
		self.__root = root
		self.__candidate = candidate
		self.__fetcher = fetcher
	# @used-by :func:`agent_tools.text_sources.probe_links()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__handle_lint()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_claims_sources_and_cli_runner_classes()`
	def probe(self) -> dict:
		from agent_tools.evidence_loader import probe_observation_status
		observed, results, findings = ({}, [], [])
		for url in dfh_source_urls(self.__candidate):
			base, fragment = urldefrag(url)
			if base not in observed:
				observed[base] = Collector(self.__root, base, scope='client-text-source', max_age=0, refresh_reason='Explicit network check of the exact client-text candidate', fetcher=self.__fetcher).collect()
			meta = observed[base]
			status = probe_observation_status(self.__root, meta, base, fragment)
			result = {'url': url, 'status': status, 'observation': meta['observation'], 'final_url': meta['final_url'], 'http_status': meta['status']}
			raw = dfh_json_data({'schema_version': 1, 'candidate_sha256': dfh_text_digest(self.__candidate.encode()), **result})
			path = write_immutable_bytes(dfh_text_folder(self.__root) / 'sources' / (dfh_text_digest(raw) + '-probe.json'), raw, diff_error='Immutable source probe differs')
			reference = path.relative_to(Path(self.__root).resolve()).as_posix()
			dfh_source_attempt(self.__root, self.__candidate, url, meta['observation'], reference)
			results.append({**result, 'probe': reference})
			if 'http-ok' != status:
				findings.append(Finding('error', 'SOURCE-UNVERIFIED', 1, url + ': ' + status))
		return {'results': results, 'findings': findings}
