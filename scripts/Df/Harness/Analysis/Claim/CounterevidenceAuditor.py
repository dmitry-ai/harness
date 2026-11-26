# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Project.Diagnostics import Diagnostics
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class CounterevidenceAuditor:
	# @used-by :meth:`Df.Harness.Analysis.Claim.StructureAuditor.StructureAuditor.__check_causal_and_impact()`
	# @used-by :meth:`Df.Harness.Analysis.ClaimGraph.ClaimGraph.__check_deps_and_caps()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_remaining_edge_paths()`
	def __init__(self, issues: list[dict], seen: dict) -> None:
		self.__issues = issues
		self.__seen = seen
	# @used-by :meth:`CounterevidenceAuditor.__has_counter_obs()`
	def __for_sets(self, claim: dict) -> tuple[dict, set[str], set[str]]:
		ev_list = claim.get('evidence') if isinstance(claim.get('evidence'), list) else ()
		own_ev = {r['id']: r.get('kind') for r in ev_list if isinstance(r, dict) and isinstance(r.get('id'), str) and r['id'].strip()}
		for_list = claim.get('for') if isinstance(claim.get('for'), list) else ()
		for_ev = {a['evidence_id'] for a in for_list if isinstance(a, dict) and isinstance(a.get('evidence_id'), str) and a['evidence_id'].strip()}
		for_cl = {a['claim_id'] for a in for_list if isinstance(a, dict) and isinstance(a.get('claim_id'), str) and a['claim_id'].strip()}
		return (own_ev, for_ev, for_cl)
	# @used-by :meth:`CounterevidenceAuditor.check()`
	def __has_counter_obs(self, claim: dict, against: list) -> bool:
		own_ev, for_ev, for_cl = self.__for_sets(claim)
		r = False
		for arg in against:
			if isinstance(arg, dict):
				ev_id, c_id = (arg.get('evidence_id'), arg.get('claim_id'))
				if isinstance(ev_id, str) and ev_id.strip() and ev_id not in for_ev and own_ev.get(ev_id) in {'observation', 'experiment'}:
					r = True
					break
				if isinstance(c_id, str) and c_id.strip() and c_id not in for_cl and c_id in self.__seen and self.__seen[c_id][2].get('knowledge_type') in {'observation', 'calculation'}:
					r = True
					break
		return r
	# @used-by :meth:`Df.Harness.Analysis.Claim.StructureAuditor.StructureAuditor.__check_causal_and_impact()`
	# @used-by :meth:`Df.Harness.Analysis.ClaimGraph.ClaimGraph.__check_deps_and_caps()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_remaining_edge_paths()`
	def check(self, field: str, section: str, claim: dict) -> None:
		against = claim.get('against')
		prob = claim.get('probability_percent')
		if 'hypothesis' == claim.get('knowledge_type') and 'verified' != claim.get('verification_status') and isinstance(against, list) and isinstance(prob, int) and 75 < prob:
			is_causal = section in ('causes', 'misconceptions') or 'causal' == claim.get('category')
			if not against and (is_causal or bool(claim.get('alternative_explanations'))):
				self.__issues.append(Diagnostics().problem('claim.counterevidence', field + '/probability_percent', 'An unverified or limited hypothesis with competing alternatives and no against arguments cannot exceed 75% probability; include counter-arguments from plausible alternatives or lower the probability', claim_id=claim.get('id')))
			elif against and is_causal and self.__seen.get(claim.get('id')) == (field, section, claim) and (not self.__has_counter_obs(claim, against)):
				self.__issues.append(Diagnostics().problem('claim.counterevidence', field + '/probability_percent', 'An unverified causal or misconception hypothesis above 75% requires genuine observation/experiment counter-evidence in against (citing only client intake or reusing for-premises does not lift the 75% cap)', claim_id=claim.get('id')))