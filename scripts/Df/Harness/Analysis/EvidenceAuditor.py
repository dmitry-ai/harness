# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Analysis.ClaimGraph import ClaimGraph
from Df.Harness.Analysis.LocalSourceResolver import LocalSourceResolver
from Df.Harness.Analysis.SavedQuoteVerifier import SavedQuoteVerifier
from Df.Harness.Analysis.SavedSourceLoader import SavedSourceLoader
from Df.Harness.Analysis.Validator import SECTIONS, Validator
from Df.Harness.Project.Diagnostics import Diagnostics
from agent_tools.research import load_observation
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class EvidenceAuditor:
	# @used-by :func:`agent_tools.evidence.evidence_issues()`
	# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.__validate_partial()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.save()`
	# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.__default_analysis()`
	# @used-by :meth:`Df.Harness.Review.PackageEnvelopeReader.PackageEnvelopeReader.load_analysis()`
	# @used-by :meth:`Df.Harness.Workflow.AnalysisCardAuditor.AnalysisCardAuditor.__init__()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def __init__(self, root, value, *, skip_structural: bool=False) -> None:
		self.__root = root
		self.__value = value
		self.__skip_structural = skip_structural
	# @used-by :meth:`EvidenceAuditor.issues()`
	def __check_arguments(self, out: list[dict]) -> None:
		for ident, field, argument, source in Validator.iter_arguments(self.__value):
			if not isinstance(source, str) or not isinstance(argument.get('quote'), str):
				continue
			exc_map = argument.get('anchor_exception') if isinstance(argument.get('anchor_exception'), dict) else {}
			try:
				SavedQuoteVerifier(self.__root, source, argument['quote'], mode=argument.get('quote_match', 'exact'), expected_hash=argument.get('source_sha256'), observation=argument.get('observation') or exc_map.get('observation'), documentation=bool(argument.get('documentation')), exception=exc_map).verify()
			except (OSError, ValueError, KeyError, IndexError, TypeError, UnicodeError) as exc:
				out.append(Diagnostics().problem('evidence.unconfirmed', field, str(exc), claim_id=ident, hint='Use the exact saved source and locator; keep the claim unverified until resolved'))
	# @used-by :meth:`EvidenceAuditor.__check_counterevidence()`
	def __check_claim_counter(self, section: str, index: int, claim: dict, out: list[dict]) -> None:
		gap = claim.get('counterevidence', {})
		reviewed = gap.get('reviewed_sources', []) if isinstance(gap, dict) else []
		for source in reviewed if isinstance(reviewed, list) else []:
			if isinstance(source, str):
				try:
					self.__check_counter_source(source, gap)
				except (OSError, ValueError, KeyError, TypeError) as exc:
					out.append(Diagnostics().problem('counterevidence.unconfirmed', f'/{section}/{index}/counterevidence', str(exc), claim_id=claim.get('id')))
	# @used-by :meth:`EvidenceAuditor.__check_claim_counter()`
	def __check_counter_source(self, source: str, gap: dict) -> None:
		if source.startswith(('http://', 'https://')):
			SavedSourceLoader(self.__root, source, need_sections=False).load()
		else:
			file = LocalSourceResolver(self.__root, source).resolve()
			if 'observation.json' != file.name and (not file.is_file()):
				raise FileNotFoundError(source)
			if 'observation.json' == file.name:
				obs = load_observation(self.__root, source)
				if 'not_found' == gap.get('status') and (obs.get('error') or ('http' == obs.get('kind', 'http') and (not 200 <= obs['status'] < 300))):
					raise ValueError('An unavailable observation establishes unavailable, not a completed search for counterevidence')
	# @used-by :meth:`EvidenceAuditor.issues()`
	def __check_counterevidence(self, out: list[dict]) -> None:
		for section in SECTIONS:
			items = self.__value.get(section, [])
			if isinstance(items, list):
				for index, claim in enumerate(items):
					if isinstance(claim, dict) and [] == claim.get('against'):
						self.__check_claim_counter(section, index, claim, out)
	# @used-by :func:`agent_tools.evidence.evidence_issues()`
	# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.__validate_partial()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.save()`
	# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.__default_analysis()`
	# @used-by :meth:`Df.Harness.Review.PackageEnvelopeReader.PackageEnvelopeReader.load_analysis()`
	# @used-by :meth:`Df.Harness.Workflow.AnalysisCardAuditor.AnalysisCardAuditor.__init__()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def issues(self) -> list[dict]:
		if not isinstance(self.__value, dict):
			r = [Diagnostics().problem('analysis.object', '/', 'Analysis must be a JSON object')]
		else:
			out: list[dict] = []
			self.__check_arguments(out)
			self.__check_counterevidence(out)
			out.extend(ClaimGraph(self.__value, root=self.__root).evidence_issues(skip_structural=self.__skip_structural))
			r = out
		return r