# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from urllib.parse import urldefrag
from Df.Harness.Analysis.Claim.CalculationContract import CalculationContract
from Df.Harness.Analysis.Claim.ComparisonContract import ComparisonContract
from Df.Harness.Analysis.Claim.CounterevidenceAuditor import CounterevidenceAuditor
from Df.Harness.Analysis.Claim.InlineCalcVerifier import InlineCalcVerifier
from Df.Harness.Analysis.Claim.SourceNumericTokenizer import SourceNumericTokenizer
from Df.Harness.Analysis.Claim.StandaloneNumberExtractor import StandaloneNumberExtractor
from Df.Harness.Project.Diagnostics import Diagnostics
import re
KINDS = {'observation', 'client_report', 'hypothesis', 'recommendation', 'calculation'}
STATUSES = {'verified', 'limited', 'unverified', 'unavailable', 'stale'}
PROPERTIES = {'content', 'markup', 'dom', 'interaction', 'currency_transition', 'ip_country', 'admin_configuration', 'serp', 'platform_capability', 'calculation', 'comparison', 'modification', 'causality', 'business_impact', 'architecture_change', 'pricing_change'}
HASH = re.compile('^[a-f0-9]{64}$')
ID = re.compile('^[A-Z][A-Z0-9-]*$')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class StructureAuditor:
	# @used-by :meth:`Df.Harness.Analysis.ClaimGraph.ClaimGraph.structural_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	def __init__(self, value: dict, locations: list, issues: list[dict]) -> None:
		self.__value = value
		self.__locations = locations
		self.__issues = issues
		self.seen: dict = {}
		self.__ev_ids: set[str] = set()
	# @used-by :meth:`StructureAuditor.__check_arg_entry()`
	# @used-by :meth:`StructureAuditor.__check_basic()`
	# @used-by :meth:`StructureAuditor.__check_causal_and_impact()`
	# @used-by :meth:`StructureAuditor.__check_deps()`
	# @used-by :meth:`StructureAuditor.__check_deps_and_ev()`
	# @used-by :meth:`StructureAuditor.__check_impact_and_ops()`
	# @used-by :meth:`StructureAuditor.__check_kind_rules()`
	# @used-by :meth:`StructureAuditor.__check_numbers()`
	# @used-by :meth:`StructureAuditor.__check_one_ev_extra()`
	# @used-by :meth:`StructureAuditor.__check_one_evidence()`
	# @used-by :meth:`StructureAuditor.__check_scope_and_props()`
	# @used-by :meth:`StructureAuditor.check()`
	def __add(self, code: str, field: str, message: str, claim=None) -> None:
		self.__issues.append(Diagnostics().problem(code, field, message, claim_id=claim.get('id') if claim else None))
	# @used-by :meth:`StructureAuditor.__check_arguments()`
	def __arg_sets(self, claim: dict, evidence) -> tuple[set[str], set[str], set[str]]:
		deps = claim.get('derived_from', []) if isinstance(claim.get('derived_from'), list) else ()
		dep_ids = {x['claim_id'] for x in deps if isinstance(x, dict) and self.__text(x.get('claim_id'))}
		own_ev = {x['id'] for x in (evidence if isinstance(evidence, list) else ()) if isinstance(x, dict) and self.__text(x.get('id'))}
		for_list = claim.get('for') if isinstance(claim.get('for'), list) else ()
		for_ev = {a['evidence_id'] for a in for_list if isinstance(a, dict) and self.__text(a.get('evidence_id'))}
		return (dep_ids, own_ev, for_ev)
	# @used-by :meth:`StructureAuditor.__check_arguments()`
	def __check_arg_entry(self, field: str, side: str, number: int, arg, claim: dict, dep_ids: set[str], own_ev: set[str], for_ev: set[str]) -> None:
		if isinstance(arg, dict):
			if 'against' == side and (not arg.get('claim_id')) and self.__text(arg.get('evidence_id')) and arg['evidence_id'] in own_ev and arg['evidence_id'] in for_ev:
				self.__add('argument.contradictory_reuse', field + f'/against/{number}', 'An against argument cannot reuse the exact same evidence_id as a for argument on the same claim', claim)
			elif (not arg.get('claim_id')) and (not self.__text(arg.get('evidence_id')) or arg['evidence_id'] not in own_ev):
				self.__add('argument.primary', field + f'/{side}/{number}', 'Direct arguments must identify their own primary evidence_id, or use a versioned claim_id', claim)
			elif arg.get('claim_id') and (not self.__text(arg['claim_id']) or arg['claim_id'] not in dep_ids):
				self.__add('argument.dependency', field + f'/{side}/{number}', 'A claim argument must name a versioned derived_from dependency', claim)
			if (arg.get('claim_id') or arg.get('evidence_id')) and any((k in arg for k in ('source', 'source_id', 'quote', 'observation'))):
				self.__add('argument.competing_reference', field + f'/{side}/{number}', 'Resolve the referenced claim/evidence instead of supplying competing source prose', claim)
	# @used-by :meth:`StructureAuditor.__check_claim()`
	def __check_arguments(self, field: str, claim: dict, evidence) -> None:
		dep_ids, own_ev, for_ev = self.__arg_sets(claim, evidence)
		for side in ('for', 'against'):
			items = claim.get(side, [])
			if isinstance(items, list):
				for num, arg in enumerate(items):
					self.__check_arg_entry(field, side, num, arg, claim, dep_ids, own_ev, for_ev)
	# @used-by :meth:`StructureAuditor.__check_claim()`
	def __check_basic(self, field: str, section: str, claim: dict) -> None:
		ident = claim.get('id')
		if not self.__text(ident) or not ID.fullmatch(ident) or ident in self.seen:
			self.__add('claim.id', field + '/id', 'Invalid or duplicate claim ID across facts and all five stages', claim)
		else:
			self.seen[ident] = (field, section, claim)
		for key in ('essence', 'assessment_basis'):
			if not self.__text(claim.get(key)):
				self.__add('claim.required', field + '/' + key, key + ' is required', claim)
		if not self.__enum(claim.get('knowledge_type'), KINDS):
			self.__add('claim.knowledge_type', field + '/knowledge_type', 'Choose an explicit observation, client_report, hypothesis, recommendation or calculation', claim)
		if not self.__enum(claim.get('verification_status'), STATUSES):
			self.__add('claim.verification_status', field + '/verification_status', 'Choose verified, limited, unverified, unavailable or stale', claim)
		self.__check_kind_rules(field, section, claim)
	# @used-by :meth:`StructureAuditor.__check_claim()`
	def __check_causal_and_impact(self, field: str, section: str, claim: dict, evidence) -> None:
		if 'causal' == claim.get('category') or section in ('causes', 'misconceptions'):
			if not self.__strings(claim.get('alternative_explanations'), nonempty=True) or not self.__text(claim.get('discriminating_check')):
				self.__add('claim.causal', field, 'Causal and misconception explanations need plausible alternatives and a check that distinguishes them', claim)
		if self.seen.get(claim.get('id')) != (field, section, claim):
			CounterevidenceAuditor(self.__issues, self.seen).check(field, section, claim)
		if 'recommendation' == claim.get('knowledge_type') and (not self.__strings(claim.get('applicability'), nonempty=True) or not self.__text(claim.get('validation'))):
			self.__add('claim.recommendation', field, 'Recommendations need applicability conditions and an outcome validation plan', claim)
		self.__check_impact_and_ops(field, claim, evidence)
	# @used-by :meth:`StructureAuditor.check()`
	def __check_claim(self, field: str, section: str, claim: dict) -> None:
		self.__check_basic(field, section, claim)
		self.__check_scope_and_props(field, claim)
		evidence = self.__check_deps_and_ev(field, claim)
		self.__check_numbers(field, claim, evidence)
		self.__check_causal_and_impact(field, section, claim, evidence)
		self.__check_arguments(field, claim, evidence)
	# @used-by :meth:`StructureAuditor.__check_deps_and_ev()`
	def __check_deps(self, field: str, claim: dict):
		deps = claim.get('derived_from')
		if not isinstance(deps, list):
			self.__add('claim.dependencies', field + '/derived_from', 'Record dependency IDs with exact claim sha256 revisions', claim)
		else:
			used: set[str] = set()
			for num, dep in enumerate(deps):
				if not isinstance(dep, dict) or not self.__text(dep.get('claim_id')) or (not self.__hash(dep.get('sha256'))):
					self.__add('claim.dependency', field + f'/derived_from/{num}', 'A dependency needs claim_id and canonical claim sha256', claim)
				elif dep['claim_id'] in used:
					self.__add('claim.dependency', field + f'/derived_from/{num}', 'Duplicate dependency', claim)
				else:
					used.add(dep['claim_id'])
		return deps
	# @used-by :meth:`StructureAuditor.__check_claim()`
	def __check_deps_and_ev(self, field: str, claim: dict):
		deps = self.__check_deps(field, claim)
		evidence = claim.get('evidence')
		if not isinstance(evidence, list):
			self.__add('claim.evidence', field + '/evidence', 'Record a list of primary references; KB prose is not primary evidence', claim)
		else:
			for num, ref in enumerate(evidence):
				self.__check_one_evidence(field + f'/evidence/{num}', ref, claim)
		if 'unavailable' != claim.get('verification_status') and (not evidence) and (not deps):
			self.__add('claim.unsourced', field, 'A claim must trace to primary evidence through evidence or versioned dependencies', claim)
		return evidence
	# @used-by :meth:`StructureAuditor.__check_causal_and_impact()`
	def __check_impact_and_ops(self, field: str, claim: dict, evidence) -> None:
		impact = claim.get('impact')
		if not isinstance(impact, dict) or not self.__enum(impact.get('severity'), {'unknown', 'low', 'medium', 'high', 'critical'}) or (not self.__text(impact.get('basis'))) or (not self.__strings(impact.get('evidence_claim_ids'))):
			self.__add('claim.impact', field + '/impact', 'Impact needs severity, substantive basis and evidence_claim_ids (empty if unknown)', claim)
		elif impact['severity'] in {'high', 'critical'} and (not impact['evidence_claim_ids']):
			self.__add('claim.impact_evidence', field + '/impact', 'High/critical impact needs versioned evidence claims, not only an adjective', claim)
		props = claim.get('properties') if isinstance(claim.get('properties'), list) else []
		if 'calculation' == claim.get('knowledge_type') or 'calculation' in props:
			self.__issues.extend(CalculationContract(claim.get('calculation'), field + '/calculation', claim).issues())
		if None is not claim.get('comparison') or ('verified' == claim.get('verification_status') and {'modification', 'comparison'}.intersection(props)):
			self.__issues.extend(ComparisonContract(claim.get('comparison'), field + '/comparison', claim, evidence).issues())
	# @used-by :meth:`StructureAuditor.__check_basic()`
	def __check_kind_rules(self, field: str, section: str, claim: dict) -> None:
		if 'facts' == section and (not self.__enum(claim.get('knowledge_type'), {'observation', 'client_report', 'calculation'})):
			self.__add('fact.knowledge_type', field, 'A fact is an observation, attributed client report or calculation; hypotheses belong to the five stages', claim)
		if 'methods' == section and 'recommendation' != claim.get('knowledge_type'):
			self.__add('method.knowledge_type', field, 'Solution methods are recommendations with conditions and a validation plan', claim)
		if 'hypothesis' == claim.get('knowledge_type') and 'verified' == claim.get('verification_status'):
			self.__add('hypothesis.status', field, 'An unproved explanation remains a hypothesis; a score cannot make it verified', claim)
		for key, allowed in (('materiality', {'routine', 'significant'}), ('novelty', {'new', 'restatement'}), ('category', {'descriptive', 'causal', 'architecture', 'pricing', 'interaction'})):
			if not self.__enum(claim.get(key), allowed):
				self.__add('claim.' + key, field + '/' + key, 'Choose one of: ' + ', '.join(sorted(allowed)), claim)
	# @used-by :meth:`StructureAuditor.__check_claim()`
	def __check_numbers(self, field: str, claim: dict, evidence) -> None:
		deps = claim.get('derived_from', []) if isinstance(claim.get('derived_from'), list) else []
		if 'verified' == claim.get('verification_status') and self.__enum(claim.get('knowledge_type'), {'observation', 'client_report'}) and (not claim.get('calculation')) and (not deps) and isinstance(evidence, list) and evidence:
			essence_nums = StandaloneNumberExtractor(claim.get('essence', '')).extract()
			ev_corpus = '\n'.join((str(ref.get('quote', '')) + '\n' + str((ref.get('locator') or {}).get('value', '')) for ref in evidence if isinstance(ref, dict)))
			ev_nums = SourceNumericTokenizer(ev_corpus).tokenize()
			derived_ok, calc_errs = InlineCalcVerifier(claim.get('essence', ''), ev_nums).extract()
			ev_nums.update(derived_ok)
			for c_err in calc_errs:
				self.__add('calculation.unconfirmed', field + '/essence', c_err, claim)
			ungrounded = sorted(essence_nums - ev_nums)
			if ungrounded:
				self.__add('claim.ungrounded_number', field + '/essence', 'Verified observation/client_report essence contains numeric figures absent from its primary evidence quotes: ' + ', '.join(ungrounded), claim)
	# @used-by :meth:`StructureAuditor.__check_one_evidence()`
	def __check_one_ev_extra(self, ef: str, ref: dict, locator, claim: dict) -> None:
		if 'documentation' in ref and bool is not type(ref['documentation']):
			self.__add('documentation.type', ef + '/documentation', 'documentation must be an explicit boolean', claim)
		if ref.get('documentation') and self.__text(ref.get('source')) and (not urldefrag(ref['source'])[1]):
			exc = ref.get('anchor_exception')
			if isinstance(locator, dict) and 'anchor' == locator.get('type'):
				self.__add('documentation.locator', ef + '/source', 'Put the available documentation section anchor in the source URL itself', claim)
			elif not isinstance(exc, dict) or not all((self.__text(exc.get(k)) for k in ('section', 'observation'))):
				self.__add('documentation.locator', ef + '/anchor_exception', 'Documentation needs its section anchor URL or a named section and saved no-anchor observation', claim)
		if 'observation' == ref.get('kind') and (not self.__text(ref.get('observation'))):
			self.__add('primary.observation', ef, 'Observation metadata reference is required', claim)
		if 'experiment' == ref.get('kind') and (not self.__text(ref.get('experiment')) or not self.__text(ref.get('artifact_id'))):
			self.__add('primary.experiment', ef, 'Experiment and exact artifact_id are required', claim)
		if self.__enum(ref.get('kind'), {'intake', 'attachment'}) and (not self.__text(ref.get('manifest'))):
			self.__add('primary.manifest', ef, 'Bind intake/attachment bytes to the saved project snapshot or intake manifest', claim)
	# @used-by :meth:`StructureAuditor.__check_deps_and_ev()`
	def __check_one_evidence(self, ef: str, ref, claim: dict) -> None:
		if not isinstance(ref, dict):
			self.__add('primary.reference', ef, 'A primary reference must be an object', claim)
		else:
			if not self.__text(ref.get('id')) or ref['id'] in self.__ev_ids:
				self.__add('primary.id', ef + '/id', 'Evidence IDs must be nonempty and unique in this analysis', claim)
			else:
				self.__ev_ids.add(ref['id'])
			if not self.__enum(ref.get('kind'), {'observation', 'intake', 'attachment', 'experiment'}):
				self.__add('primary.kind', ef + '/kind', 'Primary evidence needs observation, intake, attachment or experiment provenance', claim)
			if not self.__text(ref.get('source')) or not self.__text(ref.get('quote')) or (not self.__hash(ref.get('source_sha256'))):
				self.__add('primary.source', ef, 'Supply exact source, quote and source_sha256', claim)
			loc = ref.get('locator')
			if not isinstance(loc, dict) or not self.__enum(loc.get('type'), {'text', 'json_pointer', 'anchor', 'lines'}) or (not self.__text(loc.get('value'))):
				self.__add('primary.locator', ef + '/locator', 'Use an exact text, JSON pointer, anchor or line-range locator', claim)
			self.__check_one_ev_extra(ef, ref, loc, claim)
	# @used-by :meth:`StructureAuditor.__check_claim()`
	def __check_scope_and_props(self, field: str, claim: dict) -> None:
		scope = claim.get('scope')
		if not isinstance(scope, dict) or not self.__text(scope.get('description')) or (not self.__strings(scope.get('sample'))) or (not self.__strings(scope.get('limitations'))):
			self.__add('claim.scope', field + '/scope', 'Scope needs description, sampled objects and explicit limitations lists', claim)
		elif 'verified' == claim.get('verification_status') and (not scope['sample']):
			self.__add('claim.scope', field + '/scope/sample', 'A verified claim must identify the objects actually examined', claim)
		props = claim.get('properties')
		if not self.__strings(props, nonempty=True) or any((x not in PROPERTIES for x in props)):
			self.__add('claim.properties', field + '/properties', 'List supported property types: ' + ', '.join(sorted(PROPERTIES)), claim)
		elif {'architecture_change', 'pricing_change'}.intersection(props) and 'recommendation' != claim.get('knowledge_type'):
			self.__add('claim.action_property', field + '/properties', 'Architecture/pricing changes are conditional recommendations', claim)
		checks = claim.get('missing_checks')
		if not self.__strings(checks):
			self.__add('claim.missing_checks', field + '/missing_checks', 'List missing checks explicitly, including an empty list when resolved', claim)
		elif self.__enum(claim.get('verification_status'), {'limited', 'unverified', 'unavailable', 'stale'}) and (not checks):
			self.__add('claim.missing_checks', field + '/missing_checks', 'An incomplete or stale claim needs actionable missing checks', claim)
		elif 'verified' == claim.get('verification_status') and checks:
			self.__add('claim.verified_gap', field, 'A claim with unresolved required checks cannot be verified', claim)
	# @used-by :meth:`StructureAuditor.__check_basic()`
	# @used-by :meth:`StructureAuditor.__check_impact_and_ops()`
	# @used-by :meth:`StructureAuditor.__check_kind_rules()`
	# @used-by :meth:`StructureAuditor.__check_numbers()`
	# @used-by :meth:`StructureAuditor.__check_one_ev_extra()`
	# @used-by :meth:`StructureAuditor.__check_one_evidence()`
	# @used-by :meth:`StructureAuditor.__check_scope_and_props()`
	def __enum(self, value, allowed) -> bool:
		return isinstance(value, str) and value in allowed
	# @used-by :meth:`StructureAuditor.__check_deps()`
	# @used-by :meth:`StructureAuditor.__check_one_evidence()`
	def __hash(self, value) -> bool:
		return isinstance(value, str) and None is not HASH.fullmatch(value)
	# @used-by :meth:`StructureAuditor.__check_causal_and_impact()`
	# @used-by :meth:`StructureAuditor.__check_impact_and_ops()`
	# @used-by :meth:`StructureAuditor.__check_scope_and_props()`
	def __strings(self, value, *, nonempty: bool=False) -> bool:
		return isinstance(value, list) and (bool(value) or not nonempty) and all((self.__text(x) for x in value))
	# @used-by :meth:`StructureAuditor.__arg_sets()`
	# @used-by :meth:`StructureAuditor.__check_arg_entry()`
	# @used-by :meth:`StructureAuditor.__check_basic()`
	# @used-by :meth:`StructureAuditor.__check_causal_and_impact()`
	# @used-by :meth:`StructureAuditor.__check_deps()`
	# @used-by :meth:`StructureAuditor.__check_impact_and_ops()`
	# @used-by :meth:`StructureAuditor.__check_one_ev_extra()`
	# @used-by :meth:`StructureAuditor.__check_one_evidence()`
	# @used-by :meth:`StructureAuditor.__check_scope_and_props()`
	# @used-by :meth:`StructureAuditor.__strings()`
	def __text(self, value) -> bool:
		return isinstance(value, str) and bool(value.strip())
	# @used-by :meth:`Df.Harness.Analysis.ClaimGraph.ClaimGraph.structural_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	def check(self) -> dict:
		if not isinstance(self.__value.get('facts'), list):
			self.__add('facts.list', '/facts', 'Version 3 requires first-class facts, including an explicit empty list')
		else:
			for num, item in enumerate(self.__value['facts']):
				if not isinstance(item, dict):
					self.__add('claim.object', f'/facts/{num}', 'Each fact must be an object')
		for field, section, claim in self.__locations:
			self.__check_claim(field, section, claim)
		return self.seen