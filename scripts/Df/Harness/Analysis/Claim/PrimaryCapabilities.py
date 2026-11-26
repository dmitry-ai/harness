# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from urllib.parse import urldefrag, urlsplit
from Df.Harness.Analysis.Claim.ManifestPrimaryVerifier import ManifestPrimaryVerifier
from Df.Harness.Analysis.LocalSourceResolver import LocalSourceResolver
from Df.Harness.Analysis.SavedQuoteVerifier import SavedQuoteVerifier
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class PrimaryCapabilities:
	# @used-by :func:`agent_tools.claims._primary_capabilities()`
	# @used-by :meth:`Df.Harness.Analysis.ClaimGraph.ClaimGraph.__load_one_ref()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
	def __init__(self, root, ref: dict) -> None:
		self.__root = root
		self.__ref = ref
	# @used-by :meth:`PrimaryCapabilities.resolve()`
	def __resolve_experiment(self) -> tuple[set[str], dict]:
		from Df.Harness.Experiment.RunLoader import RunLoader
		exp = RunLoader(self.__root, self.__ref['experiment']).load_run()
		asset = next((a for a in exp.get('artifacts', []) if a.get('id') == self.__ref['artifact_id']), None)
		if not asset or LocalSourceResolver(self.__root, asset['path']).resolve() != LocalSourceResolver(self.__root, self.__ref['source']).resolve() or asset.get('sha256') != self.__ref['source_sha256']:
			raise ValueError('Experiment source must be the exact recorded artifact and hash')
		return (set(exp.get('capabilities', [])), self.__verify_quote())
	# @used-by :meth:`PrimaryCapabilities.__resolve_experiment()`
	# @used-by :meth:`PrimaryCapabilities.resolve()`
	def __verify_quote(self, *, observation=None) -> dict:
		loc = self.__ref['locator']
		return SavedQuoteVerifier(self.__root, self.__with_locator(self.__ref['source'], loc), self.__ref['quote'], mode=self.__ref.get('quote_match', 'exact'), expected_hash=self.__ref['source_sha256'], require_hash=True, observation=observation, documentation=bool(self.__ref.get('documentation')), exception=self.__ref.get('anchor_exception', {}), locator=loc, require_bound_observation=True, hash_error='Primary source bytes changed from source_sha256', absent_error='Exact quote is absent from the located primary source').verify()
	# @used-by :meth:`PrimaryCapabilities.__verify_quote()`
	def __with_locator(self, source: str, locator: dict) -> str:
		base, fragment = urldefrag(source)
		if locator['type'] not in {'anchor', 'json_pointer'}:
			if fragment:
				raise ValueError('A fragment source needs an anchor or json_pointer locator')
			r = base
		else:
			if fragment and fragment != locator['value']:
				raise ValueError('Source fragment and explicit locator disagree')
			r = base + '#' + locator['value']
		return r
	# @used-by :func:`agent_tools.claims._primary_capabilities()`
	# @used-by :meth:`Df.Harness.Analysis.ClaimGraph.ClaimGraph.__load_one_ref()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
	def resolve(self) -> tuple[set[str], dict]:
		kind = self.__ref['kind']
		if 'observation' == kind:
			from agent_tools.research import load_observation, observation_capabilities
			meta = load_observation(self.__root, self.__ref['observation'])
			if urlsplit(self.__ref['source']).scheme.lower() not in {'http', 'https'}:
				raise ValueError('An observation primary source must name its captured HTTP(S) URL')
			r = (set(observation_capabilities(meta)), self.__verify_quote(observation=self.__ref['observation']))
		elif 'experiment' != kind:
			r = (ManifestPrimaryVerifier(self.__root, self.__ref).verify(), self.__verify_quote())
		else:
			r = self.__resolve_experiment()
		return r