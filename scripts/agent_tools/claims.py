# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract ClaimGraphValidator class and unify derived_from DAG traversals, numeric grounding, and primary quote verification across claims.py, text_claims.py, review.py, and evidence.py":
# https://github.com/dmitry-ai/harness/issues/62
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify quote normalization, MarkdownIt link/quote traversal, locale checks, numeric corpus tokenization, and Evidence loading across response_grounding.py, completion.py, source_grounding.py, claims.py, and review.py":
# https://github.com/dmitry-ai/harness/issues/59
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
# https://github.com/dmitry-ai/harness/issues/37
# 2026-11-06 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement structured fact-tuple ledger (facts.json) and symbolic AST arithmetic grounding":
# https://github.com/dmitry-ai/harness/issues/46
import ast
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path
from urllib.parse import urldefrag, urlsplit
import hashlib
import json
import re
import unicodedata
from .diagnostics import problem
SECTIONS = ('identity', 'concerns', 'misconceptions', 'causes', 'methods')
KINDS = {'observation', 'client_report', 'hypothesis', 'recommendation', 'calculation'}
STATUSES = {'verified', 'limited', 'unverified', 'unavailable', 'stale'}
PROPERTIES = {'content', 'markup', 'dom', 'interaction', 'currency_transition', 'ip_country', 'admin_configuration', 'serp', 'platform_capability', 'calculation', 'comparison', 'modification', 'causality', 'business_impact', 'architecture_change', 'pricing_change'}
HASH = re.compile('^[a-f0-9]{64}$')
ID = re.compile('^[A-Z][A-Z0-9-]*$')
class ClaimGraphValidator:
	def __init__(self, value, *, root=None):
		self.value = value
		self.root = root
		self.is_v3 = isinstance(value, dict) and 3 == value.get('schema_version')
		self.locations = list(claim_locations(value)) if self.is_v3 else []
		self.index = claim_index(value) if self.is_v3 else {}
		self.issues = []
		self.seen = {}
		self.evidence_ids = set()
		self.capabilities = {}
		self.refs = {}
		self.direct_obs_urls = {}
		self.direct_obs_metas = {}
		self.inherited_memo = {}
		self.http_dns_error_cached = None
	def _add(self, code, field, message, claim=None):
		self.issues.append(problem(code, field, message, claim_id=claim.get('id') if claim else None))
	def _check_claim_arguments(self, field, claim, evidence):
		dep_ids = {x.get('claim_id') for x in _dependencies(claim) if isinstance(x, dict) and _text(x.get('claim_id'))}
		own_evidence = {x.get('id') for x in (evidence if isinstance(evidence, list) else []) if isinstance(x, dict) and _text(x.get('id'))}
		for_evidence_ids = {arg.get('evidence_id') for arg in (claim.get('for') if isinstance(claim.get('for'), list) else []) if isinstance(arg, dict) and _text(arg.get('evidence_id'))}
		for side in ('for', 'against'):
			for number, arg in enumerate(claim.get(side, []) if isinstance(claim.get(side), list) else []):
				if not isinstance(arg, dict):
					continue
				if 'against' == side and (not arg.get('claim_id')) and _text(arg.get('evidence_id')) and (arg.get('evidence_id') in own_evidence) and (arg.get('evidence_id') in for_evidence_ids):
					self._add('argument.contradictory_reuse', field + f'/against/{number}', 'An against argument cannot reuse the exact same evidence_id as a for argument on the same claim', claim)
				elif not arg.get('claim_id') and (not _text(arg.get('evidence_id')) or arg.get('evidence_id') not in own_evidence):
					self._add('argument.primary', field + f'/{side}/{number}', 'Direct arguments must identify their own primary evidence_id, or use a versioned claim_id', claim)
				elif arg.get('claim_id') and (not _text(arg['claim_id']) or arg['claim_id'] not in dep_ids):
					self._add('argument.dependency', field + f'/{side}/{number}', 'A claim argument must name a versioned derived_from dependency', claim)
				if (arg.get('claim_id') or arg.get('evidence_id')) and any((k in arg for k in ('source', 'source_id', 'quote', 'observation'))):
					self._add('argument.competing_reference', field + f'/{side}/{number}', 'Resolve the referenced claim/evidence instead of supplying competing source prose', claim)
	def _check_claim_dependencies_and_caps(self):
		for _, (field, section, claim) in self.seen.items():
			dep_ids = set()
			for dep in _dependencies(claim):
				if not isinstance(dep, dict) or not _text(dep.get('claim_id')):
					continue
				dep_ids.add(dep['claim_id'])
				target = self.seen.get(dep['claim_id'])
				if None is target:
					self._add('claim.reference', field + '/derived_from', 'Unknown dependency: ' + dep['claim_id'], claim)
				else:
					try:
						target_hash = claim_digest(target[2])
					except (TypeError, ValueError):
						target_hash = None
					if dep.get('sha256') != target_hash:
						self._add('claim.stale_dependency', field + '/derived_from', 'Dependency changed; reassess the dependent claim and record its new revision', claim)
					elif 'stale' == target[2].get('verification_status') and 'stale' != claim.get('verification_status'):
						self._add('claim.stale_dependency', field + '/derived_from', 'A dependent claim must be reassessed after a stale premise', claim)
			self._check_counterevidence_cap(field, section, claim)
			impact = claim.get('impact', {})
			for ref in impact.get('evidence_claim_ids', []) if isinstance(impact, dict) and isinstance(impact.get('evidence_claim_ids'), list) else []:
				if not _text(ref) or ref not in dep_ids:
					self._add('claim.impact_reference', field + '/impact', 'Impact evidence must be a versioned derived_from dependency: ' + str(ref), claim)
	def _check_claim_structure(self, field, section, claim):
		ident = claim.get('id')
		if not _text(ident) or not ID.fullmatch(ident) or ident in self.seen:
			self._add('claim.id', field + '/id', 'Invalid or duplicate claim ID across facts and all five stages', claim)
		else:
			self.seen[ident] = (field, section, claim)
		for key in ('essence', 'assessment_basis'):
			if not _text(claim.get(key)):
				self._add('claim.required', field + '/' + key, key + ' is required', claim)
		if not _enum(claim.get('knowledge_type'), KINDS):
			self._add('claim.knowledge_type', field + '/knowledge_type', 'Choose an explicit observation, client_report, hypothesis, recommendation or calculation', claim)
		if not _enum(claim.get('verification_status'), STATUSES):
			self._add('claim.verification_status', field + '/verification_status', 'Choose verified, limited, unverified, unavailable or stale', claim)
		if 'facts' == section and (not _enum(claim.get('knowledge_type'), {'observation', 'client_report', 'calculation'})):
			self._add('fact.knowledge_type', field, 'A fact is an observation, attributed client report or calculation; hypotheses belong to the five stages', claim)
		if 'methods' == section and 'recommendation' != claim.get('knowledge_type'):
			self._add('method.knowledge_type', field, 'Solution methods are recommendations with conditions and a validation plan', claim)
		if 'hypothesis' == claim.get('knowledge_type') and 'verified' == claim.get('verification_status'):
			self._add('hypothesis.status', field, 'An unproved explanation remains a hypothesis; a score cannot make it verified', claim)
		for key, allowed in (('materiality', {'routine', 'significant'}), ('novelty', {'new', 'restatement'}), ('category', {'descriptive', 'causal', 'architecture', 'pricing', 'interaction'})):
			if not _enum(claim.get(key), allowed):
				self._add('claim.' + key, field + '/' + key, 'Choose one of: ' + ', '.join(sorted(allowed)), claim)
		scope = claim.get('scope')
		if not isinstance(scope, dict) or not _text(scope.get('description')) or (not _strings(scope.get('sample'))) or (not _strings(scope.get('limitations'))):
			self._add('claim.scope', field + '/scope', 'Scope needs description, sampled objects and explicit limitations lists', claim)
		elif 'verified' == claim.get('verification_status') and (not scope['sample']):
			self._add('claim.scope', field + '/scope/sample', 'A verified claim must identify the objects actually examined', claim)
		properties = claim.get('properties')
		if not _strings(properties, nonempty=True) or any((x not in PROPERTIES for x in properties)):
			self._add('claim.properties', field + '/properties', 'List supported property types: ' + ', '.join(sorted(PROPERTIES)), claim)
		elif {'architecture_change', 'pricing_change'}.intersection(properties) and 'recommendation' != claim.get('knowledge_type'):
			self._add('claim.action_property', field + '/properties', 'Architecture/pricing changes are conditional recommendations', claim)
		checks = claim.get('missing_checks')
		if not _strings(checks):
			self._add('claim.missing_checks', field + '/missing_checks', 'List missing checks explicitly, including an empty list when resolved', claim)
		elif _enum(claim.get('verification_status'), {'limited', 'unverified', 'unavailable', 'stale'}) and (not checks):
			self._add('claim.missing_checks', field + '/missing_checks', 'An incomplete or stale claim needs actionable missing checks', claim)
		elif 'verified' == claim.get('verification_status') and checks:
			self._add('claim.verified_gap', field, 'A claim with unresolved required checks cannot be verified', claim)
		dependencies = claim.get('derived_from')
		if not isinstance(dependencies, list):
			self._add('claim.dependencies', field + '/derived_from', 'Record dependency IDs with exact claim sha256 revisions', claim)
		else:
			used = set()
			for number, dep in enumerate(dependencies):
				if not isinstance(dep, dict) or not _text(dep.get('claim_id')) or (not _hash(dep.get('sha256'))):
					self._add('claim.dependency', field + f'/derived_from/{number}', 'A dependency needs claim_id and canonical claim sha256', claim)
				elif dep['claim_id'] in used:
					self._add('claim.dependency', field + f'/derived_from/{number}', 'Duplicate dependency', claim)
				else:
					used.add(dep['claim_id'])
		evidence = claim.get('evidence')
		if not isinstance(evidence, list):
			self._add('claim.evidence', field + '/evidence', 'Record a list of primary references; KB prose is not primary evidence', claim)
		else:
			self._check_primary_evidence_list(field, claim, evidence)
		if 'unavailable' != claim.get('verification_status') and (not evidence) and (not dependencies):
			self._add('claim.unsourced', field, 'A claim must trace to primary evidence through evidence or versioned dependencies', claim)
		if 'verified' == claim.get('verification_status') and _enum(claim.get('knowledge_type'), {'observation', 'client_report'}) and (not claim.get('calculation')) and (not _dependencies(claim)) and isinstance(evidence, list) and evidence:
			essence_nums = standalone_numbers(claim.get('essence', ''))
			ev_corpus = '\n'.join((str(ref.get('quote', '')) + '\n' + str((ref.get('locator') or {}).get('value', '')) for ref in evidence if isinstance(ref, dict)))
			ev_nums = source_numeric_tokens(ev_corpus)
			derived_ok, calc_errs = extract_verified_inline_calc_numbers(claim.get('essence', ''), ev_nums)
			ev_nums.update(derived_ok)
			for c_err in calc_errs:
				self._add('calculation.unconfirmed', field + '/essence', c_err, claim)
			ungrounded = sorted(essence_nums - ev_nums)
			if ungrounded:
				self._add('claim.ungrounded_number', field + '/essence', 'Verified observation/client_report essence contains numeric figures absent from its primary evidence quotes: ' + ', '.join(ungrounded), claim)
		if 'causal' == claim.get('category') or section in ('causes', 'misconceptions'):
			if not _strings(claim.get('alternative_explanations'), nonempty=True) or not _text(claim.get('discriminating_check')):
				self._add('claim.causal', field, 'Causal and misconception explanations need plausible alternatives and a check that distinguishes them', claim)
		if self.seen.get(ident) != (field, section, claim):
			self._check_counterevidence_cap(field, section, claim)
		if 'recommendation' == claim.get('knowledge_type'):
			if not _strings(claim.get('applicability'), nonempty=True) or not _text(claim.get('validation')):
				self._add('claim.recommendation', field, 'Recommendations need applicability conditions and an outcome validation plan', claim)
		impact = claim.get('impact')
		if not isinstance(impact, dict) or not _enum(impact.get('severity'), {'unknown', 'low', 'medium', 'high', 'critical'}) or (not _text(impact.get('basis'))) or (not _strings(impact.get('evidence_claim_ids'))):
			self._add('claim.impact', field + '/impact', 'Impact needs severity, substantive basis and evidence_claim_ids (empty if unknown)', claim)
		elif impact['severity'] in {'high', 'critical'} and (not impact['evidence_claim_ids']):
			self._add('claim.impact_evidence', field + '/impact', 'High/critical impact needs versioned evidence claims, not only an adjective', claim)
		calculation = claim.get('calculation')
		if 'calculation' == claim.get('knowledge_type') or 'calculation' in (properties if isinstance(properties, list) else []):
			self.issues.extend(_calculation_structure(calculation, field + '/calculation', claim))
		comparison = claim.get('comparison')
		if None is not comparison or ('verified' == claim.get('verification_status') and {'modification', 'comparison'}.intersection(properties if isinstance(properties, list) else [])):
			self.issues.extend(_comparison_structure(comparison, field + '/comparison', claim, evidence))
		self._check_claim_arguments(field, claim, evidence)
	def _check_counterevidence_cap(self, field, section, claim):
		against = claim.get('against')
		prob = claim.get('probability_percent')
		if 'hypothesis' == claim.get('knowledge_type') and 'verified' != claim.get('verification_status') and isinstance(against, list) and isinstance(prob, int) and (75 < prob):
			is_causal = section in ('causes', 'misconceptions') or 'causal' == claim.get('category')
			if not against and (is_causal or bool(claim.get('alternative_explanations'))):
				self._add('claim.counterevidence', field + '/probability_percent', 'An unverified or limited hypothesis with competing alternatives and no against arguments cannot exceed 75% probability; include counter-arguments from plausible alternatives or lower the probability', claim)
			elif against and is_causal and (self.seen.get(claim.get('id')) == (field, section, claim)):
				own_ev_kind = {ref.get('id'): ref.get('kind') for ref in (claim.get('evidence') if isinstance(claim.get('evidence'), list) else []) if isinstance(ref, dict) and _text(ref.get('id'))}
				for_ev_ids = {arg.get('evidence_id') for arg in (claim.get('for') if isinstance(claim.get('for'), list) else []) if isinstance(arg, dict) and _text(arg.get('evidence_id'))}
				for_claim_ids = {arg.get('claim_id') for arg in (claim.get('for') if isinstance(claim.get('for'), list) else []) if isinstance(arg, dict) and _text(arg.get('claim_id'))}
				has_counter_obs = False
				for arg in against:
					if not isinstance(arg, dict):
						continue
					ev_id, c_id = (arg.get('evidence_id'), arg.get('claim_id'))
					if _text(ev_id) and ev_id not in for_ev_ids and (own_ev_kind.get(ev_id) in {'observation', 'experiment'}):
						has_counter_obs = True
						break
					if _text(c_id) and c_id not in for_claim_ids and (c_id in self.seen) and (self.seen[c_id][2].get('knowledge_type') in {'observation', 'calculation'}):
						has_counter_obs = True
						break
				if not has_counter_obs:
					self._add('claim.counterevidence', field + '/probability_percent', 'An unverified causal or misconception hypothesis above 75% requires genuine observation/experiment counter-evidence in against (citing only client intake or reusing for-premises does not lift the 75% cap)', claim)
	def _check_cycles(self):
		visited, active = (set(), set())
		def visit(ident):
			if ident in active:
				self._add('claim.cycle', self.seen[ident][0] + '/derived_from', 'Claim dependencies contain a cycle', self.seen[ident][2])
			elif ident not in visited and ident in self.seen:
				active.add(ident)
				for dep in _dependencies(self.seen[ident][2]):
					if isinstance(dep, dict) and _text(dep.get('claim_id')):
						visit(dep['claim_id'])
				active.remove(ident)
				visited.add(ident)
		for ident in self.seen:
			visit(ident)
	def _check_primary_evidence_list(self, field, claim, evidence):
		for number, ref in enumerate(evidence):
			ef = field + f'/evidence/{number}'
			if not isinstance(ref, dict):
				self._add('primary.reference', ef, 'A primary reference must be an object', claim)
				continue
			if not _text(ref.get('id')) or ref['id'] in self.evidence_ids:
				self._add('primary.id', ef + '/id', 'Evidence IDs must be nonempty and unique in this analysis', claim)
			else:
				self.evidence_ids.add(ref['id'])
			if not _enum(ref.get('kind'), {'observation', 'intake', 'attachment', 'experiment'}):
				self._add('primary.kind', ef + '/kind', 'Primary evidence needs observation, intake, attachment or experiment provenance', claim)
			if not _text(ref.get('source')) or not _text(ref.get('quote')) or (not _hash(ref.get('source_sha256'))):
				self._add('primary.source', ef, 'Supply exact source, quote and source_sha256', claim)
			locator = ref.get('locator')
			if not isinstance(locator, dict) or not _enum(locator.get('type'), {'text', 'json_pointer', 'anchor', 'lines'}) or (not _text(locator.get('value'))):
				self._add('primary.locator', ef + '/locator', 'Use an exact text, JSON pointer, anchor or line-range locator', claim)
			if 'documentation' in ref and bool is not type(ref['documentation']):
				self._add('documentation.type', ef + '/documentation', 'documentation must be an explicit boolean', claim)
			if ref.get('documentation') and _text(ref.get('source')) and (not urldefrag(ref['source'])[1]):
				exception = ref.get('anchor_exception')
				if isinstance(locator, dict) and 'anchor' == locator.get('type'):
					self._add('documentation.locator', ef + '/source', 'Put the available documentation section anchor in the source URL itself', claim)
				elif not isinstance(exception, dict) or not all((_text(exception.get(k)) for k in ('section', 'observation'))):
					self._add('documentation.locator', ef + '/anchor_exception', 'Documentation needs its section anchor URL or a named section and saved no-anchor observation', claim)
			if 'observation' == ref.get('kind') and (not _text(ref.get('observation'))):
				self._add('primary.observation', ef, 'Observation metadata reference is required', claim)
			if 'experiment' == ref.get('kind') and (not _text(ref.get('experiment')) or not _text(ref.get('artifact_id'))):
				self._add('primary.experiment', ef, 'Experiment and exact artifact_id are required', claim)
			if _enum(ref.get('kind'), {'intake', 'attachment'}) and (not _text(ref.get('manifest'))):
				self._add('primary.manifest', ef, 'Bind intake/attachment bytes to the saved project snapshot or intake manifest', claim)
	def _has_http_dns_error(self):
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
	def _inherited(self, ident, active=None):
		active = set() if None is active else active
		if ident in self.inherited_memo:
			r = self.inherited_memo[ident]
		elif ident in active or ident not in self.index:
			r = (set(), set(), [])
		else:
			next_active = active | {ident}
			caps = set(self.capabilities.get(ident, set()))
			urls = set(self.direct_obs_urls.get(ident, set()))
			metas = list(self.direct_obs_metas.get(ident, []))
			for dep in _dependencies(self.index[ident]):
				if isinstance(dep, dict) and dep.get('claim_id') in self.index:
					dep_caps, dep_urls, dep_metas = self._inherited(dep['claim_id'], next_active)
					caps.update(dep_caps)
					urls.update(dep_urls)
					metas.extend(dep_metas)
			r = (caps, urls, metas)
			if not active:
				self.inherited_memo[ident] = r
		return r
	def _load_direct_evidence(self):
		for field, _, claim in self.locations:
			ident = claim.get('id')
			if not _text(ident):
				self._add('primary.claim_id', field + '/id', 'Primary evidence needs a valid claim ID', claim)
				continue
			self.capabilities[ident] = set()
			self.direct_obs_urls[ident] = set()
			self.direct_obs_metas[ident] = []
			for number, ref in enumerate(claim.get('evidence', []) if isinstance(claim.get('evidence'), list) else []):
				if not isinstance(ref, dict):
					continue
				try:
					caps, saved = _primary_capabilities(self.root, ref)
					self.capabilities[ident].update(caps)
					self.refs[ref.get('id')] = (claim, ref, saved)
					if 'observation' == ref.get('kind'):
						self.direct_obs_urls[ident].add(ref.get('source', ''))
						if isinstance(saved, dict) and isinstance(saved.get('meta'), dict):
							self.direct_obs_metas[ident].append(saved['meta'])
				except (OSError, ValueError, KeyError, IndexError, TypeError, UnicodeError, ImportError) as exc:
					self._add('primary.unconfirmed', field + f'/evidence/{number}', str(exc), claim)
	def _verify_claim_evidence(self, field, claim):
		ident = claim['id']
		caps, obs_urls, obs_metas = self._inherited(ident)
		status = claim.get('verification_status')
		text_blob = str(claim.get('essence', '')) + ' ' + str(claim.get('assessment_basis', ''))
		if re.search('(?i)\\bgetaddrinfo\\b|\\bnxdomain\\b|\\u043d\\u0435\\s+\\u0440\\u0435\\u0437\\u043e\\u043b\\u0432\\u0438\\u0442\\u0441\\u044f(?:\\s+\\u043d\\u0430\\s+\\u0443\\u0440\\u043e\\u0432\\u043d\\u0435\\s+dns)?|dns\\s+(?:resolution\\s+failed|\\u043d\\u0435\\s+\\u0440\\u0435\\u0437\\u043e\\u043b\\u0432)', text_blob):
			has_dns_err = any(('dns_error' == m.get('error_kind') or False is m.get('dns_resolved') for m in obs_metas)) or self._has_http_dns_error()
			if not has_dns_err:
				self._add('claim.unverified_dns', field + '/essence', 'Claim asserts DNS non-resolution (getaddrinfo/NXDOMAIN) without a saved observation showing error_kind == dns_error; distinguish TCP timeout from DNS failure', claim)
		if 'verified' == status:
			for prop in claim.get('properties', []) if isinstance(claim.get('properties'), list) else []:
				if prop not in {'calculation', 'comparison', 'modification'} and (not _text(prop) or prop not in caps):
					self._add('claim.method_insufficient', field + '/properties', 'Saved methods cannot verify property ' + prop + '; keep a limited hypothesis and list the missing check', claim)
			for dep in _dependencies(claim):
				target = self.index.get(dep.get('claim_id')) if isinstance(dep, dict) and _text(dep.get('claim_id')) else None
				if target and 'verified' != target.get('verification_status'):
					self._add('claim.unverified_premise', field + '/derived_from', 'A verified conclusion cannot rely on an incomplete or hypothetical premise', claim)
			if set(claim.get('properties', [])) & {'content', 'markup', 'dom'} and obs_urls:
				self._verify_scope_coverage(field, claim, obs_urls)
		if 'calculation' == claim.get('knowledge_type') or 'calculation' in (claim.get('properties') or []):
			try:
				_check_calculation(claim, self.index, self.refs)
			except (ValueError, KeyError, TypeError, InvalidOperation, ZeroDivisionError) as exc:
				self._add('calculation.unconfirmed', field + '/calculation', str(exc), claim)
		if None is not claim.get('comparison') or ('verified' == status and {'modification', 'comparison'}.intersection(claim.get('properties') or [])):
			try:
				_check_comparison(claim, self.index, self.refs)
			except (ValueError, KeyError, TypeError) as exc:
				self._add('comparison.unconfirmed', field + '/comparison', str(exc), claim)
	def _verify_scope_coverage(self, field, claim, obs_urls):
		observed_paths = {urlsplit(urldefrag(u)[0]).path.rstrip('/') or '/' for u in obs_urls if u}
		sample_items = (claim.get('scope') or {}).get('sample') or []
		sample_urls = [s.strip() for s in sample_items if isinstance(s, str) and (s.strip().startswith(('http://', 'https://')) or s.strip().startswith('/')) and ('example.invalid' not in s)]
		sample_paths = {urlsplit(urldefrag(s)[0]).path.rstrip('/') or '/' for s in sample_urls}
		if observed_paths and all((p.lower().endswith(('sitemap.xml', 'robots.txt')) for p in observed_paths)):
			non_sitemap_samples = {p for p in sample_paths if not p.lower().endswith(('sitemap.xml', 'robots.txt'))}
			if non_sitemap_samples or re.search('(?i)(?:\\u0434\\u0435\\u043c\\u043e-\\u0437\\u0430\\u043f\\u0438\\u0441|\\u0434\\u0435\\u043c\\u043e-\\u0441\\u0442\\u0440\\u0430\\u043d\\u0438\\u0446|\\u0448\\u0430\\u0431\\u043b\\u043e\\u043d\\w+\\s+\\u0437\\u0430\\u0433\\u043b\\u0443\\u0448\\u043a|\\u043f\\u0443\\u0441\\u0442\\w+\\s+\\u0441\\u0442\\u0440\\u0430\\u043d\\u0438\\u0446|demo\\s+post|placeholder\\s+page|thin\\s+content)', str(claim.get('essence', ''))):
				self._add('claim.sitemap_insufficient', field + '/evidence', 'A sitemap.xml/robots.txt observation only proves URL listing in XML, not the HTTP status, content or markup of target pages; collect the target page URLs or CMS JSON first', claim)
		if sample_paths and (len(observed_paths) < len(sample_paths) or (any((p not in ('/', '/sitemap.xml', '/robots.txt') for p in sample_paths)) and observed_paths.issubset({'/', '/sitemap.xml', '/robots.txt'}))):
			self._add('claim.unobserved_sample', field + '/scope/sample', 'Verified claim scope.sample lists page URLs that were not observed in primary evidence; collect every sampled URL or narrow scope.sample', claim)
		non_sitemap_observed = {p for p in observed_paths if not p.lower().endswith(('sitemap.xml', 'robots.txt'))}
		if 1 >= len(non_sitemap_observed) and re.search('(?i)(?:\\u043d\\u0430\\s+(?:\\u0432\\u0441\\u0451\\u043c\\s+)?\\u0441\\u0430\\u0439\\u0442\\u0435|\\u043f\\u043e\\u043b\\u043d\\u043e\\u0441\\u0442\\u044c\\u044e\\s+\\u043e\\u0442\\u0441\\u0443\\u0442\\u0441\\u0442\\u0432\\u0443|\\u043e\\u0442\\u0441\\u0443\\u0442\\u0441\\u0442\\u0432\\u0443\\u044e\\u0442\\s+\\u0441\\u0445\\u0435\\u043c\\u044b\\s+`?(?:Product|Offer|Article)|absent\\s+across\\s+the\\s+entire\\s+site|no\\s+(?:Product|Offer|Article)\\s+schema\\s+on\\s+the\\s+site)', str(claim.get('essence', ''))):
			self._add('claim.scope_extrapolation', field + '/scope', 'Homepage/single-page/sitemap observations alone cannot verify site-wide absence of Product/Offer/Article structured data; observe representative product/article pages or keep status limited', claim)
	def evidence_issues(self, *, skip_structural=False):
		structural = [] if skip_structural or not self.is_v3 else self.structural_issues()
		if not self.is_v3 or structural:
			r = structural
		else:
			self.issues = []
			self.capabilities = {}
			self.refs = {}
			self.direct_obs_urls = {}
			self.direct_obs_metas = {}
			self.inherited_memo = {}
			self._load_direct_evidence()
			for field, _, claim in self.locations:
				if _text(claim.get('id')):
					self._verify_claim_evidence(field, claim)
			r = list(self.issues)
		return r
	def structural_issues(self):
		self.issues, self.seen, self.evidence_ids = ([], {}, set())
		if self.is_v3:
			if not isinstance(self.value.get('facts'), list):
				self._add('facts.list', '/facts', 'Version 3 requires first-class facts, including an explicit empty list')
			else:
				for number, item in enumerate(self.value['facts']):
					if not isinstance(item, dict):
						self._add('claim.object', f'/facts/{number}', 'Each fact must be an object')
			for field, section, claim in self.locations:
				self._check_claim_structure(field, section, claim)
			self._check_claim_dependencies_and_caps()
			self._check_cycles()
		return list(self.issues)
def evaluate_safe_arithmetic(expr: str, env: dict[str, Decimal] | None = None) -> tuple[Decimal | None, set[str]]:
	if not isinstance(expr, str) or not expr.strip() or len(expr) > 400:
		return (None, set())
	normalized = re.sub('(?<=\\d)[ \\u00a0\\u202f](?=\\d{3}(?!\\d))', '', expr.strip())
	normalized = re.sub('(?<=\\d),(?=\\d{3}(?!\\d))', '', normalized)
	normalized = normalized.replace('\u2212', '-').replace('\u00d7', '*').replace('\u00f7', '/')
	tree = None
	try:
		cand_tree = ast.parse(normalized, mode='eval')
		if not any((isinstance(n, ast.Tuple) for n in ast.walk(cand_tree))):
			tree = cand_tree
	except SyntaxError:
		tree = None
	if None is tree:
		dec_comma_norm = re.sub('(?<=\\d),(?=\\d)', '.', normalized)
		try:
			cand_tree = ast.parse(dec_comma_norm, mode='eval')
			if not any((isinstance(n, ast.Tuple) for n in ast.walk(cand_tree))):
				tree = cand_tree
		except SyntaxError:
			return (None, set())
	if None is tree:
		return (None, set())
	literal_tokens: set[str] = set()
	env_map = env or {}
	def _eval(node) -> Decimal:
		if isinstance(node, ast.Expression):
			return _eval(node.body)
		if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and (not isinstance(node.value, bool)):
			val_str = str(node.value)
			literal_tokens.add(val_str)
			return Decimal(val_str)
		if isinstance(node, ast.Name) and node.id in env_map:
			return Decimal(env_map[node.id])
		if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
			operand = _eval(node.operand)
			return operand if isinstance(node.op, ast.UAdd) else -operand
		if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)):
			left = _eval(node.left)
			right = _eval(node.right)
			if isinstance(node.op, ast.Add):
				return left + right
			if isinstance(node.op, ast.Sub):
				return left - right
			if isinstance(node.op, ast.Mult):
				return left * right
			if isinstance(node.op, ast.Div):
				if 0 == right:
					raise ZeroDivisionError('division by zero')
				return left / right
			if isinstance(node.op, ast.FloorDiv):
				if 0 == right:
					raise ZeroDivisionError('division by zero')
				return left // right
			if isinstance(node.op, ast.Mod):
				if 0 == right:
					raise ZeroDivisionError('modulo by zero')
				return left % right
			if isinstance(node.op, ast.Pow):
				if abs(right) > Decimal(10) or right != right.to_integral_value():
					raise ValueError('unsupported exponent')
				return left ** int(right)
		if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and (node.func.id in {'round', 'abs', 'min', 'max'}) and (not node.keywords):
			eval_args = [_eval(a) for a in node.args]
			if 'abs' == node.func.id and 1 == len(eval_args):
				return abs(eval_args[0])
			if 'min' == node.func.id and eval_args:
				return min(eval_args)
			if 'max' == node.func.id and eval_args:
				return max(eval_args)
			if 'round' == node.func.id and 1 <= len(eval_args) <= 2:
				places = int(eval_args[1]) if 2 == len(eval_args) else 0
				if not 0 <= places <= 12:
					raise ValueError('invalid rounding places')
				return eval_args[0].quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
		raise ValueError('unsupported AST node')
	try:
		with localcontext() as ctx:
			ctx.prec = 50
			res = _eval(tree)
		if not res.is_finite():
			return (None, set())
		return (res, literal_tokens)
	except (ValueError, ZeroDivisionError, InvalidOperation, ArithmeticError, TypeError):
		return (None, set())
_NUM_EXPR_TOK = '-?\\d+(?:[ \\u00a0\\u202f]\\d{3})*(?:[.,]\\d+)*'
_INLINE_EQ_RE = re.compile(
	'(?<![A-Za-z0-9_./])'
	f'((?:\\(\\s*)*{_NUM_EXPR_TOK}(?:\\s*\\))*'
	f'(?:\\s*[+\\-*/\\u2212\\u00d7\\u00f7]\\s*(?:\\(\\s*)*{_NUM_EXPR_TOK}(?:\\s*\\))*)+)'
	'\\s*(=|\\u2248|~=|\\u2245)\\s*'
	f'({_NUM_EXPR_TOK})(\\s*%)?'
)
def _claim_numeric_corpus(claim):
	texts = []
	for key in ('essence', 'assessment_basis', 'discriminating_check', 'validation', 'criterion'):
		if isinstance(claim.get(key), str):
			texts.append(claim[key])
	for key in ('probability_percent', 'score_percent'):
		if isinstance(claim.get(key), int):
			texts.append(str(claim[key]))
	if isinstance(claim.get('scope'), dict):
		texts.append(str(claim['scope'].get('description', '')))
		texts.extend((str(x) for x in claim['scope'].get('sample') or []))
		texts.extend((str(x) for x in claim['scope'].get('limitations') or []))
	if isinstance(claim.get('calculation'), dict):
		texts.append(json.dumps(claim['calculation'], ensure_ascii=False))
	for ref in claim.get('evidence', []) if isinstance(claim.get('evidence'), list) else []:
		if isinstance(ref, dict):
			texts.append(str(ref.get('quote', '')))
			if isinstance(ref.get('locator'), dict):
				texts.append(str(ref['locator'].get('value', '')))
	for side in ('for', 'against'):
		for arg in claim.get(side, []) if isinstance(claim.get(side), list) else []:
			if isinstance(arg, dict):
				texts.append(str(arg.get('argument', '')))
				texts.append(str(arg.get('quote', '')))
	return '\n'.join(texts)
def _decimal_matches_stated(computed: Decimal, stated_raw: str, is_approx: bool = False, is_percent_suffix: bool = False) -> bool:
	clean_stated = re.sub('(?<=\\d)[ \\u00a0\\u202f](?=\\d{3}(?!\\d))', '', stated_raw.strip())
	clean_stated = re.sub('(?<=\\d),(?=\\d{3}(?!\\d))', '', clean_stated).replace(',', '.')
	try:
		stated_dec = Decimal(clean_stated)
	except InvalidOperation:
		return False
	places = len(clean_stated.split('.')[1]) if '.' in clean_stated else 0
	q = Decimal(1).scaleb(-places)
	candidates = [computed]
	if is_percent_suffix:
		candidates.append(computed * Decimal(100))
	for cand in candidates:
		with localcontext() as ctx:
			ctx.prec = 50
			rounded = cand.quantize(q, rounding=ROUND_HALF_UP)
		if rounded == stated_dec or cand == stated_dec:
			return True
		if is_approx and abs(cand - stated_dec) <= q:
			return True
	return False
def extract_verified_inline_calc_numbers(text: str, grounded_nums: set[str]) -> tuple[set[str], list[str]]:
	if not isinstance(text, str) or not text:
		return (set(), [])
	verified: set[str] = set()
	errors: list[str] = []
	allowed_constants = {'100', '1000', '1024', '60', '24', '3600'}
	expanded_grounded = set(grounded_nums)
	for g in list(grounded_nums):
		expanded_grounded.add(g.replace(',', ''))
		expanded_grounded.add(g.replace(',', '.'))
	for m in _INLINE_EQ_RE.finditer(text):
		lhs, op_sym, rhs_raw, pct_suf = (m.group(1), m.group(2), m.group(3), bool(m.group(4)))
		for sp_m in re.finditer('\\b(\\d{1,3}(?:[ \\u00a0\\u202f]\\d{3})+(?:[.,]\\d+)?)\\b', lhs):
			sp_parts = re.findall('\\d+(?:[.,]\\d+)?', sp_m.group(1))
			if sp_parts and all((p.replace(',', '.') in expanded_grounded or p.replace(',', '') in expanded_grounded for p in sp_parts)):
				joined = re.sub('[ \\u00a0\\u202f]', '', sp_m.group(1)).replace(',', '.')
				expanded_grounded.add(joined)
		val, lit_tokens = evaluate_safe_arithmetic(lhs)
		if None is val or len(lit_tokens) < 2:
			continue
		if not all((tok in expanded_grounded or tok.replace(',', '') in expanded_grounded or tok in allowed_constants for tok in lit_tokens)):
			continue
		is_approx = op_sym != '='
		if _decimal_matches_stated(val, rhs_raw, is_approx=is_approx, is_percent_suffix=pct_suf):
			clean_rhs = re.sub('(?<=\\d)[ \\u00a0\\u202f](?=\\d{3}(?!\\d))', '', rhs_raw.strip())
			norm_dot = clean_rhs.replace(',', '.')
			no_comma = re.sub('(?<=\\d),(?=\\d{3}(?!\\d))', '', clean_rhs).replace(',', '.')
			verified.add(norm_dot)
			verified.add(no_comma)
			verified.update(norm_dot.split('.'))
			verified.update(no_comma.split('.'))
			for sub_tok in re.findall('\\d+(?:[.,]\\d+)*', rhs_raw):
				verified.add(sub_tok.replace(',', '.'))
				verified.add(sub_tok.replace(',', ''))
		elif '=' == op_sym:
			with localcontext() as ctx:
				ctx.prec = 28
				expected_str = str(val.normalize())
			errors.append(f'derived_calc mismatch: "{lhs.strip()} = {rhs_raw}" evaluates to {expected_str}, not {rhs_raw}')
	return (verified, errors)
def claim_locations(value):
	if not isinstance(value, dict):
		return
	for section in ('facts', 'claims', *SECTIONS):
		for number, claim in enumerate(value.get(section, []) if isinstance(value.get(section), list) else []):
			if isinstance(claim, dict):
				yield (f'/{section}/{number}', section, claim)
def all_claims(value):
	return [claim for _, _, claim in claim_locations(value)]
def claim_index(value):
	return {claim['id']: claim for claim in all_claims(value) if _text(claim.get('id'))}
# 2026-10-22 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Ban conditional conjunctions in limited claim qualifications and isolate closed admin access from proven public storefront facts":
# https://github.com/dmitry-ai/harness/issues/15
def claim_digest(claim):
	return hashlib.sha256(json.dumps(claim, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
def collect_claim_closure(seed_ids, index, *, include_addresses=False, unknown_prefix=None):
	r, seen = ([], set())
	def visit(ident):
		if None is not unknown_prefix and ident not in index:
			raise ValueError(unknown_prefix + str(ident))
		if _text(ident) and ident not in seen and ident in index:
			seen.add(ident)
			r.append(ident)
			item = index[ident]
			for dep in _dependencies(item):
				if isinstance(dep, dict):
					dep_id = dep.get('claim_id')
					if None is not unknown_prefix or _text(dep_id):
						visit(dep_id)
			if include_addresses:
				for addr_id in item.get('addresses', []) if isinstance(item.get('addresses'), list) else []:
					if None is not unknown_prefix or _text(addr_id):
						visit(addr_id)
	for seed in seed_ids:
		if None is not unknown_prefix or _text(seed):
			visit(seed)
	return r
def _text(value):
	return isinstance(value, str) and bool(value.strip())
def _strings(value, *, nonempty=False):
	return isinstance(value, list) and (bool(value) or not nonempty) and all((_text(x) for x in value))
def _hash(value):
	return isinstance(value, str) and None is not HASH.fullmatch(value)
def _enum(value, allowed):
	return isinstance(value, str) and value in allowed
def _dependencies(claim):
	return claim.get('derived_from', []) if isinstance(claim.get('derived_from'), list) else []
def source_numeric_tokens(raw_text: str) -> set[str]:
	r: set[str] = set()
	for sp_tok in re.findall('\\d{1,3}(?:[ \\u00a0\\u202f]\\d{3})+(?:[.,]\\d+)?', raw_text or ''):
		compact = re.sub('[ \\u00a0\\u202f]', '', sp_tok)
		r.add(compact.replace(',', '.'))
		r.add(compact.replace(',', ''))
	for tok in re.findall('\\d+(?:[.,]\\d+)*', raw_text or ''):
		norm_dot = tok.replace(',', '.')
		no_comma = tok.replace(',', '')
		r.add(norm_dot)
		r.add(no_comma)
		r.update(norm_dot.split('.'))
		r.update(no_comma.split('.'))
		if '.' in no_comma:
			r.add(no_comma.rstrip('0').rstrip('.') or '0')
	return r
def standalone_numbers(text):
	if not isinstance(text, str) or not text:
		r = set()
	else:
		from .markdown_links import numeric_text
		cleaned = numeric_text(text)
		cleaned = re.sub('https?://\\S+', ' ', cleaned)
		cleaned = re.sub('\\b[a-f0-9]{8,64}\\b', ' ', cleaned, flags=re.I)
		cleaned = re.sub('\\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\\b', ' ', cleaned)
		cleaned = re.sub('(?m)^\\s*#{1,6}\\s+\\d+(?:\\.\\d+)*\\.?\\b', ' ', cleaned)
		cleaned = re.sub('(?m)^\\s*\\d+(?:\\.\\d+)*[.)]\\s+', ' ', cleaned)
		cleaned = re.sub('§+\\s*\\d+(?:\\.\\d+)*', ' ', cleaned)
		tokens = re.findall('(?<![A-Za-z0-9_./~+-])\\d+(?:[.,]\\d+)*(?![A-Za-z0-9_./~+-])', cleaned)
		r = {t.replace(',', '.') for t in tokens}
	return r
def grounded_numbers_for_claim(claim, index=None, visited=None, _memo=None):
	visited = set() if None is visited else visited
	memo = {} if None is _memo else _memo
	ident = claim.get('id') if isinstance(claim, dict) else None
	if not isinstance(claim, dict) or ident in visited:
		r = set()
	elif _text(ident) and ident in memo:
		r = set(memo[ident])
	else:
		next_visited = visited | ({ident} if isinstance(ident, str) else set())
		corpus = _claim_numeric_corpus(claim)
		numbers = source_numeric_tokens(corpus)
		if isinstance(index, dict):
			for dep in _dependencies(claim):
				dep_id = dep.get('claim_id') if isinstance(dep, dict) else None
				if dep_id and dep_id in index:
					numbers.update(grounded_numbers_for_claim(index[dep_id], index, next_visited, memo))
			for addr_id in claim.get('addresses', []) if isinstance(claim.get('addresses'), list) else []:
				if isinstance(addr_id, str) and addr_id in index:
					numbers.update(grounded_numbers_for_claim(index[addr_id], index, next_visited, memo))
		derived_nums, _ = extract_verified_inline_calc_numbers(corpus, numbers)
		numbers.update(derived_nums)
		if _text(ident) and not visited:
			memo[ident] = set(numbers)
		r = numbers
	return r
def contract_issues(value):
	return ClaimGraphValidator(value).structural_issues()
def _calculation_structure(value, field, claim):
	message = None
	op = value.get('operation') if isinstance(value, dict) else None
	if not isinstance(value, dict) or op not in {'percent_change', 'formula', 'derived_calc'}:
		message = 'Supported calculation operations are percent_change, formula, or derived_calc'
	elif 'percent_change' == op and '(new - old) / old * 100' != value.get('formula'):
		message = 'Supported calculation is percent_change with formula (new - old) / old * 100'
	elif op in {'formula', 'derived_calc'} and (not _text(value.get('formula'))):
		message = 'Formula calculation requires a nonempty arithmetic formula'
	elif type(value.get('rounding_places')) is not int or not 0 <= value['rounding_places'] <= 12 or 'ROUND_HALF_UP' != value.get('rounding'):
		message = 'Choose explicit ROUND_HALF_UP and 0..12 decimal places'
	elif not isinstance(value.get('operands'), dict) or not value['operands'] or ('percent_change' == op and set(value['operands']) != {'old', 'new'}):
		message = 'Supply old/new operands with exact decimal value, unit, claim_id and evidence_id'
	elif ('percent_change' == op and 'percent' != value.get('result_unit')) or (op in {'formula', 'derived_calc'} and not _text(value.get('result_unit'))):
		message = 'Percentage change requires explicit result_unit percent'
	else:
		for operand in value['operands'].values():
			if not isinstance(operand, dict) or not all((_text(operand.get(k)) for k in ('value', 'unit', 'claim_id', 'evidence_id'))):
				message = 'Each operand needs decimal string value, explicit unit, claim_id and evidence_id'
				break
			if operand['unit'] != operand['unit'].strip():
				message = 'Operand units must be canonical strings without surrounding whitespace'
				break
		if None is message and 'percent_change' == op and value['operands']['old']['unit'] != value['operands']['new']['unit']:
			message = 'Percent change requires matching operand units; perform and source any conversion as a separate claim first'
		if not _text(value.get('result')):
			message = 'Calculation result must be an explicit decimal string'
	r = [problem('calculation.contract', field, message, claim_id=claim.get('id'))] if message else []
	return r
def _comparison_structure(value, field, claim, evidence):
	message = None
	own_ev_ids = {ref.get('id') for ref in (evidence if isinstance(evidence, list) else []) if isinstance(ref, dict) and _text(ref.get('id'))}
	has_dep = bool(_dependencies(claim))
	if not isinstance(value, dict) or not _enum(value.get('relation'), {'equal', 'differs', 'modified_from', 'identical_to'}):
		message = 'A relational or modification claim requires comparison metadata with relation in {equal, differs, modified_from, identical_to}'
	elif not _text(value.get('operand_a_evidence_id')) or not _text(value.get('operand_b_evidence_id')):
		message = 'Relational comparison requires two primary evidence IDs: operand_a_evidence_id and operand_b_evidence_id'
	elif value['operand_a_evidence_id'] == value['operand_b_evidence_id']:
		message = 'Relational comparison requires two distinct primary evidence operands (operand_a_evidence_id != operand_b_evidence_id)'
	elif not has_dep and (value['operand_a_evidence_id'] not in own_ev_ids or value['operand_b_evidence_id'] not in own_ev_ids):
		message = 'Relational comparison operands must reference primary evidence IDs present on the claim or its derived_from dependencies'
	r = [problem('claim.relational_arity', field, message, claim_id=claim.get('id'))] if message else []
	return r
def _with_locator(source, locator):
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
def _verify_quote(root, ref, *, observation=None):
	from .evidence import verify_saved_quote
	locator = ref['locator']
	return verify_saved_quote(root, _with_locator(ref['source'], locator), ref['quote'], mode=ref.get('quote_match', 'exact'), expected_hash=ref['source_sha256'], require_hash=True, observation=observation, documentation=bool(ref.get('documentation')), exception=ref.get('anchor_exception', {}), locator=locator, require_bound_observation=True, hash_error='Primary source bytes changed from source_sha256', absent_error='Exact quote is absent from the located primary source')
def _manifest_primary(root, ref):
	from .evidence import local_file
	from .research import inside
	root = Path(root).resolve()
	source = local_file(root, ref['source'])
	manifest_file = local_file(root, ref['manifest'])
	manifest = json.loads(manifest_file.read_text(encoding='utf-8-sig'))
	if not isinstance(manifest, dict):
		raise ValueError('A primary manifest must be a saved JSON object')
	state_file = root / 'ꘖ/project.json'
	state = json.loads(state_file.read_text(encoding='utf-8-sig')) if state_file.exists() else {}
	if not isinstance(state, dict) or True is not state.get('initialized') or (not _text(state.get('job_id'))) or (not _text(state.get('snapshot'))):
		raise ValueError('Intake evidence needs a registered initialized project and its exact permanent snapshot')
	snapshot = inside(root, state['snapshot'])
	evidence = root / 'ꘖ/KB/Evidence'
	if not snapshot.is_relative_to(evidence):
		raise ValueError('Registered intake snapshot must belong to project Evidence')
	snapshot_raw = snapshot.read_bytes()
	snapshot_value = json.loads(snapshot_raw.decode('utf-8-sig'))
	if not HASH.fullmatch(snapshot.stem) or hashlib.sha256(snapshot_raw).hexdigest() != snapshot.stem or (not isinstance(snapshot_value, dict)) or (snapshot_value.get('job_id') != state['job_id']):
		raise ValueError('The registered snapshot must retain its content-addressed bytes and project job ID')
	if manifest_file == snapshot:
		raw = manifest_file.read_bytes()
		if not HASH.fullmatch(manifest_file.stem) or hashlib.sha256(raw).hexdigest() != manifest_file.stem:
			raise ValueError('The registered intake snapshot must retain its content-addressed bytes')
		if 'intake' == ref['kind'] and source == manifest_file:
			return {'client_report', 'content'}
		if 'attachment' == ref['kind']:
			for asset in manifest.get('asset_evidence', []):
				if isinstance(asset, dict) and local_file(root, asset.get('file', '')) == source and (asset.get('sha256') == ref['source_sha256']):
					return {'client_report', 'content'}
	intake = root / 'ꘖ/KB/Evidence/Intake'
	if manifest_file.parent != intake or 1 != manifest.get('version') or manifest.get('status') not in {'prepared', 'drained'} or (manifest.get('job_id') != state.get('job_id')):
		raise ValueError('Primary intake/attachment must belong to the registered snapshot or its intake manifest')
	from .intake import CAPTURE_NAME, _validate_receipt
	provenance = manifest.get('original_directory_provenance')
	if not _text(provenance):
		raise ValueError('Intake primary needs the full capture receipt bound to its registered snapshot')
	capture = Path(provenance)
	name = CAPTURE_NAME.fullmatch(capture.name)
	if not capture.is_absolute() or not name or '~' + name[1] != state['job_id'] or (manifest_file.name != capture.name + '.json') or (True is not manifest.get('original_paths_are_provenance_only')):
		raise ValueError('Intake capture identity must match its receipt filename and registered project')
	try:
		_validate_receipt(manifest, capture, root, state)
	except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, StopIteration) as exc:
		raise ValueError('Intake receipt is not bound to the permanent registered source snapshot: ' + str(exc)) from exc
	for entry in manifest.get('entries', []):
		if not isinstance(entry, dict) or not isinstance(entry.get('durable_file'), str):
			continue
		if inside(root, entry['durable_file']) == source and entry.get('sha256') == ref['source_sha256'] and ('identity' == entry.get('transform')):
			name = entry.get('original_relative_provenance', '')
			if 'attachment' == ref['kind'] and (not name.startswith('attachments/')):
				continue
			if 'intake' == ref['kind'] and name not in {'source.json', 'request.txt'}:
				raise ValueError('Intake primaries are the captured source.json or exact user request; site hypotheses and agent notes require their own primary origins')
			return {'client_report', 'content'}
	raise ValueError('Source bytes are absent from the declared intake/attachment manifest')
def _primary_capabilities(root, ref):
	if 'observation' == ref['kind']:
		from .research import load_observation
		meta = load_observation(root, ref['observation'])
		if not urlsplit(ref['source']).scheme.lower() in {'http', 'https'}:
			raise ValueError('An observation primary source must name its captured HTTP(S) URL')
		saved = _verify_quote(root, ref, observation=ref['observation'])
		from .research import observation_capabilities
		r = (set(observation_capabilities(meta)), saved)
	elif 'experiment' != ref['kind']:
		capabilities = _manifest_primary(root, ref)
		saved = _verify_quote(root, ref)
		r = (capabilities, saved)
	else:
		from .experiments import load_experiment
		from .evidence import local_file
		experiment = load_experiment(root, ref['experiment'])
		asset = next((a for a in experiment.get('artifacts', []) if a.get('id') == ref['artifact_id']), None)
		if not asset or local_file(root, asset['path']) != local_file(root, ref['source']) or asset.get('sha256') != ref['source_sha256']:
			raise ValueError('Experiment source must be the exact recorded artifact and hash')
		saved = _verify_quote(root, ref)
		r = (set(experiment.get('capabilities', [])), saved)
	return r
def evidence_contract_issues(root, value, *, skip_structural=False):
	return ClaimGraphValidator(value, root=root).evidence_issues(skip_structural=skip_structural)
def _check_comparison(claim, index, refs):
	comp = claim.get('comparison')
	if _comparison_structure(comp, '/', claim, claim.get('evidence')):
		raise ValueError('Relational comparison does not satisfy its two-operand arity contract')
	allowed_claims = {claim.get('id')} | {d.get('claim_id') for d in _dependencies(claim) if isinstance(d, dict) and _text(d.get('claim_id'))}
	entry_a = refs.get(comp['operand_a_evidence_id'])
	entry_b = refs.get(comp['operand_b_evidence_id'])
	if not entry_a or not entry_b:
		raise ValueError('Both operand_a_evidence_id and operand_b_evidence_id must resolve to verified primary evidence')
	if entry_a[0].get('id') not in allowed_claims or entry_b[0].get('id') not in allowed_claims:
		raise ValueError('Comparison operand evidence must belong to the claim or its versioned derived_from dependencies')
	ref_a, saved_a = (entry_a[1], entry_a[2])
	ref_b, saved_b = (entry_b[1], entry_b[2])
	loc_a = (ref_a.get('source'), (ref_a.get('locator') or {}).get('type'), (ref_a.get('locator') or {}).get('value'))
	loc_b = (ref_b.get('source'), (ref_b.get('locator') or {}).get('type'), (ref_b.get('locator') or {}).get('value'))
	if loc_a == loc_b:
		raise ValueError('Relational comparison requires two distinct source/locator operands, not the same source fragment twice')
	hash_equal = ref_a.get('source_sha256') == ref_b.get('source_sha256')
	quote_equal = ' '.join(str(ref_a.get('quote', '')).split()) == ' '.join(str(ref_b.get('quote', '')).split())
	if comp['relation'] in {'differs', 'modified_from'} and hash_equal and quote_equal:
		raise ValueError('Claimed modification/difference between operand_a and operand_b is refuted: primary source hashes and quotes are identical')
	if comp['relation'] in {'equal', 'identical_to'} and (not hash_equal) and (not quote_equal):
		raise ValueError('Claimed identity between operand_a and operand_b is refuted: primary source hashes and quotes differ')
def _check_calculation(claim, index, refs):
	value = claim['calculation']
	if _calculation_structure(value, '/', claim):
		raise ValueError('Calculation does not satisfy its explicit contract')
	dependencies = {d.get('claim_id') for d in _dependencies(claim) if isinstance(d, dict)}
	operands = {}
	for name, operand in value['operands'].items():
		if operand['claim_id'] not in dependencies or operand['claim_id'] not in index:
			raise ValueError('Calculation operands must name versioned source claims')
		entry = refs.get(operand['evidence_id'])
		if not entry or entry[0].get('id') != operand['claim_id']:
			raise ValueError('Operand evidence must belong to its declared source claim')
		if not re.fullmatch('-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?', operand['value']):
			raise ValueError('Use exact finite base-10 decimal strings for operands')
		number = Decimal(operand['value'])
		if not _quantity_matches(entry[1], operand['value'], operand['unit'], entry[2]['quantity_context']):
			raise ValueError('Operand value and unit must identify the same unambiguous primary quantity; use an adjacent value-unit quote or a JSON value/unit object')
		operands[name] = number
	op = value.get('operation')
	if 'percent_change' == op:
		if 0 == operands['old']:
			raise ValueError('Percentage change denominator old must be nonzero')
		with localcontext() as context:
			context.prec = 50
			expected = ((operands['new'] - operands['old']) / operands['old'] * Decimal(100)).quantize(Decimal(1).scaleb(-value['rounding_places']), rounding=ROUND_HALF_UP)
	else:
		raw_eval, _ = evaluate_safe_arithmetic(value.get('formula', ''), env=operands)
		if None is raw_eval:
			raise ValueError(f"Arithmetic formula {value.get('formula')!r} could not be evaluated safely over operands {sorted(operands)}")
		with localcontext() as context:
			context.prec = 50
			expected = raw_eval.quantize(Decimal(1).scaleb(-value['rounding_places']), rounding=ROUND_HALF_UP)
	actual = Decimal(value['result'])
	if not actual.is_finite() or actual != expected:
		label = 'Percentage change' if 'percent_change' == op else 'Calculation result'
		raise ValueError(f"{label} is {expected}, not {value['result']}; formula includes the declared denominator and rounding")
def _quantity_matches(reference, decimal_value, unit, source_context=None):
	if 'json_pointer' == reference.get('locator', {}).get('type'):
		try:
			selected = json.loads(source_context if None is not source_context else reference['quote'], parse_float=Decimal, parse_int=Decimal)
		except (TypeError, ValueError):
			selected = None
		if isinstance(selected, dict):
			pairs = [(selected[v], selected[u]) for v, u in (('amount', 'currency'), ('value', 'unit')) if v in selected and u in selected]
			if pairs:
				if 1 != len(pairs):
					return False
				amount, currency = pairs[0]
				if type(amount) not in (str, Decimal) or currency != unit:
					return False
				try:
					return Decimal(amount).is_finite() and Decimal(amount) == Decimal(decimal_value)
				except InvalidOperation:
					return False
	if re.search('<\\s*/?\\s*[A-Za-z][^>]*>', reference['quote']):
		raise ValueError('Raw markup excerpts are ambiguous numeric provenance; use a complete signed quantity in parsed source text or a structured JSON value/unit object')
	def normalized(text):
		return ' '.join(text.replace(',', '.').replace('−', '-').split())
	quote = normalized(reference['quote'])
	text = normalized(source_context if None is not source_context else reference['quote'])
	excerpts = list(re.finditer(re.escape(quote), text))
	if not excerpts:
		return False
	unit_tokens = {'EUR': ('EUR', '€'), 'GBP': ('GBP', '£'), 'USD': ('USD', 'US$'), 'CAD': ('CAD', 'CA$', 'C$'), 'AUD': ('AUD', 'AU$', 'A$'), 'JPY': ('JPY', 'JP¥'), 'CNY': ('CNY', 'CN¥', 'RMB'), 'percent': ('percent', '%')}.get(unit, (unit,))
	expected = Decimal(decimal_value)
	tokens = list(re.finditer('(?<![\\d.])[0-9]+(?:\\.[0-9]+)?(?![\\d.])', text))
	def sign_before(start):
		marks = re.search('([+-](?:\\s*[+-])*)\\s*$', text[:start])
		if marks:
			signs = ''.join(marks[1].split())
			r = (signs, marks.start()) if 1 == len(signs) else (None, start)
		else:
			previous = text[:start].rstrip()[-1:]
			if previous and (unicodedata.category(previous) in {'Pd', 'Cf'} or 'MINUS' in unicodedata.name(previous, '')):
				r = (None, start)
			else:
				r = ('', start)
		return r
	def quantity(number):
		candidates = []
		for token in unit_tokens:
			escaped = re.escape(token)
			boundary = '(?<!\\w)' if token[0].isalnum() else ''
			prefix = re.search(boundary + escaped + '\\s*([+-]?)\\s*$', text[:number.start()])
			if prefix:
				leading, start = sign_before(prefix.start())
				trailing = prefix[1]
				if None is not leading and (not (leading and trailing)):
					candidates.append((leading or trailing, start, number.end()))
			boundary = '(?!\\w)' if token[-1].isalnum() else ''
			suffix = re.match('\\s*' + escaped + boundary, text[number.end():])
			if suffix:
				sign, start = sign_before(number.start())
				preceding = text[:start]
				ambiguous = not sign and (preceding[-1:].isalnum() or bool(re.search('[0-9.]\\s+$', preceding)))
				if None is not sign and (not ambiguous):
					candidates.append((sign, start, number.end() + suffix.end()))
		valid = []
		for sign, start, end in candidates:
			if text[:start].rstrip().endswith('(') and text[end:].lstrip().startswith(')'):
				continue
			amount = Decimal(number[0]) * (-1 if '-' == sign else 1)
			valid.append((amount, start, end))
		r = valid
		return r
	for excerpt in excerpts:
		numbers = [n for n in tokens if excerpt.start() <= n.start() and n.end() <= excerpt.end() and (Decimal(n[0]) == abs(expected))]
		if 1 != len(numbers):
			return False
		matches = quantity(numbers[0])
		if not matches or any((amount != expected or start < excerpt.start() or end > excerpt.end() for amount, start, end in matches)):
			return False
	return True
