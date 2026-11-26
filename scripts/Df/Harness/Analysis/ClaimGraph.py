# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from decimal import InvalidOperation
from pathlib import Path
from Df.Harness.Analysis.Claim.CalculationValidator import CalculationValidator
from Df.Harness.Analysis.Claim.ComparisonValidator import ComparisonValidator
from Df.Harness.Analysis.Claim.CounterevidenceAuditor import CounterevidenceAuditor
from Df.Harness.Analysis.Claim.PrimaryCapabilities import PrimaryCapabilities
from Df.Harness.Analysis.Claim.ScopeCoverageAuditor import ScopeCoverageAuditor
from Df.Harness.Analysis.Claim.StructureAuditor import StructureAuditor
from Df.Harness.Project.Diagnostics import Diagnostics
import hashlib
import json
import re
_SECTIONS = ('identity', 'concerns', 'misconceptions', 'causes', 'methods')
_DNS_RE = re.compile('(?i)\\bgetaddrinfo\\b|\\bnxdomain\\b|\\u043d\\u0435\\s+\\u0440\\u0435\\u0437\\u043e\\u043b\\u0432\\u0438\\u0442\\u0441\\u044f(?:\\s+\\u043d\\u0430\\s+\\u0443\\u0440\\u043e\\u0432\\u043d\\u0435\\s+dns)?|dns\\s+(?:resolution\\s+failed|\\u043d\\u0435\\s+\\u0440\\u0435\\u0437\\u043e\\u043b\\u0432)')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ClaimGraph:
	# @used-by :func:`agent_tools.claims.contract_issues()`
	# @used-by :func:`agent_tools.claims.evidence_contract_issues()`
	# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.issues()`
	# @used-by :meth:`Df.Harness.Analysis.Validator.Validator.issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_remaining_edge_paths()`
	# @used-by :meth:`test_evidence_contract.ClaimGraphValidatorTests.test_claim_graph_validator_memoizes_diamond_dag_and_dns_cache()`
	def __init__(self, value, *, root=None) -> None:
		self.value = value
		self.root = root
		self.is_v3 = isinstance(value, dict) and 3 == value.get('schema_version')
		self.locations = self.__locations(value) if self.is_v3 else []
		self.index = {c['id']: c for _, _, c in self.locations if isinstance(c.get('id'), str) and c['id'].strip()}
		self.issues: list[dict] = []
		self.seen: dict = {}
		self.capabilities: dict = {}
		self.refs: dict = {}
		self.direct_obs_urls: dict = {}
		self.direct_obs_metas: dict = {}
		self.inherited_memo: dict = {}
		self.http_dns_error_cached: bool | None = None
	# @used-by :meth:`ClaimGraph.__check_deps_and_caps()`
	# @used-by :meth:`ClaimGraph.__check_one_dep()`
	# @used-by :meth:`ClaimGraph.__check_verified_claim()`
	# @used-by :meth:`ClaimGraph.__check_verified_deps()`
	# @used-by :meth:`ClaimGraph.__load_direct_evidence()`
	# @used-by :meth:`ClaimGraph.__load_one_ref()`
	# @used-by :meth:`ClaimGraph.__verify_claim_evidence()`
	# @used-by :meth:`ClaimGraph.__visit_cycle()`
	def __add(self, code: str, field: str, message: str, claim=None) -> None:
		self.issues.append(Diagnostics().problem(code, field, message, claim_id=claim.get('id') if claim else None))
	# @used-by :meth:`ClaimGraph.__check_deps_and_caps()`
	def __check_one_dep(self, field: str, claim: dict, dep, dep_ids: set[str]) -> None:
		if isinstance(dep, dict) and isinstance(dep.get('claim_id'), str) and dep['claim_id'].strip():
			dep_ids.add(dep['claim_id'])
			target = self.seen.get(dep['claim_id'])
			if None is target:
				self.__add('claim.reference', field + '/derived_from', 'Unknown dependency: ' + dep['claim_id'], claim)
			else:
				try:
					target_hash = hashlib.sha256(json.dumps(target[2], ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
				except (TypeError, ValueError):
					target_hash = None
				if dep.get('sha256') != target_hash:
					self.__add('claim.stale_dependency', field + '/derived_from', 'Dependency changed; reassess the dependent claim and record its new revision', claim)
				elif 'stale' == target[2].get('verification_status') and 'stale' != claim.get('verification_status'):
					self.__add('claim.stale_dependency', field + '/derived_from', 'A dependent claim must be reassessed after a stale premise', claim)
	# @used-by :meth:`ClaimGraph.structural_issues()`
	def __check_deps_and_caps(self) -> None:
		counter = CounterevidenceAuditor(self.issues, self.seen)
		for _, (field, section, claim) in self.seen.items():
			dep_ids: set[str] = set()
			deps = claim.get('derived_from', [])
			for dep in deps if isinstance(deps, list) else ():
				self.__check_one_dep(field, claim, dep, dep_ids)
			counter.check(field, section, claim)
			impact = claim.get('impact', {})
			ev_ids = impact.get('evidence_claim_ids', []) if isinstance(impact, dict) else []
			for ref in ev_ids if isinstance(ev_ids, list) else ():
				if not (isinstance(ref, str) and ref.strip()) or ref not in dep_ids:
					self.__add('claim.impact_reference', field + '/impact', 'Impact evidence must be a versioned derived_from dependency: ' + str(ref), claim)
	# @used-by :meth:`ClaimGraph.__verify_claim_evidence()`
	def __check_verified_claim(self, field: str, claim: dict, caps: set[str], obs_urls: set[str]) -> None:
		props = claim.get('properties', []) if isinstance(claim.get('properties'), list) else ()
		for prop in props:
			if prop not in {'calculation', 'comparison', 'modification'} and (not (isinstance(prop, str) and prop.strip()) or prop not in caps):
				self.__add('claim.method_insufficient', field + '/properties', 'Saved methods cannot verify property ' + str(prop) + '; keep a limited hypothesis and list the missing check', claim)
		self.__check_verified_deps(field, claim)
		if set(props) & {'content', 'markup', 'dom'} and obs_urls:
			ScopeCoverageAuditor(self.issues).check(field, claim, obs_urls)
	# @used-by :meth:`ClaimGraph.__check_verified_claim()`
	def __check_verified_deps(self, field: str, claim: dict) -> None:
		deps = claim.get('derived_from', [])
		for dep in deps if isinstance(deps, list) else ():
			cid = dep.get('claim_id') if isinstance(dep, dict) else None
			target = self.index.get(cid) if isinstance(cid, str) and cid.strip() else None
			if target and 'verified' != target.get('verification_status'):
				self.__add('claim.unverified_premise', field + '/derived_from', 'A verified conclusion cannot rely on an incomplete or hypothetical premise', claim)
	# @used-by :meth:`ClaimGraph.__verify_claim_evidence()`
	def __has_http_dns_error(self) -> bool:
		if None is self.http_dns_error_cached:
			found = False
			if self.root:
				http_root = Path(self.root).resolve() / '\ua616/KB/Evidence/HTTP'
				if http_root.is_dir():
					for obs_file in http_root.rglob('observation.json'):
						try:
							m = json.loads(obs_file.read_text(encoding='utf-8'))
							if 'dns_error' == m.get('error_kind') or False is m.get('dns_resolved'):
								found = True
								break
						except (OSError, ValueError):
							pass
			self.http_dns_error_cached = found
		return bool(self.http_dns_error_cached)
	# @used-by :meth:`ClaimGraph.__verify_claim_evidence()`
	def __inherited(self, ident: str, active: set[str] | None=None) -> tuple[set[str], set[str], list[dict]]:
		act = set() if None is active else active
		if ident in self.inherited_memo:
			r = self.inherited_memo[ident]
		elif ident in act or ident not in self.index:
			r = (set(), set(), [])
		else:
			next_act = act | {ident}
			caps, urls, metas = (set(self.capabilities.get(ident, set())), set(self.direct_obs_urls.get(ident, set())), list(self.direct_obs_metas.get(ident, [])))
			deps = self.index[ident].get('derived_from', [])
			for dep in deps if isinstance(deps, list) else ():
				if isinstance(dep, dict) and dep.get('claim_id') in self.index:
					dc, du, dm = self.__inherited(dep['claim_id'], next_act)
					caps.update(dc)
					urls.update(du)
					metas.extend(dm)
			r = (caps, urls, metas)
			if not act:
				self.inherited_memo[ident] = r
		return r
	# @used-by :meth:`ClaimGraph.evidence_issues()`
	def __load_direct_evidence(self) -> None:
		for field, _, claim in self.locations:
			ident = claim.get('id')
			if not (isinstance(ident, str) and ident.strip()):
				self.__add('primary.claim_id', field + '/id', 'Primary evidence needs a valid claim ID', claim)
			else:
				self.capabilities[ident], self.direct_obs_urls[ident], self.direct_obs_metas[ident] = (set(), set(), [])
				ev = claim.get('evidence', [])
				for num, ref in enumerate(ev if isinstance(ev, list) else ()):
					if isinstance(ref, dict):
						self.__load_one_ref(ident, field + f'/evidence/{num}', claim, ref)
	# @used-by :meth:`ClaimGraph.__load_direct_evidence()`
	def __load_one_ref(self, ident: str, ef: str, claim: dict, ref: dict) -> None:
		try:
			caps, saved = PrimaryCapabilities(self.root, ref).resolve()
			self.capabilities[ident].update(caps)
			self.refs[ref.get('id')] = (claim, ref, saved)
			if 'observation' == ref.get('kind'):
				self.direct_obs_urls[ident].add(ref.get('source', ''))
				if isinstance(saved, dict) and isinstance(saved.get('meta'), dict):
					self.direct_obs_metas[ident].append(saved['meta'])
		except (OSError, ValueError, KeyError, IndexError, TypeError, UnicodeError, ImportError) as exc:
			self.__add('primary.unconfirmed', ef, str(exc), claim)
	# @used-by :meth:`ClaimGraph.__init__()`
	def __locations(self, value: dict) -> list[tuple[str, str, dict]]:
		return [(f'/{sec}/{num}', sec, claim) for sec in ('facts', 'claims', *_SECTIONS) for num, claim in enumerate(value.get(sec, []) if isinstance(value.get(sec), list) else ()) if isinstance(claim, dict)]
	# @used-by :meth:`ClaimGraph.evidence_issues()`
	def __verify_claim_evidence(self, field: str, claim: dict) -> None:
		caps, obs_urls, obs_metas = self.__inherited(claim['id'])
		status = claim.get('verification_status')
		if _DNS_RE.search(str(claim.get('essence', '')) + ' ' + str(claim.get('assessment_basis', ''))) and (not any(('dns_error' == m.get('error_kind') or False is m.get('dns_resolved') for m in obs_metas))) and (not self.__has_http_dns_error()):
			self.__add('claim.unverified_dns', field + '/essence', 'Claim asserts DNS non-resolution (getaddrinfo/NXDOMAIN) without a saved observation showing error_kind == dns_error; distinguish TCP timeout from DNS failure', claim)
		if 'verified' == status:
			self.__check_verified_claim(field, claim, caps, obs_urls)
		props = claim.get('properties') or []
		if 'calculation' == claim.get('knowledge_type') or 'calculation' in props:
			try:
				CalculationValidator(claim, self.index, self.refs).check()
			except (ValueError, KeyError, TypeError, InvalidOperation, ZeroDivisionError) as exc:
				self.__add('calculation.unconfirmed', field + '/calculation', str(exc), claim)
		if None is not claim.get('comparison') or ('verified' == status and {'modification', 'comparison'}.intersection(props)):
			try:
				ComparisonValidator(claim, self.index, self.refs).check()
			except (ValueError, KeyError, TypeError) as exc:
				self.__add('comparison.unconfirmed', field + '/comparison', str(exc), claim)
	# @used-by :meth:`ClaimGraph.structural_issues()`
	def __visit_cycle(self, ident: str, visited: set[str], active: set[str]) -> None:
		if ident in active:
			self.__add('claim.cycle', self.seen[ident][0] + '/derived_from', 'Claim dependencies contain a cycle', self.seen[ident][2])
		elif ident not in visited and ident in self.seen:
			active.add(ident)
			deps = self.seen[ident][2].get('derived_from', [])
			for dep in deps if isinstance(deps, list) else ():
				if isinstance(dep, dict) and isinstance(dep.get('claim_id'), str) and dep['claim_id'].strip():
					self.__visit_cycle(dep['claim_id'], visited, active)
			active.remove(ident)
			visited.add(ident)
	# @used-by :func:`agent_tools.claims.evidence_contract_issues()`
	# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_remaining_edge_paths()`
	# @used-by :meth:`test_evidence_contract.ClaimGraphValidatorTests.test_claim_graph_validator_memoizes_diamond_dag_and_dns_cache()`
	def evidence_issues(self, *, skip_structural: bool=False) -> list[dict]:
		structural = [] if skip_structural or not self.is_v3 else self.structural_issues()
		if not self.is_v3 or structural:
			r = structural
		else:
			self.issues, self.capabilities, self.refs, self.direct_obs_urls, self.direct_obs_metas, self.inherited_memo = ([], {}, {}, {}, {}, {})
			self.__load_direct_evidence()
			for field, _, claim in self.locations:
				if isinstance(claim.get('id'), str) and claim['id'].strip():
					self.__verify_claim_evidence(field, claim)
			r = list(self.issues)
		return r
	# @used-by :func:`agent_tools.claims.contract_issues()`
	# @used-by :meth:`ClaimGraph.evidence_issues()`
	# @used-by :meth:`Df.Harness.Analysis.Validator.Validator.issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	# @used-by :meth:`test_evidence_contract.ClaimGraphValidatorTests.test_claim_graph_validator_memoizes_diamond_dag_and_dns_cache()`
	def structural_issues(self) -> list[dict]:
		self.issues, self.seen = ([], {})
		if self.is_v3:
			self.seen = StructureAuditor(self.value, self.locations, self.issues).check()
			self.__check_deps_and_caps()
			visited, active = (set(), set())
			for ident in self.seen:
				self.__visit_cycle(ident, visited, active)
		return list(self.issues)