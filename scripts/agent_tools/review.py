# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Decompose review.py and text_review.py into ReviewReportValidator, ReviewClassifier, and ReviewQuorumEvaluator classes":
# https://github.com/dmitry-ai/harness/issues/73
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract ClaimGraphValidator class and unify derived_from DAG traversals, numeric grounding, and primary quote verification across claims.py, text_claims.py, review.py, and evidence.py":
# https://github.com/dmitry-ai/harness/issues/62
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify quote normalization, MarkdownIt link/quote traversal, locale checks, numeric corpus tokenization, and Evidence loading across response_grounding.py, completion.py, source_grounding.py, claims.py, and review.py":
# https://github.com/dmitry-ai/harness/issues/59
# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Fix Antigravity executor/generation model mismatch in native-review-proof, decouple post-finalize deliverable reviews from initial Analysis.json, cache source grounding, and preserve journal recording on gate failure":
# https://github.com/dmitry-ai/harness/issues/51
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-06 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement claim-level Merkle cache, blind entailment predicates, single adversarial falsifier, and full-read reviewer verification":
# https://github.com/dmitry-ai/harness/issues/47
import hashlib
import importlib
import json
import re
from pathlib import Path
from .research import inside, json_data
from .storage import read_addressed_json, replace_bytes, write_immutable_bytes
PACKAGE_HANDLERS = {}
REVIEW_SCHEMA = 2
SCOPES = ('identity', 'concerns', 'misconceptions', 'causes', 'methods', 'kb_consistency', 'response')
TASK_FLAGS = {'new_causal_analysis', 'architecture_change', 'pricing_change', 'admin_configuration', 'business_impact', 'material_analysis'}
REPORT_CONTRACT = {'schema_version': REVIEW_SCHEMA, 'result_options': ['approved', 'needs_changes'], 'required_scope': list(SCOPES), 'claim_review_fields': ['claim_id', 'observed', 'inferred', 'method', 'alternatives', 'limits', 'falsification', 'raw_vs_criteria', 'test_alignment', 'outcome'], 'test_alignment_fields': ['target_claim', 'tested_claim', 'relationship', 'rationale', 'counterexample'], 'relationship_options': ['direct', 'proxy', 'irrelevant'], 'outcome_options': ['supported', 'qualified', 'unsupported'], 'finding_fields': ['id', 'claim_ids', 'severity', 'description', 'status'], 'severity_options': ['minor', 'significant', 'critical'], 'claim_review_required': {'fields': ['claim_id', 'observed', 'inferred', 'method', 'alternatives', 'limits', 'falsification', 'raw_vs_criteria', 'test_alignment', 'outcome'], 'outcome_options': ['supported', 'qualified', 'unsupported'], 'test_alignment_required': {'fields': ['target_claim', 'tested_claim', 'relationship', 'rationale', 'counterexample'], 'relationship_options': ['direct', 'proxy', 'irrelevant']}}, 'finding_required': {'fields': ['id', 'claim_ids', 'severity', 'description', 'status'], 'severity_options': ['minor', 'significant', 'critical'], 'status_options': ['open', 'resolved', 'rejected']}, 'falsifier_fields': ['disproved_claims'], 'disproved_claim_fields': ['claim_id', 'excerpt_from_answer', 'contradicting_tier0_source', 'verbatim_quote_from_source', 'falsification_reason']}
class ReviewClassifier:
	def __init__(self, root, state, value, *, exclude_package=None):
		self.exclude_package = exclude_package
		self.is_finalized = 'complete' == state.get('stages', {}).get('finalize', {}).get('status')
		self.root = root
		self.state = state
		self.value = value
	def _check_omitted_stage_claims(self, seen, previously_approved, risk):
		from .claims import claim_digest
		if not self.is_finalized:
			unreviewed = [c['id'] for s in ('causes', 'misconceptions', 'methods') for c in self.value.get(s) or [] if isinstance(c, dict) and is_nonempty_text(c.get('id')) and ((c['id'], claim_digest(c)) not in previously_approved)]
			omitted = sorted(set(unreviewed) - seen)
			if omitted and 'routine' == risk:
				raise ValueError('Unjustified routine risk downgrade: unreviewed causes/misconceptions/methods claims in Analysis.json cannot be omitted from the review manifest (' + ', '.join(omitted) + ')')
	def _evaluate_claim_risk(self, ident, claim, claim_section, restatement, reasons, required_flags):
		material = 'significant' == claim.get('materiality') or claim.get('impact', {}).get('severity') in ('high', 'critical')
		causal_section = claim_section in ('causes', 'misconceptions')
		properties = set(claim.get('properties', []))
		significant_kind = causal_section or claim.get('category') in ('causal', 'architecture', 'pricing') or bool(properties & {'causality', 'business_impact', 'admin_configuration', 'architecture_change', 'pricing_change'})
		if not restatement and (material or significant_kind):
			reasons.append(f"{ident}: new {claim.get('category')} claim ({claim.get('materiality')})")
			if material:
				required_flags.add('material_analysis')
			if causal_section:
				required_flags.add('new_causal_analysis')
			for category, prop, flag in (('causal', 'causality', 'new_causal_analysis'), ('architecture', 'architecture_change', 'architecture_change'), ('pricing', 'pricing_change', 'pricing_change')):
				if claim.get('category') == category or prop in properties:
					required_flags.add(flag)
			required_flags.update(properties & {'admin_configuration', 'business_impact'})
	def _resolve_claim(self, item, risk, index, section_by_id):
		from .claims import claim_digest, grounded_numbers_for_claim, standalone_numbers
		ident = item['claim_id']
		if ident not in index:
			essence_val = str(item.get('essence') or item['response_excerpt']).strip()
			claim = {'id': ident, 'essence': essence_val, 'materiality': item.get('materiality') or ('significant' if 'significant' == risk else 'routine'), 'category': item.get('category') or 'descriptive', 'properties': list(item.get('properties') or []), 'knowledge_type': item.get('knowledge_type') or 'observation', 'verification_status': item.get('verification_status') or 'verified', 'novelty': item.get('novelty') or 'new'}
			r = (claim, None, item.get('claim_sha256') or digest(json_data({'id': ident, 'essence': essence_val, 'response_excerpt': item['response_excerpt']})))
		else:
			claim = index[ident]
			excerpt_nums = standalone_numbers(item['response_excerpt'])
			if excerpt_nums:
				ungrounded_nums = sorted(excerpt_nums - grounded_numbers_for_claim(claim, index))
				if ungrounded_nums:
					raise ValueError(f'Response excerpt for {ident} contains numeric figures not grounded in the claim or its primary evidence: ' + ', '.join(ungrounded_nums))
			r = (claim, section_by_id.get(ident), claim_digest(claim))
		return r
	def _validate_spec(self, spec):
		if not isinstance(spec, dict) or spec.get('risk') not in ('routine', 'significant'):
			raise ValueError('Explicit review spec risk routine/significant is required; no default risk')
		if not is_nonempty_text(spec.get('basis')) or (not is_nonempty_text(spec.get('request_scope'))):
			raise ValueError('Review classification needs a substantive basis and current request_scope')
		flags = spec.get('task_flags')
		if not isinstance(flags, list) or any((not is_nonempty_text(x) or x not in TASK_FLAGS for x in flags)) or len(set(flags)) != len(flags):
			raise ValueError('Explicit unique task_flags list required: ' + ', '.join(sorted(TASK_FLAGS)) + ' (or [])')
		if not isinstance(spec.get('claim_ids'), list) or not spec['claim_ids'] or (not isinstance(spec.get('claims'), list)) or (not spec['claims']):
			raise ValueError('Analytical review requires nonempty claim_ids and response claims manifest')
		claim_ids = spec['claim_ids']
		if any((not is_nonempty_text(x) for x in claim_ids)) or len(set(claim_ids)) != len(claim_ids):
			raise ValueError('Review claim_ids must be unique existing claim IDs')
		return (flags, claim_ids)
	def classify(self, spec, response):
		from .claims import claim_index, claim_locations
		flags, claim_ids = self._validate_spec(spec)
		index = claim_index(self.value)
		section_by_id = {claim['id']: section for _, section, claim in claim_locations(self.value) if isinstance(claim, dict) and is_nonempty_text(claim.get('id'))}
		previously_approved = _approved_digests(self.root, self.state, exclude_package=self.exclude_package)
		manifest, seen, reasons, required_flags = ([], set(), [], set())
		for item in spec['claims']:
			if not isinstance(item, dict) or not is_nonempty_text(item.get('claim_id')) or (item['claim_id'] not in index and (not self.is_finalized)):
				raise ValueError('Every response claim must identify a current Analysis claim')
			ident = item['claim_id']
			if ident in seen or not is_nonempty_text(item.get('response_excerpt')) or item['response_excerpt'] not in response:
				raise ValueError('Response manifest needs one exact nonempty response excerpt per claim')
			seen.add(ident)
			claim, claim_section, sha = self._resolve_claim(item, spec['risk'], index, section_by_id)
			novelty = item.get('novelty', claim.get('novelty'))
			if novelty not in ('new', 'restatement'):
				raise ValueError('Response claim novelty must be new or restatement')
			restatement = 'restatement' == novelty and (ident, sha) in previously_approved
			self._evaluate_claim_risk(ident, claim, claim_section, restatement, reasons, required_flags)
			manifest.append({'claim_id': ident, 'claim_sha256': sha, 'response_excerpt': item['response_excerpt'], 'novelty': novelty, 'previously_approved_restatement': restatement, 'materiality': claim.get('materiality'), 'category': claim.get('category'), 'properties': claim.get('properties'), 'knowledge_type': claim.get('knowledge_type'), 'verification_status': claim.get('verification_status'), 'essence': claim['essence']})
		if set(claim_ids) != seen:
			raise ValueError('Classification claim_ids must equal the response manifest claim IDs')
		self._check_omitted_stage_claims(seen, previously_approved, spec['risk'])
		minimum = 'significant' if reasons or flags else 'routine'
		if 'significant' == minimum and 'routine' == spec['risk']:
			raise ValueError('Unjustified routine risk downgrade: ' + '; '.join(reasons))
		if not required_flags.issubset(flags):
			raise ValueError('Task flags omit typed significant work: ' + ', '.join(sorted(required_flags - set(flags))))
		return {'risk': spec['risk'], 'minimum_risk': minimum, 'risk_basis': spec['basis'], 'risk_reasons': reasons, 'request_scope': spec['request_scope'], 'claims': manifest, 'task_flags': flags, 'minimum_task_flags': sorted(required_flags)}
	@staticmethod
	def has_significant_flags(claims, flags):
		return any(('significant' == c.get('materiality') for c in claims)) or bool(set(flags) & TASK_FLAGS)
class ReviewQuorumEvaluator:
	def __init__(self, root, state):
		self.root = Path(root).resolve()
		self.state = state
	def approval_current(self, approval, *, package_reader=None):
		r = False
		if isinstance(approval, dict):
			try:
				reader = read_package if None is package_reader else package_reader
				package = reader(self.root, approval['package'], state=self.state)
				if digest(inside(self.root, approval['package']).read_bytes()) == approval['package_sha256']:
					approved = {item['id']: item for item in self.state['reviews'] if REVIEW_SCHEMA == item.get('schema_version')}
					selected = [approved[ident] for ident in approval['review_ids']]
					latest = self.latest_for_subject(package)
					if not self.has_unhandled_verdicts(package, latest) and (not any(('approved' != item.get('result') or latest[item['reviewer_id']].get('id') != item['id'] or (not self.findings_closed(item)) or (not self.entry_proof_current(item)) for item in selected))):
						eligible = [item for item in selected if 'routine' == package['risk'] or item.get('independent')]
						r = self.quorum_satisfied(package, latest, eligible)
			except (ValueError, OSError, KeyError, TypeError):
				r = False
		return r
	def approved_claim_digests(self, *, exclude_package=None):
		from .claims import claim_index
		from .workflow import evidence_paths, hashes
		r = set()
		is_finalized = 'complete' == self.state.get('stages', {}).get('finalize', {}).get('status')
		cur_ev_hashes = hashes(self.root, evidence_paths(self.root))
		index = None
		if is_finalized:
			try:
				index = claim_index(_analysis(self.root))
			except (OSError, ValueError):
				index = {}
		groups = {}
		for entry in self.state['reviews']:
			if REVIEW_SCHEMA != entry.get('schema_version') or 'approved' != entry.get('result') or (not entry.get('independent')) or entry.get('package') == exclude_package or (not self.entry_proof_current(entry)) or (not self.findings_closed(entry)):
				continue
			pkg_rel = entry['package']
			if pkg_rel not in groups:
				groups[pkg_rel] = (json.loads(inside(self.root, pkg_rel).read_text(encoding='utf-8')), [])
			groups[pkg_rel][1].append(entry)
		for package, matching in groups.values():
			pkg_ev = package.get('evidence_inputs') or {}
			ev_exact = pkg_ev == cur_ev_hashes
			if not ev_exact and (not is_finalized):
				continue
			latest = self.latest_for_subject(package)
			if self.has_unhandled_verdicts(package, latest):
				continue
			eligible = [item for item in matching if latest.get(item['reviewer_id'], {}).get('id') == item['id']]
			if not self.quorum_satisfied(package, latest, eligible):
				continue
			if ev_exact:
				r.update(((c['claim_id'], c['claim_sha256']) for c in package['claims']))
			else:
				for c in package['claims']:
					cid = c['claim_id']
					c_pairs = _claim_evidence_pairs(cid, index or {}, pkg_ev)
					if all((cur_ev_hashes.get(s) == sha for s, sha in c_pairs if sha)):
						r.add((cid, c['claim_sha256']))
		return r
	def entry_proof_current(self, entry):
		from .workflow import receipt_current
		return receipt_current(self.root, {'inputs': entry.get('proof', {})})
	def findings_closed(self, entry):
		data = json.loads(inside(self.root, entry['report']).read_text(encoding='utf-8'))
		statuses = {f['id']: f.get('status') for f in data['findings']}
		r = True
		for item in entry.get('dispositions', []):
			if not self.entry_proof_current({'proof': item['proof']}):
				r = False
				break
			saved = json.loads(inside(self.root, item['file']).read_text(encoding='utf-8'))
			statuses[saved['finding_id']] = saved['status']
		return r and all((status in ('resolved', 'rejected') for status in statuses.values()))
	def has_unhandled_verdicts(self, package, latest=None):
		active = self.latest_for_subject(package) if None is latest else latest
		ordered = {entry.get('id'): idx for idx, entry in enumerate(self.state['reviews'])}
		approved = [entry for entry in active.values() if 'approved' == entry.get('result') and entry.get('independent') and self.findings_closed(entry) and self.entry_proof_current(entry)]
		r = False
		for entry in active.values():
			if not ('approved' == entry.get('result') and self.findings_closed(entry)) and (not any((ordered[followup['id']] > ordered[entry['id']] and entry['id'] in followup.get('addresses_reviews', []) for followup in approved))):
				r = True
				break
		return r
	def latest_for_subject(self, package):
		r = {}
		for entry in self.state['reviews']:
			if REVIEW_SCHEMA == entry.get('schema_version') and entry.get('subject_sha256') == package['subject_sha256']:
				r[entry['reviewer_id']] = entry
		return r
	def quorum_satisfied(self, package, latest, eligible, *, allow_falsifier_or_cached=True) -> bool:
		required = 1
		if 'significant' == package['risk']:
			required = 2
			if allow_falsifier_or_cached:
				has_escalation = self.significant_findings(package['subject_sha256']) or any(('approved' != item.get('result') for item in latest.values()))
				merkle_delta = package.get('merkle_delta') or {}
				all_merkle_cached = bool(merkle_delta.get('cached_claim_ids')) and (not bool(merkle_delta.get('unverified_claim_ids')))
				if not has_escalation and ('falsifier' == package.get('review_mode') or any(('falsifier' == item.get('review_mode') for item in eligible)) or all_merkle_cached):
					required = 1
		return len({item['reviewer_id'] for item in eligible}) >= required
	def select_authorized_group(self, groups, *, allow_routine_self=True, allow_falsifier_or_cached=True):
		r = None
		for path, (package, reviews) in reversed(list(groups.items())):
			eligible = [item for item in reviews if (allow_routine_self and 'routine' == package['risk']) or item.get('independent')]
			latest = self.latest_for_subject(package)
			if not self.has_unhandled_verdicts(package, latest):
				eligible = [item for item in eligible if latest[item['reviewer_id']]['id'] == item['id']]
				if self.quorum_satisfied(package, latest, eligible, allow_falsifier_or_cached=allow_falsifier_or_cached):
					r = (path, package, eligible)
					break
		return r
	def significant_findings(self, subject):
		r = False
		for entry in self.state['reviews']:
			if REVIEW_SCHEMA == entry.get('schema_version') and entry.get('subject_sha256') == subject and self.entry_proof_current(entry):
				report = json.loads(inside(self.root, entry['report']).read_text(encoding='utf-8'))
				if any((f.get('severity') in ('significant', 'critical') for f in report.get('findings', []))):
					r = True
					break
		return r
class ReviewReportValidator:
	def __init__(self, package, *, candidate=None, text_checks=(), source_reviewer=None):
		self.candidate = candidate
		self.expected = {c['claim_id'] for c in package['claims']}
		self.package = package
		self.package_claims = {c['claim_id']: c for c in package['claims']}
		self.pkg_root = Path(package['project_root']).resolve() if is_nonempty_text(package.get('project_root')) else None
		self.source_reviewer = source_reviewer
		self.targets = {c['claim_id']: c['essence'] for c in package['claims']}
		self.text_checks = tuple(text_checks)
	def _check_alignment_and_outcome(self, ident, item, result, issues):
		from .claims import source_numeric_tokens, standalone_numbers
		alignment = item.get('test_alignment')
		if not isinstance(alignment, dict) or alignment.get('target_claim') != self.targets.get(ident) or any((not is_nonempty_text(alignment.get(k)) for k in ('tested_claim', 'rationale', 'counterexample'))) or (alignment.get('relationship') not in ('direct', 'proxy', 'irrelevant')):
			issues.append(f'{ident}: test_alignment must bind the exact claim, actual tested statement, relationship, rationale and a concrete counterexample')
		elif 'proxy' == alignment['relationship'] and 'supported' == item.get('outcome'):
			issues.append(f'{ident}: a proxy test cannot support the broader target; qualify the claim and show the limitation in the response')
		elif 'irrelevant' == alignment['relationship'] and 'unsupported' != item.get('outcome'):
			issues.append(f'{ident}: an irrelevant test must leave the target unsupported')
		if item.get('outcome') not in ('supported', 'qualified', 'unsupported'):
			issues.append(f'{ident}: unsupported review outcome')
		if 'unsupported' == item.get('outcome') and 'approved' == result:
			issues.append(f'{ident}: an unsupported claim requires needs_changes')
		if 'qualified' == item.get('outcome'):
			excerpt = item.get('response_qualification')
			if not is_nonempty_text(excerpt):
				issues.append(f'{ident}: qualified claim needs an exact response_qualification excerpt')
			elif None is not self.candidate and excerpt not in self.candidate:
				issues.append('Claim qualification must occur verbatim in the exact response')
		if ident in self.package_claims and 'supported' == item.get('outcome') and (not item.get('preflight_numeric_grounded')):
			pkg_claim = self.package_claims[ident]
			claim_nums = standalone_numbers(str(pkg_claim.get('essence', '')) + '\n' + str(pkg_claim.get('response_excerpt', '')))
			if claim_nums:
				obs_corpus = str(item.get('observed', '')) + '\n' + str((alignment or {}).get('tested_claim', ''))
				missing_nums = sorted(claim_nums - source_numeric_tokens(obs_corpus))
				if missing_nums:
					issues.append(f'{ident}: claim/response numeric figures {missing_nums} are not confirmed in reviewer observed/tested_claim')
	def _check_claim_reviews(self, data, issues):
		if not isinstance(data.get('claim_reviews'), list):
			issues.append('Per-claim review coverage is required')
		else:
			covered = set()
			for item in data['claim_reviews']:
				if not isinstance(item, dict):
					issues.append('Claim review must be an object')
					continue
				ident = item.get('claim_id')
				if not is_nonempty_text(ident):
					issues.append('Claim review needs a string claim_id')
					continue
				if ident not in self.expected or ident in covered:
					issues.append('Claim review must cover each response claim exactly once')
				covered.add(ident)
				for field in ('observed', 'inferred', 'method', 'alternatives', 'limits', 'falsification', 'raw_vs_criteria'):
					if not is_nonempty_text(item.get(field)):
						issues.append(f'{ident}: review {field} must explain the evidence assessment')
				self._check_alignment_and_outcome(ident, item, data.get('result'), issues)
			merkle_unverified = set((self.package.get('merkle_delta') or {}).get('unverified_claim_ids') or [])
			if covered != self.expected and (not (data.get('use_merkle_delta') and covered == merkle_unverified)):
				issues.append('Every response claim requires an authored evidence assessment')
	def _check_disproved_claim(self, dc, issues):
		from .source_grounding import classify_provenance_tier, norm_quote_text, quote_segments_present
		cid_val = dc.get('claim_id')
		if cid_val not in self.expected:
			issues.append('Each disproved_claims entry must reference a valid response claim_id')
		for req_field in ('excerpt_from_answer', 'contradicting_tier0_source', 'verbatim_quote_from_source', 'falsification_reason'):
			if not is_nonempty_text(dc.get(req_field)):
				issues.append(f"disproved_claims[{cid_val or '?'}]: {req_field} is required")
		src_str = dc.get('contradicting_tier0_source')
		quote_str = dc.get('verbatim_quote_from_source')
		if is_nonempty_text(src_str):
			src_cand = Path(src_str)
			if None is not self.pkg_root and (not src_cand.is_absolute()):
				src_cand = (self.pkg_root / src_cand).resolve()
			if 'tier_0' != classify_provenance_tier(src_cand, self.pkg_root):
				issues.append(f"disproved_claims[{cid_val or '?'}]: contradicting_tier0_source ({src_str}) must be a Tier 0 primary source")
			elif src_cand.is_file() and is_nonempty_text(quote_str):
				try:
					raw_src = src_cand.read_text(encoding='utf-8', errors='replace')
					if not quote_segments_present(quote_str, norm_quote_text(raw_src), 8):
						issues.append(f"disproved_claims[{cid_val or '?'}]: verbatim_quote_from_source is absent from Tier 0 source {src_str}")
				except OSError:
					pass
	def _check_envelope(self, data, issues):
		if REVIEW_SCHEMA != data.get('schema_version'):
			issues.append('Review report schema_version 2 is required')
		if data.get('result') not in ('approved', 'needs_changes'):
			issues.append('Review result must be approved or needs_changes')
		required_scope = self.package.get('scope', list(SCOPES)) if 'client_text' == self.package.get('kind') else SCOPES
		if not isinstance(data.get('scope'), list) or not all((is_nonempty_text(x) for x in data['scope'])) or (not set(required_scope).issubset(data['scope'])):
			issues.append('Review must cover the required subject scope: ' + ', '.join(required_scope))
	def _check_falsifier(self, data, issues):
		disproved = data.get('disproved_claims')
		if not isinstance(disproved, list):
			issues.append('Adversarial falsifier report requires a disproved_claims list')
		else:
			for dc in disproved:
				if not isinstance(dc, dict):
					issues.append('Each disproved_claims entry must be an object')
					continue
				self._check_disproved_claim(dc, issues)
			if disproved and 'approved' == data.get('result'):
				issues.append('Adversarial falsifier report with non-empty disproved_claims requires needs_changes')
			if not disproved and 'needs_changes' == data.get('result') and (not data.get('findings')):
				issues.append('Adversarial falsifier needs_changes verdict requires at least one disproved_claims entry or open finding')
	def _check_findings(self, data, issues):
		findings = data.get('findings')
		if not isinstance(findings, list):
			issues.append('Review findings list is required')
		else:
			seen = set()
			for finding in findings:
				if not isinstance(finding, dict):
					issues.append('Finding must be an object')
					continue
				ident = finding.get('id')
				if not is_nonempty_text(ident):
					issues.append('Findings need string IDs')
					continue
				if ident in seen:
					issues.append('Findings need unique IDs')
				seen.add(ident)
				if finding.get('status') not in ('open', 'resolved', 'rejected'):
					issues.append('Finding status must be open, resolved or rejected')
				if finding.get('severity') not in ('minor', 'significant', 'critical') or (not is_nonempty_text(finding.get('description'))):
					issues.append('Finding needs severity and description')
				if finding.get('severity') in ('significant', 'critical') and 'approved' == data.get('result') and ('routine' == self.package['risk']):
					issues.append('A significant/critical finding cannot approve a routine package; prepare significant review')
				if not isinstance(finding.get('claim_ids'), list) or any((c not in self.expected for c in finding['claim_ids'])):
					issues.append('Finding claim_ids must refer to response manifest claims')
				if finding.get('status') in ('resolved', 'rejected') and (not is_nonempty_text(finding.get('disposition')) or not finding.get('evidence')):
					issues.append('Closed finding needs an authored disposition and evidence')
	def _check_text_checks(self, data, issues):
		if self.text_checks:
			for item in data.get('claim_reviews', []):
				if isinstance(item, dict):
					checks = item.get('text_checks')
					if not isinstance(checks, dict) or any((not is_nonempty_text(checks.get(key)) for key in self.text_checks)):
						issues.append(str(item.get('claim_id')) + ': assess source applicability, scope, role, relevance, deduplication and numerical provenance')
	@staticmethod
	def is_falsifier_report(data):
		return 'falsifier' == data.get('review_mode') or ('disproved_claims' in data and 'claim_reviews' not in data)
	def validate(self, data):
		r = []
		self._check_envelope(data, r)
		if self.is_falsifier_report(data):
			self._check_falsifier(data, r)
		else:
			self._check_claim_reviews(data, r)
		self._check_findings(data, r)
		self._check_text_checks(data, r)
		if None is not self.source_reviewer:
			try:
				self.source_reviewer(data, self.package)
			except (OSError, ValueError, KeyError, TypeError) as exc:
				r.append(str(exc))
		return r
def digest(payload):
	return hashlib.sha256(payload).hexdigest()
def findings_closed(root, entry):
	return ReviewQuorumEvaluator(root, {'reviews': []}).findings_closed(entry)
def has_unhandled_verdicts(root, state, package, latest):
	return ReviewQuorumEvaluator(root, state).has_unhandled_verdicts(package, latest)
def is_nonempty_text(value):
	return isinstance(value, str) and bool(value.strip())
def latest_for_subject(state, package):
	return ReviewQuorumEvaluator('.', state).latest_for_subject(package)
_findings_closed = findings_closed
_latest_for_subject = latest_for_subject
_text = is_nonempty_text
_unhandled_verdicts = has_unhandled_verdicts
def load_verified_claims_cache(root) -> dict:
	path = Path(root).resolve() / 'ꘖ/data/verified-claims.json'
	r = {'version': 1, 'claims': {}}
	if path.is_file():
		try:
			data = json.loads(path.read_text(encoding='utf-8'))
			if isinstance(data, dict) and isinstance(data.get('claims'), dict):
				r = data
		except (OSError, ValueError):
			pass
	return r
def _claim_evidence_pairs(claim_id: str, index: dict, evidence_inputs: dict | None = None, _visited: set | None = None) -> list[tuple[str, str]]:
	from .claims import collect_claim_closure
	visited = set() if None is _visited else _visited
	if not _text(claim_id) or claim_id in visited:
		r = []
	else:
		ev_map = evidence_inputs if isinstance(evidence_inputs, dict) else {}
		pairs: dict[str, str] = {}
		for cid in collect_claim_closure([claim_id], index):
			if cid in visited:
				continue
			claim = index.get(cid) or {}
			for ref in list(claim.get('evidence') or []) + list(claim.get('primary_evidence') or []):
				if not isinstance(ref, dict):
					continue
				for key in ('source', 'observation', 'manifest'):
					val = ref.get(key)
					if _text(val):
						s = val.strip()
						sha = ev_map.get(s) or (str(ref.get('source_sha256') or '') if 'source' == key else '')
						if s not in pairs or (not pairs[s] and sha):
							pairs[s] = sha
		r = sorted(pairs.items())
	return r
def _claim_evidence_sources(claim_id: str, index: dict) -> list[str]:
	return [s for s, _ in _claim_evidence_pairs(claim_id, index, {})]
def claim_merkle_hash(claim_entry: dict, index: dict, evidence_inputs: dict) -> str:
	ident = claim_entry.get('claim_id', '')
	claim_obj = index.get(ident) or {}
	ev_pairs = _claim_evidence_pairs(ident, index, evidence_inputs or {})
	norm_excerpt = ' '.join(str(claim_entry.get('response_excerpt', '')).split())
	payload = json_data({
		'claim_id': ident,
		'claim_sha256': claim_entry.get('claim_sha256', ''),
		'knowledge_type': claim_entry.get('knowledge_type') or claim_obj.get('knowledge_type') or '',
		'verification_status': claim_entry.get('verification_status') or claim_obj.get('verification_status') or '',
		'response_excerpt': norm_excerpt,
		'evidence_hashes': ev_pairs,
	})
	return digest(payload)
def compute_claim_merkle_delta(root, manifest: list[dict], value: dict, evidence_inputs: dict) -> dict:
	from .claims import claim_index
	index = claim_index(value)
	cache = load_verified_claims_cache(root).get('claims', {})
	cached_ids = []
	unverified_ids = []
	merkle_hashes = {}
	for item in manifest:
		ident = item['claim_id']
		m_hash = claim_merkle_hash(item, index, evidence_inputs or {})
		merkle_hashes[ident] = m_hash
		cached_entry = cache.get(ident)
		if isinstance(cached_entry, dict) and cached_entry.get('merkle_sha256') == m_hash and cached_entry.get('claim_sha256') == item.get('claim_sha256'):
			cached_ids.append(ident)
		else:
			unverified_ids.append(ident)
	return {
		'cached_claim_ids': cached_ids,
		'unverified_claim_ids': unverified_ids,
		'merkle_hashes': merkle_hashes,
	}
def read_package_envelope(root, reference, *, expected_kind=None, error_msg='Invalid immutable review package'):
	root_p = Path(root).resolve()
	path = inside(root_p, reference)
	raw, data = read_addressed_json(path, suffix='-inputs.json', error_msg=error_msg)
	if REVIEW_SCHEMA != data.get('schema_version') or (None is not expected_kind and data.get('kind') != expected_kind) or data.get('project_root') != str(root_p) or (data.get('subject_sha256') != subject_digest(data)):
		raise ValueError(error_msg)
	resp = data.get('response') if isinstance(data.get('response'), dict) else {}
	candidate = inside(root_p, resp.get('file', ''))
	cand_bytes = candidate.read_bytes() if candidate.is_file() else None
	if None is cand_bytes or digest(cand_bytes) != resp.get('sha256') or (None is not resp.get('bytes') and len(cand_bytes) != resp.get('bytes')):
		raise ValueError('Reviewed candidate response bytes differ or are missing')
	return (root_p, raw, data, cand_bytes)
def resolve_addressed_reviews(root, data, package, independent, existing_reviews):
	addresses = data.get('addresses_reviews', [])
	if not isinstance(addresses, list):
		raise ValueError('addresses_reviews must be an authored list of previous verdict resolutions')
	addressed, extra_proofs = ([], [])
	if addresses:
		if not independent or 'approved' != data.get('result'):
			raise ValueError('Only a new independent authored approval can address another reviewer verdict')
		prior_by_id = {item.get('id'): item for item in existing_reviews}
		for resolution in addresses:
			prior = prior_by_id.get(resolution.get('review_id')) if isinstance(resolution, dict) and is_nonempty_text(resolution.get('review_id')) else None
			if not prior or prior.get('subject_sha256') != package['subject_sha256'] or (not is_nonempty_text(resolution.get('basis'))) or (not isinstance(resolution.get('evidence'), list)) or (not resolution['evidence']):
				raise ValueError('Authored review resolution needs same-subject prior verdict, basis and saved evidence')
			addressed.append(prior['id'])
			extra_proofs += [inside(root, item).relative_to(root).as_posix() for item in resolution['evidence']]
		if len(set(addressed)) != len(addressed):
			raise ValueError('Duplicate addressed review verdict')
	return (addressed, extra_proofs)
def update_verified_claims_cache(root, package: dict, value: dict | None = None) -> dict:
	from .claims import claim_index
	root_p = Path(root).resolve()
	val = value
	if None is val:
		try:
			val = _analysis(root_p)
		except (OSError, ValueError):
			val = {}
	index = claim_index(val)
	ev_inputs = package.get('evidence_inputs') or {}
	r = load_verified_claims_cache(root_p)
	claims_map = r.setdefault('claims', {})
	for item in package.get('claims') or []:
		if isinstance(item, dict) and is_nonempty_text(item.get('claim_id')):
			ident = item['claim_id']
			claim_obj = index.get(ident) or {}
			m_hash = (package.get('merkle_delta') or {}).get('merkle_hashes', {}).get(ident) or claim_merkle_hash(item, index, ev_inputs)
			claims_map[ident] = {'claim_id': ident, 'claim_sha256': item.get('claim_sha256', ''), 'knowledge_type': item.get('knowledge_type') or claim_obj.get('knowledge_type') or '', 'verification_status': item.get('verification_status') or claim_obj.get('verification_status') or '', 'tier0_evidence_hashes': dict(_claim_evidence_pairs(ident, index, ev_inputs)), 'merkle_sha256': m_hash, 'response_sha256': (package.get('response') or {}).get('sha256', '')}
	path = root_p / 'ꘖ/data/verified-claims.json'
	if path.parent.is_dir() or (root_p / 'ꘖ').is_dir():
		replace_bytes(path, json_data(r))
	return r
def build_blind_verification_predicates(manifest: list[dict], value: dict) -> list[dict]:
	from .claims import claim_index
	index = claim_index(value)
	r = []
	for item in manifest:
		ident = item['claim_id']
		raw_essence = str(item.get('essence') or '')
		clean_predicate = re.sub('(?:\\s*\\(\\d{1,3}%\\)|\\s+with\\s+\\d{1,3}%\\s+(?:confidence|probability|plausibility|score)|\\s*[—–-]\\s*\\d{1,3}%)', '', raw_essence, flags=re.I).strip()
		r.append({
			'claim_id': ident,
			'knowledge_type': item.get('knowledge_type'),
			'atomic_predicate': clean_predicate,
			'primary_sources': _claim_evidence_sources(ident, index),
			'question': f'Does the Tier 0 primary evidence directly entail or falsify the atomic statement for {ident}: "{clean_predicate}"?',
		})
	return r
def _immutable(path, payload):
	return write_immutable_bytes(path, payload, diff_error='Immutable review artifact differs; preserve the original and create a new attempt')
def _package_handler(kind):
	if 'client_text' == kind and kind not in PACKAGE_HANDLERS:
		importlib.import_module('.text_review', __package__)
	return PACKAGE_HANDLERS.get(kind)
def request_snapshot(state):
	return [{'id': item['id'], 'text': item['text']} for item in state['requests']]
def _analysis(root):
	from .analysis import analysis_issues
	from .evidence import evidence_issues
	path = Path(root) / 'ꘖ/KB/Analysis.json'
	value = json.loads(path.read_text(encoding='utf-8-sig'))
	if not isinstance(value, dict) or 3 != value.get('schema_version'):
		raise ValueError('New review and publication require Analysis schema 3; legacy files remain readable')
	if analysis_issues(value) or evidence_issues(root, value, skip_structural=True):
		raise ValueError('Resolve Analysis schema 3 and evidence diagnostics before preparing or accepting review')
	r = value
	return r
def _approved_digests(root, state, *, exclude_package=None):
	return ReviewQuorumEvaluator(root, state).approved_claim_digests(exclude_package=exclude_package)
def classification(root, state, spec, response, value, *, exclude_package=None):
	return ReviewClassifier(root, state, value, exclude_package=exclude_package).classify(spec, response)
def parse_report_object(text):
	value = text.strip()
	if value.startswith('```'):
		match = re.fullmatch('```(?:json)?\\s*\\n(.*?)\\n```', value, re.S)
		if not match:
			raise ValueError('Reviewer final output must be one JSON report, optionally one fenced JSON block')
		value = match.group(1)
	try:
		result = json.loads(value)
	except ValueError as exc:
		raise ValueError('Reviewer authored final output is not a JSON report') from exc
	if not isinstance(result, dict):
		raise ValueError('Reviewer report must be a JSON object')
	return result
_report_object = parse_report_object
# 2026-10-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
# https://github.com/dmitry-ai/harness/issues/12
def prepare(root, parent_id, spec, response):
	from .workflow import load, hashes, kb_paths, evidence_paths, doc4_sentence_issues
	from .source_grounding import discover_entity_tier0_sources, local_source_grounding_issues, sync_fact_ledger
	root = Path(root).resolve()
	if not _text(parent_id) or not _text(response):
		raise ValueError('Observed parent ID and the exact nonempty candidate response are required')
	state = load(root)
	requests = request_snapshot(state)
	if not requests:
		raise ValueError('Save/import the exact current requests before preparing review')
	value = _analysis(root)
	if isinstance(value, dict) and [] == value.get('red_flags') and re.search('(?im)^\\s*#{1,6}\\s+Red Flags\\b', response):
		raise ValueError('Do not include a Red Flags heading in the response when Analysis.json red_flags is empty (INIT-5)')
	if re.search('(?im)(?:generated\\s+at\\s+the\\s+`?finalize`?\\s+stage|\\u0444\\u043e\\u0440\\u043c\\u0438\\u0440\\u0443\\u0435\\u0442\\u0441\\u044f\\s+\\u043d\\u0430\\s+\\u044d\\u0442\\u0430\\u043f\\u0435\\s+`?finalize`?)|^\\s*#{1,6}\\s*(?:\\d+(?:\\.\\d+)*\\.?\\s*)?(?:Project\\s+Artifacts|\\u0410\\u0440\\u0442\\u0435\\u0444\\u0430\\u043a\\u0442\\u044b\\s+\\u043f\\u0440\\u043e\\u0435\\u043a\\u0442\\u0430)\\b', response):
		raise ValueError('Candidate response must not contain internal service notes or uninitialized finalize placeholders (INIT-4)')
	doc4_issues = doc4_sentence_issues(response)
	if doc4_issues:
		raise ValueError('\n'.join(doc4_issues))
	sync_fact_ledger(root)
	grounding_issues = local_source_grounding_issues(root, response)
	if grounding_issues:
		raise ValueError('\n'.join(grounding_issues))
	classified = classification(root, state, spec, response, value)
	payload = response.encode('utf-8')
	response_sha = digest(payload)
	candidate = root / 'ꘖ/KB/Evidence/Reviews/Candidates' / (response_sha + '.txt')
	_immutable(candidate, payload)
	ev_inputs = hashes(root, evidence_paths(root))
	extra_pkg = {'auto_tier0_evidence': discover_entity_tier0_sources(root, response), 'merkle_delta': compute_claim_merkle_delta(root, classified['claims'], value, ev_inputs), 'blind_verification_predicates': build_blind_verification_predicates(classified['claims'], value)}
	if isinstance(spec, dict) and spec.get('review_mode') in ('standard', 'falsifier'):
		extra_pkg['review_mode'] = spec['review_mode']
	data = {'schema_version': REVIEW_SCHEMA, 'project_root': str(root), 'job_id': state['job_id'], 'parent_id': parent_id, **classified, 'requests': requests, 'response': {'file': candidate.relative_to(root).as_posix(), 'sha256': response_sha, 'bytes': len(payload)}, 'kb_inputs': hashes(root, kb_paths(root)), 'evidence_inputs': ev_inputs, 'scope': list(SCOPES), 'knowledge_source': 'agent KB, primary evidence, current requests and exact response; no Context.md', **extra_pkg}
	data['subject_sha256'] = subject_digest(data)
	if 'routine' == data['risk'] and ReviewQuorumEvaluator(root, state).significant_findings(data['subject_sha256']):
		raise ValueError('A significant/critical finding on this exact answer requires a significant package and two independent A.A')
	package_bytes = json_data(data)
	path = root / 'ꘖ/KB/Evidence/Reviews' / (digest(package_bytes) + '-inputs.json')
	_immutable(path, package_bytes)
	return {'package': path.relative_to(root).as_posix(), 'package_sha256': digest(package_bytes), **data}
def prepare_verdict_record(root, report, *, parent_id, reviewer_id, native_evidence=None, allow_self=True, expected_risk=None, package_reader=None, issue_checker=None, reviews_dir_fn=None, artifact_prefix_fn=None, diff_error='Immutable review artifact differs; preserve the original and create a new attempt'):
	root_p = Path(root).resolve()
	if not is_nonempty_text(parent_id) or (not is_nonempty_text(reviewer_id)):
		raise ValueError('Observed A.A parent/reviewer IDs are required')
	source_payload = report if isinstance(report, bytes) else inside(root_p, report).read_bytes()
	data = parse_report_object(source_payload.decode('utf-8-sig'))
	package_path = data.get('package')
	if not is_nonempty_text(package_path):
		raise ValueError('Review report must identify its immutable package')
	reader = read_package if None is package_reader else package_reader
	package = reader(root_p, package_path)
	package_sha = digest(inside(root_p, package_path).read_bytes())
	if data.get('package_sha256') != package_sha or package.get('parent_id') != parent_id:
		raise ValueError('Reviewer package hash/parent differs')
	if None is not expected_risk and expected_risk != package['risk']:
		raise ValueError('Risk is fixed in the reviewed package; record-review cannot change it')
	candidate = inside(root_p, package['response']['file']).read_text(encoding='utf-8')
	checker = (lambda d, p, c: report_issues(d, p, candidate=c)) if None is issue_checker else issue_checker
	issues = checker(data, package, candidate)
	if issues:
		raise ValueError('\n'.join(issues))
	independent, proof_paths, native, raw_payload = authenticate_report(root_p, package, package_path, data, source_payload, parent_id=parent_id, reviewer_id=reviewer_id, native_evidence=native_evidence, allow_self=allow_self)
	review_id = digest((package_sha + '\x00' + reviewer_id + '\x00' + digest(raw_payload)).encode())
	folder = (root_p / 'ꘖ/KB/Evidence/Reviews' / package_sha) if None is reviews_dir_fn else reviews_dir_fn(root_p, package_sha)
	prefix = (hashlib.sha256(reviewer_id.encode()).hexdigest()[:16] + '-' + review_id) if None is artifact_prefix_fn else artifact_prefix_fn(reviewer_id, review_id)
	report_file = write_immutable_bytes(folder / f'{prefix}-report.json', json_data(data), diff_error=diff_error)
	authored_file = write_immutable_bytes(folder / f'{prefix}-authored.txt', raw_payload, diff_error=diff_error)
	report_rel = report_file.relative_to(root_p).as_posix()
	authored_rel = authored_file.relative_to(root_p).as_posix()
	proof_paths += [report_rel, authored_rel]
	for finding in data['findings']:
		if finding.get('status') in ('resolved', 'rejected'):
			ev_items = finding['evidence'] if isinstance(finding['evidence'], list) else [finding['evidence']]
			proof_paths += [inside(root_p, item).relative_to(root_p).as_posix() for item in ev_items]
	return {'root': root_p, 'data': data, 'package': package, 'package_path': package_path, 'package_sha': package_sha, 'candidate': candidate, 'independent': independent, 'proof_paths': proof_paths, 'native': native, 'review_id': review_id, 'report_rel': report_rel, 'authored_rel': authored_rel}
def quorum_satisfied(root, state, package, latest, eligible, *, allow_falsifier_or_cached=True) -> bool:
	return ReviewQuorumEvaluator(root, state).quorum_satisfied(package, latest, eligible, allow_falsifier_or_cached=allow_falsifier_or_cached)
def subject_digest(package):
	if 'client_text' != package.get('kind'):
		r = digest(json_data({k: package[k] for k in ('project_root', 'job_id', 'requests', 'response', 'kb_inputs', 'evidence_inputs')}))
	else:
		r = digest(json_data({k: package[k] for k in ('project_root', 'job_id', 'requests', 'target', 'kb_inputs', 'evidence_inputs')} | {'response_sha256': package['response']['sha256'], 'baseline_sha256': package['baseline']['sha256']}))
	return r
def significant_findings(root, state, subject):
	return ReviewQuorumEvaluator(root, state).significant_findings(subject)
def read_package(root, package, *, state=None, require_current=True):
	from .claims import claim_digest, claim_index
	from .workflow import evidence_paths, hashes, kb_paths, load
	_, peek = read_addressed_json(inside(Path(root).resolve(), package), suffix='-inputs.json', error_msg='Immutable answer-bound review package schema 2 is required')
	handler = _package_handler(peek.get('kind'))
	if None is not handler:
		r = handler['package_reader'](root, package, require_current=require_current)
	else:
		root_p, _, data, cand_bytes = read_package_envelope(root, package, error_msg='Immutable answer-bound review package schema 2 is required')
		cur_state = state or load(root_p)
		if data.get('job_id') != cur_state['job_id']:
			raise ValueError('Review package belongs to another project')
		if require_current:
			if data.get('kb_inputs') != hashes(root_p, kb_paths(root_p)) or data.get('evidence_inputs') != hashes(root_p, evidence_paths(root_p)):
				raise ValueError('Review package does not match present KB and primary evidence')
			if data.get('requests') != request_snapshot(cur_state):
				raise ValueError('Review package does not cover the exact current requests')
			value = _analysis(root_p)
			index = claim_index(value)
			is_finalized = 'complete' == cur_state.get('stages', {}).get('finalize', {}).get('status')
			if any(((c['claim_id'] not in index and (not is_finalized)) or (c['claim_id'] in index and c['claim_sha256'] != claim_digest(index[c['claim_id']])) for c in data['claims'])):
				raise ValueError('Reviewed response claim version changed')
			classification(root_p, cur_state, {'risk': data['risk'], 'basis': data['risk_basis'], 'request_scope': data['request_scope'], 'claim_ids': [c['claim_id'] for c in data['claims']], 'claims': data['claims'], 'task_flags': data['task_flags']}, cand_bytes.decode('utf-8'), value, exclude_package=package)
			if 'routine' == data['risk'] and ReviewQuorumEvaluator(root_p, cur_state).significant_findings(data['subject_sha256']):
				raise ValueError('A significant/critical finding requires a significant package and two independent A.A')
		r = data
	return r
def input_receipt(root, package):
	import os
	from .runtime import platform_name
	from .workflow import file_hash
	data = read_package(root, package)
	reviewer = os.environ.get('CODEX_THREAD_ID') or os.environ.get('ANTIGRAVITY_CONVERSATION_ID')
	if not reviewer and 'codex' == platform_name() and os.environ.get('CODEX_HOME'):
		raise ValueError('Native Codex reviewer thread ID is unavailable')
	handler = _package_handler(data.get('kind'))
	contract = handler['contract_factory']() if None is not handler and None is not handler.get('contract_factory') else dict(REPORT_CONTRACT)
	return {'upwork_review_input': 1, 'review_schema_version': REVIEW_SCHEMA, 'verified': True, 'project_root': str(Path(root).resolve()), 'job_id': data['job_id'], **{k: data[k] for k in ('project_id', 'project_kind') if k in data}, 'parent_id': data['parent_id'], 'reviewer_id': reviewer, 'package': package, 'package_sha256': file_hash(inside(root, package)), 'kb_inputs': data['kb_inputs'], 'evidence_inputs': data['evidence_inputs'], 'requests': data['requests'], 'response': data['response'], 'claims': data['claims'], 'risk': data['risk'], 'report_contract': contract, **{k: data[k] for k in ('kind', 'goal', 'diff', 'operation', 'check', 'manifest', 'source_checks', 'auto_tier0_evidence', 'merkle_delta', 'blind_verification_predicates', 'review_mode') if k in data}}
def register_package_handler(kind, *, package_reader, contract_factory=None):
	PACKAGE_HANDLERS[kind] = {'package_reader': package_reader, 'contract_factory': contract_factory}
def report_issues(data, package, *, candidate=None):
	return ReviewReportValidator(package, candidate=candidate).validate(data)
def authenticate_report(root, package, package_path, data, source_payload, *, parent_id, reviewer_id, native_evidence=None, allow_self=True):
	independent = reviewer_id != parent_id
	proof_paths = [package_path, package['response']['file']]
	if not independent:
		if 'routine' != package['risk']:
			raise ValueError('Significant claims require two independent reviewers')
		if not allow_self or 'routine' != package['risk'] or 'self_review' != data.get('review_kind'):
			raise ValueError('This subject requires an independent reviewer; only explicit routine analysis self_review is allowed')
		from .platforms import adapter
		adapter().require_current_binding(root, parent_id)
		native = {'model_verification': 'parent self-review; see observed execution metadata'}
		raw_payload = source_payload
	else:
		if not _text(native_evidence):
			raise ValueError('Independent report requires separate native_evidence proof')
		native = json.loads(inside(root, native_evidence).read_text(encoding='utf-8'))
		if native.get('parent_id') != parent_id or native.get('reviewer_id') != reviewer_id or 'completed' != native.get('status'):
			raise ValueError('Saved native reviewer identity/status differs')
		from .metrics import verify_native_proof
		observed = verify_native_proof(root, native, package=Path(package_path).name)
		final_response = observed.get('final_response')
		if not _text(final_response) or digest(final_response.encode('utf-8')) != observed.get('final_response_sha256'):
			raise ValueError('Native adapter must provide the actual authored final response and verified hash')
		if parse_report_object(final_response) != data:
			raise ValueError('Submitted report differs from the actual native reviewer verdict')
		raw_payload = final_response.encode('utf-8')
		proof_paths.append(native_evidence)
	return (independent, proof_paths, native, raw_payload)
# 2026-10-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
# https://github.com/dmitry-ai/harness/issues/12
def record(root, report, *, parent_id, reviewer_id, role='AA', native_evidence=None, risk=None):
	from .workflow import hashes, load, now, update
	if 'AA' != role:
		raise ValueError('Observed A.A parent/reviewer IDs are required')
	prepared = prepare_verdict_record(root, report, parent_id=parent_id, reviewer_id=reviewer_id, native_evidence=native_evidence, expected_risk=risk)
	root_p, data, package, review_id = (prepared['root'], prepared['data'], prepared['package'], prepared['review_id'])
	existing = load(root_p)['reviews'] if isinstance(data.get('addresses_reviews'), list) and data.get('addresses_reviews') else []
	addressed_ids, extra_proofs = resolve_addressed_reviews(root_p, data, package, prepared['independent'], existing)
	proof_paths = prepared['proof_paths'] + extra_proofs
	report_mode = 'falsifier' if ReviewReportValidator.is_falsifier_report(data) else package.get('review_mode', 'standard')
	def change(state):
		read_package(root_p, prepared['package_path'], state=state)
		if not any((item.get('id') == review_id for item in state['reviews'])):
			state['reviews'].append({'schema_version': REVIEW_SCHEMA, 'id': review_id, 'parent_id': parent_id, 'reviewer_id': reviewer_id, 'role': role, 'risk': package['risk'], 'review_mode': report_mode, 'package': prepared['package_path'], 'package_sha256': prepared['package_sha'], 'result': data['result'], 'subject_sha256': package['subject_sha256'], 'report': prepared['report_rel'], 'authored_response': prepared['authored_rel'], 'proof': hashes(root_p, proof_paths), 'independent': prepared['independent'], 'kb_inputs': package['kb_inputs'], 'evidence_inputs': package['evidence_inputs'], 'response_sha256': package['response']['sha256'], 'requests': package['requests'], 'native_evidence': native_evidence, 'dispositions': [], 'addresses_reviews': addressed_ids, 'model_verification': prepared['native'].get('model_verification', 'unverified'), 'time': now()})
	return update(root_p, {'action': 'review', 'reviewer_id': reviewer_id, 'result': data['result'], 'review_id': review_id}, change)
# 2026-10-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
# https://github.com/dmitry-ai/harness/issues/12
def disposition(root, review_id, finding_id, status, basis, evidence, parent_id):
	from .workflow import load, hashes, update, now
	from .platforms import adapter
	root = Path(root).resolve()
	if status not in ('resolved', 'rejected') or not _text(basis) or (not evidence):
		raise ValueError('Disposition needs resolved/rejected status, basis and saved evidence')
	adapter().require_current_binding(root, parent_id)
	state = load(root)
	entry = next((r for r in state['reviews'] if r.get('id') == review_id), None)
	if not entry or REVIEW_SCHEMA != entry.get('schema_version') or entry['parent_id'] != parent_id:
		raise ValueError('Current parent and immutable review ID required')
	data = json.loads(inside(root, entry['report']).read_text(encoding='utf-8'))
	if finding_id not in {f['id'] for f in data['findings']}:
		raise ValueError('Finding does not exist in the original report')
	payload = {'schema_version': 1, 'review_id': review_id, 'finding_id': finding_id, 'parent_id': parent_id, 'status': status, 'basis': basis, 'evidence': hashes(root, evidence), 'time': now()}
	encoded = json_data(payload)
	target = _immutable(root / 'ꘖ/KB/Evidence/Reviews/Dispositions' / (digest(encoded) + '.json'), encoded)
	relative = target.relative_to(root).as_posix()
	def change(current):
		saved = next((r for r in current['reviews'] if r.get('id') == review_id))
		saved.setdefault('dispositions', []).append({'file': relative, 'proof': hashes(root, [relative, *payload['evidence']])})
	return update(root, {'action': 'review_disposition', 'review_id': review_id, 'finding_id': finding_id}, change)
# 2026-10-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
# https://github.com/dmitry-ai/harness/issues/12
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
# https://github.com/dmitry-ai/harness/issues/43
# 2026-11-04 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Scope research questions to active turn, distinguish factual KB notes from hypotheses, and reconcile unprepared chat deliveries":
# https://github.com/dmitry-ai/harness/issues/44
def authorize(root, state, *, response=None, package_path=None, request_ids=None):
	from .workflow import check_project, questions_current
	value = _analysis(root)
	is_finalized = 'complete' == state.get('stages', {}).get('finalize', {}).get('status')
	if not is_finalized:
		if not questions_current(root, state) or not check_project(root)['valid']:
			raise ValueError('Complete current research questions/gaps and resolve KB/evidence diagnostics before publication')
	else:
		finalize_time = state.get('stages', {}).get('finalize', {}).get('time')
		relevant_qs = {}
		for qid, q in (state.get('questions') or {}).items():
			q_time = q.get('time') or q.get('created_at')
			if request_ids and q.get('request_id') in request_ids:
				relevant_qs[qid] = q
			elif finalize_time and q_time and (q_time > finalize_time):
				relevant_qs[qid] = q
		if relevant_qs and (not questions_current(root, {**state, 'questions': relevant_qs})):
			raise ValueError('Complete current research questions/gaps before publication')
	evaluator = ReviewQuorumEvaluator(root, state)
	response_sha = digest(response.encode('utf-8')) if None is not response else None
	groups, diagnostics = ({}, [])
	for entry in state['reviews']:
		if REVIEW_SCHEMA != entry.get('schema_version') or (package_path and entry.get('package') != package_path) or (response_sha and entry.get('response_sha256') != response_sha):
			continue
		try:
			package = read_package(root, entry['package'], state=state)
			if not evaluator.entry_proof_current(entry):
				raise ValueError('Review proof changed')
			if 'approved' != entry['result'] or not evaluator.findings_closed(entry):
				raise ValueError('Reviewer needs changes or has open findings; parent disposition cannot replace an approval')
			if entry.get('independent'):
				verify_entry_native_proof(root, entry, error_msg='Authored report differs from native final response')
			elif 'routine' != package['risk']:
				raise ValueError('Significant risk cannot use self-review')
			groups.setdefault(entry['package'], (package, []))[1].append(entry)
		except (ValueError, OSError, KeyError, TypeError) as exc:
			diagnostics.append(str(exc))
	selected = evaluator.select_authorized_group(groups)
	if None is selected:
		detail = '; '.join(dict.fromkeys(diagnostics))
		raise ValueError('Need current answer-bound approved A.A review; significant risk requires two independent reviewers' + (': ' + detail if detail else ''))
	path, package, eligible = selected
	update_verified_claims_cache(root, package, value)
	return {'package': path, 'package_sha256': digest(inside(root, path).read_bytes()), 'response_sha256': package['response']['sha256'], 'risk': package['risk'], 'review_ids': [item['id'] for item in eligible]}
def approval_current(root, state, approval):
	return ReviewQuorumEvaluator(root, state).approval_current(approval)
def verify_entry_native_proof(root, entry, *, error_msg='Saved report differs from the actual native authored final response'):
	from .metrics import verify_native_proof
	native = json.loads(inside(root, entry['native_evidence']).read_text(encoding='utf-8'))
	observed = verify_native_proof(root, native, package=Path(entry['package']).name)
	if digest(inside(root, entry['authored_response']).read_bytes()) != observed.get('final_response_sha256'):
		raise ValueError(error_msg)
	return observed
