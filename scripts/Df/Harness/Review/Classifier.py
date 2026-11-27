# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Analysis.Claim.NumericGrounding import NumericGrounding
from Df.Harness.Analysis.Claim.StandaloneNumberExtractor import StandaloneNumberExtractor
from Df.Harness.Review.ClaimEvidenceCollector import ClaimEvidenceCollector
from Df.Qa.lib.validation.check_strict import df_is_sne
from agent_tools.research import json_data
TASK_FLAGS = {'new_causal_analysis', 'architecture_change', 'pricing_change', 'admin_configuration', 'business_impact', 'material_analysis'}
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class Classifier:
	# @used-by :func:`agent_tools.review.classification()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.prepare()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.__validate_current()`
	# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_classifier_has_significant_flags_and_post_finalize_synthetic_claims()`
	def __init__(self, root, state: dict, value: dict, *, exclude_package=None, approved_fn=None) -> None:
		self.exclude_package = exclude_package
		self.is_finalized = 'complete' == state.get('stages', {}).get('finalize', {}).get('status')
		self.root = root
		self.state = state
		self.value = value
		self.__approved_fn = approved_fn
	# @used-by :meth:`Classifier.classify()`
	def __check_omitted(self, seen: set[str], previously_approved: set, risk: str) -> None:
		if not self.is_finalized:
			unreviewed = [c['id'] for s in ('causes', 'misconceptions', 'methods') for c in self.value.get(s) or [] if isinstance(c, dict) and df_is_sne(c.get('id')) and ((c['id'], ClaimEvidenceCollector.claim_digest(c)) not in previously_approved)]
			omitted = sorted(set(unreviewed) - seen)
			if omitted and 'routine' == risk:
				raise ValueError('Unjustified routine risk downgrade: unreviewed causes/misconceptions/methods claims in Analysis.json cannot be omitted from the review manifest (' + ', '.join(omitted) + ')')
	# @used-by :meth:`Classifier.__process_item()`
	def __evaluate_claim(self, ident: str, claim: dict, claim_section: str | None, restatement: bool, reasons: list[str], required_flags: set[str]) -> None:
		material = 'significant' == claim.get('materiality') or claim.get('impact', {}).get('severity') in ('high', 'critical')
		causal_sec = claim_section in ('causes', 'misconceptions')
		props = set(claim.get('properties', []))
		sig_kind = causal_sec or claim.get('category') in ('causal', 'architecture', 'pricing') or bool(props & {'causality', 'business_impact', 'admin_configuration', 'architecture_change', 'pricing_change'})
		if (not restatement) and (material or sig_kind):
			reasons.append(f"{ident}: new {claim.get('category')} claim ({claim.get('materiality')})")
			if material:
				required_flags.add('material_analysis')
			if causal_sec:
				required_flags.add('new_causal_analysis')
			for cat, prop, flag in (('causal', 'causality', 'new_causal_analysis'), ('architecture', 'architecture_change', 'architecture_change'), ('pricing', 'pricing_change', 'pricing_change')):
				if claim.get('category') == cat or prop in props:
					required_flags.add(flag)
			required_flags.update(props & {'admin_configuration', 'business_impact'})
	# @used-by :meth:`Classifier.classify()`
	def __process_item(self, item, risk: str, response: str, index: dict, sec_map: dict[str, str], prev_approved: set, seen: set[str], reasons: list[str], req_flags: set[str]) -> dict:
		if not isinstance(item, dict) or not df_is_sne(item.get('claim_id')) or (item['claim_id'] not in index and (not self.is_finalized)):
			raise ValueError('Every response claim must identify a current Analysis claim')
		ident = item['claim_id']
		if ident in seen or not df_is_sne(item.get('response_excerpt')) or item['response_excerpt'] not in response:
			raise ValueError('Response manifest needs one exact nonempty response excerpt per claim')
		seen.add(ident)
		claim, claim_sec, sha = self.__resolve_claim(item, risk, index, sec_map)
		novelty = item.get('novelty', claim.get('novelty'))
		if novelty not in ('new', 'restatement'):
			raise ValueError('Response claim novelty must be new or restatement')
		restatement = 'restatement' == novelty and (ident, sha) in prev_approved
		self.__evaluate_claim(ident, claim, claim_sec, restatement, reasons, req_flags)
		return {'claim_id': ident, 'claim_sha256': sha, 'response_excerpt': item['response_excerpt'], 'novelty': novelty, 'previously_approved_restatement': restatement, 'materiality': claim.get('materiality'), 'category': claim.get('category'), 'properties': claim.get('properties'), 'knowledge_type': claim.get('knowledge_type'), 'verification_status': claim.get('verification_status'), 'essence': claim['essence']}
	# @used-by :meth:`Classifier.__process_item()`
	def __resolve_claim(self, item: dict, risk: str, index: dict, sec_map: dict[str, str]) -> tuple[dict, str | None, str]:
		ident = item['claim_id']
		if ident not in index:
			ess = str(item.get('essence') or item['response_excerpt']).strip()
			claim = {'id': ident, 'essence': ess, 'materiality': item.get('materiality') or ('significant' if 'significant' == risk else 'routine'), 'category': item.get('category') or 'descriptive', 'properties': list(item.get('properties') or []), 'knowledge_type': item.get('knowledge_type') or 'observation', 'verification_status': item.get('verification_status') or 'verified', 'novelty': item.get('novelty') or 'new'}
			r = (claim, None, item.get('claim_sha256') or df_sha256(json_data({'id': ident, 'essence': ess, 'response_excerpt': item['response_excerpt']})))
		else:
			claim = index[ident]
			nums = StandaloneNumberExtractor(item['response_excerpt']).extract()
			if nums:
				ungrounded = sorted(nums - NumericGrounding(claim, index).grounded_numbers())
				if ungrounded:
					raise ValueError(f'Response excerpt for {ident} contains numeric figures not grounded in the claim or its primary evidence: ' + ', '.join(ungrounded))
			r = (claim, sec_map.get(ident), ClaimEvidenceCollector.claim_digest(claim))
		return r
	# @used-by :meth:`Classifier.classify()`
	def __validate_spec(self, spec) -> tuple[list[str], list[str]]:
		if not isinstance(spec, dict) or spec.get('risk') not in ('routine', 'significant'):
			raise ValueError('Explicit review spec risk routine/significant is required; no default risk')
		if not df_is_sne(spec.get('basis')) or (not df_is_sne(spec.get('request_scope'))):
			raise ValueError('Review classification needs a substantive basis and current request_scope')
		flags = spec.get('task_flags')
		if not isinstance(flags, list) or any((not df_is_sne(x) or x not in TASK_FLAGS for x in flags)) or len(set(flags)) != len(flags):
			raise ValueError('Explicit unique task_flags list required: ' + ', '.join(sorted(TASK_FLAGS)) + ' (or [])')
		if not isinstance(spec.get('claim_ids'), list) or not spec['claim_ids'] or (not isinstance(spec.get('claims'), list)) or (not spec['claims']):
			raise ValueError('Analytical review requires nonempty claim_ids and response claims manifest')
		cids = spec['claim_ids']
		if any((not df_is_sne(x) for x in cids)) or len(set(cids)) != len(cids):
			raise ValueError('Review claim_ids must be unique existing claim IDs')
		return (flags, cids)
	# @used-by :func:`agent_tools.review.classification()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.prepare()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.__validate_current()`
	def classify(self, spec: dict, response: str) -> dict:
		from Df.Harness.Review.QuorumEvaluator import QuorumEvaluator
		flags, claim_ids = self.__validate_spec(spec)
		index = ClaimEvidenceCollector.claim_index(self.value)
		sec_map = ClaimEvidenceCollector.section_map(self.value)
		prev_approved = self.__approved_fn(self.root, self.state, exclude_package=self.exclude_package) if None is not self.__approved_fn else QuorumEvaluator(self.root, self.state).approved_claim_digests(exclude_package=self.exclude_package)
		manifest, seen, reasons, req_flags = ([], set(), [], set())
		for item in spec['claims']:
			manifest.append(self.__process_item(item, spec['risk'], response, index, sec_map, prev_approved, seen, reasons, req_flags))
		if set(claim_ids) != seen:
			raise ValueError('Classification claim_ids must equal the response manifest claim IDs')
		self.__check_omitted(seen, prev_approved, spec['risk'])
		minimum = 'significant' if reasons or flags else 'routine'
		if 'significant' == minimum and 'routine' == spec['risk']:
			raise ValueError('Unjustified routine risk downgrade: ' + '; '.join(reasons))
		if not req_flags.issubset(flags):
			raise ValueError('Task flags omit typed significant work: ' + ', '.join(sorted(req_flags - set(flags))))
		return {'risk': spec['risk'], 'minimum_risk': minimum, 'risk_basis': spec['basis'], 'risk_reasons': reasons, 'request_scope': spec['request_scope'], 'claims': manifest, 'task_flags': flags, 'minimum_task_flags': sorted(req_flags)}
	# @used-by :meth:`Df.Harness.Text.ReviewPreparer.ReviewPreparer.prepare()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_alignment_and_classifier_classes()`
	# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_classifier_has_significant_flags_and_post_finalize_synthetic_claims()`
	@staticmethod
	def has_significant_flags(claims, flags) -> bool:
		return any(('significant' == c.get('materiality') for c in claims)) or bool(set(flags) & TASK_FLAGS)
