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
import json
import re
from pathlib import Path
from .research import inside, json_data
from .storage import create_bytes
REVIEW_SCHEMA = 2
SCOPES = ('identity', 'concerns', 'misconceptions', 'causes', 'methods', 'kb_consistency', 'response')
TASK_FLAGS = {'new_causal_analysis', 'architecture_change', 'pricing_change', 'admin_configuration', 'business_impact', 'material_analysis'}
def digest(payload):
	return hashlib.sha256(payload).hexdigest()
def _text(value):
	return isinstance(value, str) and bool(value.strip())
def load_verified_claims_cache(root) -> dict:
	path = Path(root).resolve() / 'ꘖ/data/verified-claims.json'
	if path.is_file():
		try:
			data = json.loads(path.read_text(encoding='utf-8'))
			if isinstance(data, dict) and isinstance(data.get('claims'), dict):
				return data
		except (OSError, ValueError):
			pass
	return {'version': 1, 'claims': {}}
def _claim_evidence_pairs(claim_id: str, index: dict, evidence_inputs: dict | None = None, _visited: set | None = None) -> list[tuple[str, str]]:
	visited = set() if None is _visited else _visited
	if not _text(claim_id) or claim_id in visited:
		return []
	visited.add(claim_id)
	claim = index.get(claim_id) or {}
	ev_map = evidence_inputs if isinstance(evidence_inputs, dict) else {}
	pairs: dict[str, str] = {}
	refs = list(claim.get('evidence') or []) + list(claim.get('primary_evidence') or [])
	for ref in refs:
		if not isinstance(ref, dict):
			continue
		for key in ('source', 'observation', 'manifest'):
			val = ref.get(key)
			if _text(val):
				s = val.strip()
				sha = ev_map.get(s) or (str(ref.get('source_sha256') or '') if 'source' == key else '')
				if s not in pairs or (not pairs[s] and sha):
					pairs[s] = sha
	for dep in claim.get('derived_from') or []:
		dep_id = dep.get('claim_id') if isinstance(dep, dict) else None
		if _text(dep_id) and dep_id in index:
			for s, sha in _claim_evidence_pairs(dep_id, index, ev_map, visited):
				if s not in pairs or (not pairs[s] and sha):
					pairs[s] = sha
	return sorted(pairs.items())
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
	from .claims import all_claims
	index = {c['id']: c for c in all_claims(value) if isinstance(c, dict) and _text(c.get('id'))}
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
def update_verified_claims_cache(root, package: dict, value: dict | None = None) -> dict:
	from .claims import all_claims
	root = Path(root).resolve()
	if None is value:
		try:
			value = _analysis(root)
		except (OSError, ValueError):
			value = {}
	index = {c['id']: c for c in all_claims(value) if isinstance(c, dict) and _text(c.get('id'))} if isinstance(value, dict) else {}
	ev_inputs = package.get('evidence_inputs') or {}
	cache_data = load_verified_claims_cache(root)
	claims_map = cache_data.setdefault('claims', {})
	for item in package.get('claims') or []:
		if isinstance(item, dict) and _text(item.get('claim_id')):
			ident = item['claim_id']
			claim_obj = index.get(ident) or {}
			m_hash = (package.get('merkle_delta') or {}).get('merkle_hashes', {}).get(ident) or claim_merkle_hash(item, index, ev_inputs)
			claims_map[ident] = {
				'claim_id': ident,
				'claim_sha256': item.get('claim_sha256', ''),
				'knowledge_type': item.get('knowledge_type') or claim_obj.get('knowledge_type') or '',
				'verification_status': item.get('verification_status') or claim_obj.get('verification_status') or '',
				'tier0_evidence_hashes': dict(_claim_evidence_pairs(ident, index, ev_inputs)),
				'merkle_sha256': m_hash,
				'response_sha256': (package.get('response') or {}).get('sha256', ''),
			}
	path = root / 'ꘖ/data/verified-claims.json'
	if path.parent.is_dir() or (root / 'ꘖ').is_dir():
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
	return cache_data
def build_blind_verification_predicates(manifest: list[dict], value: dict) -> list[dict]:
	from .claims import all_claims
	index = {c['id']: c for c in all_claims(value) if isinstance(c, dict) and _text(c.get('id'))}
	predicates = []
	for item in manifest:
		ident = item['claim_id']
		raw_essence = str(item.get('essence') or '')
		clean_predicate = re.sub('(?:\\s*\\(\\d{1,3}%\\)|\\s+with\\s+\\d{1,3}%\\s+(?:confidence|probability|plausibility|score)|\\s*[—–-]\\s*\\d{1,3}%)', '', raw_essence, flags=re.I).strip()
		predicates.append({
			'claim_id': ident,
			'knowledge_type': item.get('knowledge_type'),
			'atomic_predicate': clean_predicate,
			'primary_sources': _claim_evidence_sources(ident, index),
			'question': f'Does the Tier 0 primary evidence directly entail or falsify the atomic statement for {ident}: "{clean_predicate}"?',
		})
	return predicates
def _immutable(path, payload):
	path.parent.mkdir(parents=True, exist_ok=True)
	if path.exists():
		if path.read_bytes() != payload:
			raise ValueError('Immutable review artifact differs; preserve the original and create a new attempt')
	else:
		try:
			create_bytes(path, payload)
		except FileExistsError:
			if path.read_bytes() != payload:
				raise ValueError('Concurrent immutable review publication differs')
	r = path
	return r
def request_snapshot(state):
	return [{'id': item['id'], 'text': item['text']} for item in state['requests']]
def _analysis(root):
	from .analysis import analysis_issues
	from .evidence import evidence_issues
	path = Path(root) / 'ꘖ/KB/Analysis.json'
	value = json.loads(path.read_text(encoding='utf-8-sig'))
	if not isinstance(value, dict) or 3 != value.get('schema_version'):
		raise ValueError('New review and publication require Analysis schema 3; legacy files remain readable')
	if analysis_issues(value) or evidence_issues(root, value):
		raise ValueError('Resolve Analysis schema 3 and evidence diagnostics before preparing or accepting review')
	r = value
	return r
def _approved_digests(root, state, *, exclude_package=None):
	from .workflow import receipt_current, hashes, evidence_paths
	from .claims import all_claims
	result = set()
	is_finalized = state.get('stages', {}).get('finalize', {}).get('status') == 'complete'
	cur_ev_hashes = hashes(root, evidence_paths(root))
	index = None
	if is_finalized:
		try:
			val = _analysis(root)
			index = {c['id']: c for c in all_claims(val) if isinstance(c, dict) and _text(c.get('id'))}
		except (OSError, ValueError):
			index = {}
	for entry in state['reviews']:
		if entry.get('schema_version') != REVIEW_SCHEMA or 'approved' != entry.get('result'):
			continue
		if entry.get('package') == exclude_package:
			continue
		if not receipt_current(root, {'inputs': entry.get('proof', {})}):
			continue
		package = json.loads(inside(root, entry['package']).read_text(encoding='utf-8'))
		if not _findings_closed(root, entry):
			continue
		pkg_ev = package.get('evidence_inputs') or {}
		ev_exact = pkg_ev == cur_ev_hashes
		if not ev_exact and (not is_finalized):
			continue
		matching = [r for r in state['reviews'] if r.get('package') == entry['package'] and r.get('schema_version') == REVIEW_SCHEMA and ('approved' == r.get('result')) and r.get('independent') and _findings_closed(root, r) and receipt_current(root, {'inputs': r.get('proof', {})})]
		latest = _latest_for_subject(state, package)
		if latest[entry['reviewer_id']].get('id') != entry['id'] or _unhandled_verdicts(root, state, package, latest):
			continue
		matching = [r for r in matching if latest[r['reviewer_id']].get('id') == r['id']]
		has_escalation = significant_findings(root, state, package['subject_sha256']) or any(('approved' != r.get('result') for r in latest.values()))
		is_falsifier = 'falsifier' == package.get('review_mode') or any(('falsifier' == r.get('review_mode') for r in matching))
		if 'significant' == package['risk'] and not (is_falsifier and not has_escalation) and len({r['reviewer_id'] for r in matching}) < 2:
			continue
		if ev_exact:
			result.update(((c['claim_id'], c['claim_sha256']) for c in package['claims']))
		else:
			for c in package['claims']:
				cid = c['claim_id']
				c_pairs = _claim_evidence_pairs(cid, index or {}, pkg_ev)
				if all((cur_ev_hashes.get(s) == sha for s, sha in c_pairs if sha)):
					result.add((cid, c['claim_sha256']))
	return result
def classification(root, state, spec, response, value, *, exclude_package=None):
	from .claims import all_claims, claim_digest, claim_locations, standalone_numbers, grounded_numbers_for_claim
	if not isinstance(spec, dict) or spec.get('risk') not in ('routine', 'significant'):
		raise ValueError('Explicit review spec risk routine/significant is required; no default risk')
	if not _text(spec.get('basis')) or not _text(spec.get('request_scope')):
		raise ValueError('Review classification needs a substantive basis and current request_scope')
	flags = spec.get('task_flags')
	if not isinstance(flags, list) or any((not _text(x) or x not in TASK_FLAGS for x in flags)) or len(set(flags)) != len(flags):
		raise ValueError('Explicit unique task_flags list required: ' + ', '.join(sorted(TASK_FLAGS)) + ' (or [])')
	if not isinstance(spec.get('claim_ids'), list) or not spec['claim_ids'] or (not isinstance(spec.get('claims'), list)) or (not spec['claims']):
		raise ValueError('Analytical review requires nonempty claim_ids and response claims manifest')
	claim_ids = spec['claim_ids']
	if any((not _text(x) for x in claim_ids)) or len(set(claim_ids)) != len(claim_ids):
		raise ValueError('Review claim_ids must be unique existing claim IDs')
	is_finalized = state.get('stages', {}).get('finalize', {}).get('status') == 'complete'
	index = {item['id']: item for item in all_claims(value)}
	section_by_id = {claim['id']: section for _, section, claim in claim_locations(value) if isinstance(claim, dict) and _text(claim.get('id'))}
	previously_approved = _approved_digests(root, state, exclude_package=exclude_package)
	manifest, seen, reasons, required_flags = ([], set(), [], set())
	for item in spec['claims']:
		if not isinstance(item, dict) or not _text(item.get('claim_id')) or (item['claim_id'] not in index and not is_finalized):
			raise ValueError('Every response claim must identify a current Analysis claim')
		ident = item['claim_id']
		if ident in seen or not _text(item.get('response_excerpt')) or item['response_excerpt'] not in response:
			raise ValueError('Response manifest needs one exact nonempty response excerpt per claim')
		seen.add(ident)
		if ident in index:
			claim = index[ident]
			claim_section = section_by_id.get(ident)
			excerpt_nums = standalone_numbers(item['response_excerpt'])
			if excerpt_nums:
				grounded_nums = grounded_numbers_for_claim(claim, index)
				ungrounded_nums = sorted(excerpt_nums - grounded_nums)
				if ungrounded_nums:
					raise ValueError(f'Response excerpt for {ident} contains numeric figures not grounded in the claim or its primary evidence: ' + ', '.join(ungrounded_nums))
			sha = claim_digest(claim)
		else:
			essence_val = str(item.get('essence') or item['response_excerpt']).strip()
			claim = {
				'id': ident,
				'essence': essence_val,
				'materiality': item.get('materiality') or ('significant' if 'significant' == spec.get('risk') else 'routine'),
				'category': item.get('category') or 'descriptive',
				'properties': list(item.get('properties') or []),
				'knowledge_type': item.get('knowledge_type') or 'observation',
				'verification_status': item.get('verification_status') or 'verified',
				'novelty': item.get('novelty') or 'new',
			}
			claim_section = None
			sha = item.get('claim_sha256') or digest(json_data({'id': ident, 'essence': essence_val, 'response_excerpt': item['response_excerpt']}))
		novelty = item.get('novelty', claim.get('novelty'))
		if novelty not in ('new', 'restatement'):
			raise ValueError('Response claim novelty must be new or restatement')
		restatement = 'restatement' == novelty and (ident, sha) in previously_approved
		material = 'significant' == claim.get('materiality') or claim.get('impact', {}).get('severity') in ('high', 'critical')
		causal_section = claim_section in ('causes', 'misconceptions')
		significant_kind = causal_section or claim.get('category') in ('causal', 'architecture', 'pricing') or bool(set(claim.get('properties', [])) & {'causality', 'business_impact', 'admin_configuration', 'architecture_change', 'pricing_change'})
		if not restatement and (material or significant_kind):
			reasons.append(f"{ident}: new {claim.get('category')} claim ({claim.get('materiality')})")
			properties = set(claim.get('properties', []))
			if material:
				required_flags.add('material_analysis')
			if causal_section:
				required_flags.add('new_causal_analysis')
			for category, prop, flag in (('causal', 'causality', 'new_causal_analysis'), ('architecture', 'architecture_change', 'architecture_change'), ('pricing', 'pricing_change', 'pricing_change')):
				if claim.get('category') == category or prop in properties:
					required_flags.add(flag)
			required_flags.update(properties & {'admin_configuration', 'business_impact'})
		manifest.append({'claim_id': ident, 'claim_sha256': sha, 'response_excerpt': item['response_excerpt'], 'novelty': novelty, 'previously_approved_restatement': restatement, 'materiality': claim.get('materiality'), 'category': claim.get('category'), 'properties': claim.get('properties'), 'knowledge_type': claim.get('knowledge_type'), 'verification_status': claim.get('verification_status'), 'essence': claim['essence']})
	if set(claim_ids) != seen:
		raise ValueError('Classification claim_ids must equal the response manifest claim IDs')
	if not is_finalized:
		unreviewed_stage_claims = [c['id'] for s in ('causes', 'misconceptions', 'methods') for c in value.get(s) or [] if isinstance(c, dict) and _text(c.get('id')) and ((c['id'], claim_digest(c)) not in previously_approved)]
		omitted_stage_claims = sorted(set(unreviewed_stage_claims) - seen)
		if omitted_stage_claims and 'routine' == spec['risk']:
			raise ValueError('Unjustified routine risk downgrade: unreviewed causes/misconceptions/methods claims in Analysis.json cannot be omitted from the review manifest (' + ', '.join(omitted_stage_claims) + ')')
	minimum = 'significant' if reasons or flags else 'routine'
	if 'significant' == minimum and 'routine' == spec['risk']:
		raise ValueError('Unjustified routine risk downgrade: ' + '; '.join(reasons))
	if not required_flags.issubset(flags):
		raise ValueError('Task flags omit typed significant work: ' + ', '.join(sorted(required_flags - set(flags))))
	r = {'risk': spec['risk'], 'minimum_risk': minimum, 'risk_basis': spec['basis'], 'risk_reasons': reasons, 'request_scope': spec['request_scope'], 'claims': manifest, 'task_flags': flags, 'minimum_task_flags': sorted(required_flags)}
	return r
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
	if isinstance(value, dict) and value.get('red_flags') == [] and re.search('(?im)^\\s*#{1,6}\\s+Red Flags\\b', response):
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
	auto_tier0 = discover_entity_tier0_sources(root, response)
	merkle_delta = compute_claim_merkle_delta(root, classified['claims'], value, ev_inputs)
	blind_predicates = build_blind_verification_predicates(classified['claims'], value)
	extra_pkg = {
		'auto_tier0_evidence': auto_tier0,
		'merkle_delta': merkle_delta,
		'blind_verification_predicates': blind_predicates,
	}
	if isinstance(spec, dict) and spec.get('review_mode') in ('standard', 'falsifier'):
		extra_pkg['review_mode'] = spec['review_mode']
	data = {'schema_version': REVIEW_SCHEMA, 'project_root': str(root), 'job_id': state['job_id'], 'parent_id': parent_id, **classified, 'requests': requests, 'response': {'file': candidate.relative_to(root).as_posix(), 'sha256': response_sha, 'bytes': len(payload)}, 'kb_inputs': hashes(root, kb_paths(root)), 'evidence_inputs': ev_inputs, 'scope': list(SCOPES), 'knowledge_source': 'agent KB, primary evidence, current requests and exact response; no Context.md', **extra_pkg}
	data['subject_sha256'] = subject_digest(data)
	if 'routine' == data['risk'] and significant_findings(root, state, data['subject_sha256']):
		raise ValueError('A significant/critical finding on this exact answer requires a significant package and two independent A.A')
	package_bytes = json_data(data)
	path = root / 'ꘖ/KB/Evidence/Reviews' / (digest(package_bytes) + '-inputs.json')
	_immutable(path, package_bytes)
	r = {'package': path.relative_to(root).as_posix(), 'package_sha256': digest(package_bytes), **data}
	return r
def subject_digest(package):
	if 'client_text' != package.get('kind'):
		r = digest(json_data({k: package[k] for k in ('project_root', 'job_id', 'requests', 'response', 'kb_inputs', 'evidence_inputs')}))
	else:
		r = digest(json_data({k: package[k] for k in ('project_root', 'job_id', 'requests', 'target', 'kb_inputs', 'evidence_inputs')} | {'response_sha256': package['response']['sha256'], 'baseline_sha256': package['baseline']['sha256']}))
	return r
def _latest_for_subject(state, package):
	latest = {}
	for entry in state['reviews']:
		if entry.get('schema_version') == REVIEW_SCHEMA and entry.get('subject_sha256') == package['subject_sha256']:
			latest[entry['reviewer_id']] = entry
	r = latest
	return r
def significant_findings(root, state, subject):
	from .workflow import receipt_current
	for entry in state['reviews']:
		if entry.get('schema_version') != REVIEW_SCHEMA or entry.get('subject_sha256') != subject:
			continue
		if not receipt_current(root, {'inputs': entry.get('proof', {})}):
			continue
		report = json.loads(inside(root, entry['report']).read_text(encoding='utf-8'))
		if any((f.get('severity') in ('significant', 'critical') for f in report.get('findings', []))):
			return True
	return False
def _unhandled_verdicts(root, state, package, latest):
	from .workflow import receipt_current
	ordered = {entry.get('id'): index for index, entry in enumerate(state['reviews'])}
	approved = [entry for entry in latest.values() if 'approved' == entry.get('result') and entry.get('independent') and _findings_closed(root, entry) and receipt_current(root, {'inputs': entry.get('proof', {})})]
	for entry in latest.values():
		if 'approved' == entry.get('result') and _findings_closed(root, entry):
			continue
		if not any((ordered[followup['id']] > ordered[entry['id']] and entry['id'] in followup.get('addresses_reviews', []) for followup in approved)):
			return True
	return False
def read_package(root, package, *, state=None, require_current=True):
	from .workflow import load, hashes, kb_paths, evidence_paths
	from .claims import all_claims, claim_digest
	root = Path(root).resolve()
	path = inside(root, package)
	payload = path.read_bytes()
	data = json.loads(payload.decode('utf-8'))
	if isinstance(data, dict) and 'client_text' == data.get('kind'):
		from .text_review import read_package as read_text_package
		r = read_text_package(root, package, require_current=require_current)
	else:
		if not isinstance(data, dict) or data.get('schema_version') != REVIEW_SCHEMA or path.name != digest(payload) + '-inputs.json':
			raise ValueError('Immutable answer-bound review package schema 2 is required')
		state = state or load(root)
		if data.get('project_root') != str(root) or data.get('job_id') != state['job_id']:
			raise ValueError('Review package belongs to another project')
		if data.get('subject_sha256') != subject_digest(data):
			raise ValueError('Review subject digest differs from its exact answer, requests or evidence')
		candidate = inside(root, data['response']['file'])
		if not candidate.is_file() or digest(candidate.read_bytes()) != data['response']['sha256'] or candidate.stat().st_size != data['response']['bytes']:
			raise ValueError('Reviewed candidate response bytes differ or are missing')
		if require_current:
			if data.get('kb_inputs') != hashes(root, kb_paths(root)) or data.get('evidence_inputs') != hashes(root, evidence_paths(root)):
				raise ValueError('Review package does not match present KB and primary evidence')
			if data.get('requests') != request_snapshot(state):
				raise ValueError('Review package does not cover the exact current requests')
			value = _analysis(root)
			index = {c['id']: c for c in all_claims(value)}
			is_finalized = state.get('stages', {}).get('finalize', {}).get('status') == 'complete'
			if any(((c['claim_id'] not in index and not is_finalized) or (c['claim_id'] in index and c['claim_sha256'] != claim_digest(index[c['claim_id']])) for c in data['claims'])):
				raise ValueError('Reviewed response claim version changed')
			classification(root, state, {'risk': data['risk'], 'basis': data['risk_basis'], 'request_scope': data['request_scope'], 'claim_ids': [c['claim_id'] for c in data['claims']], 'claims': data['claims'], 'task_flags': data['task_flags']}, candidate.read_bytes().decode('utf-8'), value, exclude_package=package)
			if 'routine' == data['risk'] and significant_findings(root, state, data['subject_sha256']):
				raise ValueError('A significant/critical finding requires a significant package and two independent A.A')
		r = data
	return r
REPORT_CONTRACT = {'schema_version': REVIEW_SCHEMA, 'result_options': ['approved', 'needs_changes'], 'required_scope': list(SCOPES), 'claim_review_fields': ['claim_id', 'observed', 'inferred', 'method', 'alternatives', 'limits', 'falsification', 'raw_vs_criteria', 'test_alignment', 'outcome'], 'test_alignment_fields': ['target_claim', 'tested_claim', 'relationship', 'rationale', 'counterexample'], 'relationship_options': ['direct', 'proxy', 'irrelevant'], 'outcome_options': ['supported', 'qualified', 'unsupported'], 'finding_fields': ['id', 'claim_ids', 'severity', 'description', 'status'], 'severity_options': ['minor', 'significant', 'critical'], 'claim_review_required': {'fields': ['claim_id', 'observed', 'inferred', 'method', 'alternatives', 'limits', 'falsification', 'raw_vs_criteria', 'test_alignment', 'outcome'], 'outcome_options': ['supported', 'qualified', 'unsupported'], 'test_alignment_required': {'fields': ['target_claim', 'tested_claim', 'relationship', 'rationale', 'counterexample'], 'relationship_options': ['direct', 'proxy', 'irrelevant']}}, 'finding_required': {'fields': ['id', 'claim_ids', 'severity', 'description', 'status'], 'severity_options': ['minor', 'significant', 'critical'], 'status_options': ['open', 'resolved', 'rejected']}, 'falsifier_fields': ['disproved_claims'], 'disproved_claim_fields': ['claim_id', 'excerpt_from_answer', 'contradicting_tier0_source', 'verbatim_quote_from_source', 'falsification_reason']}
def input_receipt(root, package):
	import os
	from .runtime import platform_name
	from .workflow import file_hash
	data = read_package(root, package)
	reviewer = os.environ.get('CODEX_THREAD_ID') or os.environ.get('ANTIGRAVITY_CONVERSATION_ID')
	if not reviewer and 'codex' == platform_name() and os.environ.get('CODEX_HOME'):
		raise ValueError('Native Codex reviewer thread ID is unavailable')
	contract = dict(REPORT_CONTRACT)
	if 'client_text' == data.get('kind'):
		from .text_review import report_contract
		contract = report_contract()
	r = {'upwork_review_input': 1, 'review_schema_version': REVIEW_SCHEMA, 'verified': True, 'project_root': str(Path(root).resolve()), 'job_id': data['job_id'], **{k: data[k] for k in ('project_id', 'project_kind') if k in data}, 'parent_id': data['parent_id'], 'reviewer_id': reviewer, 'package': package, 'package_sha256': file_hash(inside(root, package)), 'kb_inputs': data['kb_inputs'], 'evidence_inputs': data['evidence_inputs'], 'requests': data['requests'], 'response': data['response'], 'claims': data['claims'], 'risk': data['risk'], 'report_contract': contract, **{k: data[k] for k in ('kind', 'goal', 'diff', 'operation', 'check', 'manifest', 'source_checks', 'auto_tier0_evidence', 'merkle_delta', 'blind_verification_predicates', 'review_mode') if k in data}}
	return r
def _report_object(text):
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
	r = result
	return r
def report_issues(data, package):
	from .claims import standalone_numbers
	from .source_grounding import _quote_segments_present, classify_provenance_tier, norm_quote_text
	issues = []
	if data.get('schema_version') != REVIEW_SCHEMA:
		issues.append('Review report schema_version 2 is required')
	if data.get('result') not in ('approved', 'needs_changes'):
		issues.append('Review result must be approved or needs_changes')
	required_scope = package.get('scope', list(SCOPES)) if 'client_text' == package.get('kind') else SCOPES
	if not isinstance(data.get('scope'), list) or not all((_text(x) for x in data['scope'])) or (not set(required_scope).issubset(data['scope'])):
		issues.append('Review must cover the required subject scope: ' + ', '.join(required_scope))
	expected = {c['claim_id'] for c in package['claims']}
	targets = {c['claim_id']: c['essence'] for c in package['claims']}
	package_claims = {c['claim_id']: c for c in package['claims']}
	pkg_root = Path(package['project_root']).resolve() if _text(package.get('project_root')) else None
	is_falsifier = 'falsifier' == data.get('review_mode') or ('disproved_claims' in data and 'claim_reviews' not in data)
	if is_falsifier:
		disproved = data.get('disproved_claims')
		if not isinstance(disproved, list):
			issues.append('Adversarial falsifier report requires a disproved_claims list')
		else:
			for dc in disproved:
				if not isinstance(dc, dict):
					issues.append('Each disproved_claims entry must be an object')
					continue
				cid_val = dc.get('claim_id')
				if cid_val not in expected:
					issues.append('Each disproved_claims entry must reference a valid response claim_id')
				for req_field in ('excerpt_from_answer', 'contradicting_tier0_source', 'verbatim_quote_from_source', 'falsification_reason'):
					if not _text(dc.get(req_field)):
						issues.append(f"disproved_claims[{cid_val or '?'}]: {req_field} is required")
				src_str = dc.get('contradicting_tier0_source')
				quote_str = dc.get('verbatim_quote_from_source')
				if _text(src_str):
					src_cand = Path(src_str)
					if None is not pkg_root and not src_cand.is_absolute():
						src_cand = (pkg_root / src_cand).resolve()
					if 'tier_0' != classify_provenance_tier(src_cand, pkg_root):
						issues.append(f"disproved_claims[{cid_val or '?'}]: contradicting_tier0_source ({src_str}) must be a Tier 0 primary source")
					elif src_cand.is_file() and _text(quote_str):
						try:
							raw_src = src_cand.read_text(encoding='utf-8', errors='replace')
							if not _quote_segments_present(quote_str, norm_quote_text(raw_src), 8):
								issues.append(f"disproved_claims[{cid_val or '?'}]: verbatim_quote_from_source is absent from Tier 0 source {src_str}")
						except OSError:
							pass
			if disproved and 'approved' == data.get('result'):
				issues.append('Adversarial falsifier report with non-empty disproved_claims requires needs_changes')
			if not disproved and 'needs_changes' == data.get('result') and not data.get('findings'):
				issues.append('Adversarial falsifier needs_changes verdict requires at least one disproved_claims entry or open finding')
	else:
		covered = set()
		if not isinstance(data.get('claim_reviews'), list):
			issues.append('Per-claim review coverage is required')
		else:
			for item in data['claim_reviews']:
				if not isinstance(item, dict):
					issues.append('Claim review must be an object')
					continue
				ident = item.get('claim_id')
				if not _text(ident):
					issues.append('Claim review needs a string claim_id')
					continue
				if ident not in expected or ident in covered:
					issues.append('Claim review must cover each response claim exactly once')
				covered.add(ident)
				for field in ('observed', 'inferred', 'method', 'alternatives', 'limits', 'falsification', 'raw_vs_criteria'):
					if not _text(item.get(field)):
						issues.append(f'{ident}: review {field} must explain the evidence assessment')
				alignment = item.get('test_alignment')
				if not isinstance(alignment, dict) or alignment.get('target_claim') != targets.get(ident) or any((not _text(alignment.get(k)) for k in ('tested_claim', 'rationale', 'counterexample'))) or (alignment.get('relationship') not in ('direct', 'proxy', 'irrelevant')):
					issues.append(f'{ident}: test_alignment must bind the exact claim, actual tested statement, relationship, rationale and a concrete counterexample')
				elif 'proxy' == alignment['relationship'] and 'supported' == item.get('outcome'):
					issues.append(f'{ident}: a proxy test cannot support the broader target; qualify the claim and show the limitation in the response')
				elif 'irrelevant' == alignment['relationship'] and 'unsupported' != item.get('outcome'):
					issues.append(f'{ident}: an irrelevant test must leave the target unsupported')
				if item.get('outcome') not in ('supported', 'qualified', 'unsupported'):
					issues.append(f'{ident}: unsupported review outcome')
				if 'unsupported' == item.get('outcome') and 'approved' == data.get('result'):
					issues.append(f'{ident}: an unsupported claim requires needs_changes')
				if 'qualified' == item.get('outcome'):
					excerpt = item.get('response_qualification')
					if not _text(excerpt):
						issues.append(f'{ident}: qualified claim needs an exact response_qualification excerpt')
				if ident in package_claims and 'supported' == item.get('outcome') and not item.get('preflight_numeric_grounded'):
					pkg_claim = package_claims[ident]
					claim_nums = standalone_numbers(str(pkg_claim.get('essence', '')) + '\n' + str(pkg_claim.get('response_excerpt', '')))
					if claim_nums:
						obs_corpus = str(item.get('observed', '')) + '\n' + str((alignment or {}).get('tested_claim', ''))
						obs_nums = {t.replace(',', '.') for t in re.findall('\\d+(?:[.,]\\d+)*', obs_corpus)}
						for token in list(obs_nums):
							obs_nums.update(token.split('.'))
						missing_nums = sorted(claim_nums - obs_nums)
						if missing_nums:
							issues.append(f'{ident}: claim/response numeric figures {missing_nums} are not confirmed in reviewer observed/tested_claim')
			merkle_unverified = set((package.get('merkle_delta') or {}).get('unverified_claim_ids') or [])
			if covered != expected and not (data.get('use_merkle_delta') and covered == merkle_unverified):
				issues.append('Every response claim requires an authored evidence assessment')
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
			if not _text(ident):
				issues.append('Findings need string IDs')
				continue
			if ident in seen:
				issues.append('Findings need unique IDs')
			seen.add(ident)
			if finding.get('status') not in ('open', 'resolved', 'rejected'):
				issues.append('Finding status must be open, resolved or rejected')
			if finding.get('severity') not in ('minor', 'significant', 'critical') or not _text(finding.get('description')):
				issues.append('Finding needs severity and description')
			if finding.get('severity') in ('significant', 'critical') and 'approved' == data.get('result') and ('routine' == package['risk']):
				issues.append('A significant/critical finding cannot approve a routine package; prepare significant review')
			if not isinstance(finding.get('claim_ids'), list) or any((c not in expected for c in finding['claim_ids'])):
				issues.append('Finding claim_ids must refer to response manifest claims')
			if finding.get('status') in ('resolved', 'rejected') and (not _text(finding.get('disposition')) or not finding.get('evidence')):
				issues.append('Closed finding needs an authored disposition and evidence')
	r = issues
	return r
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
		if _report_object(final_response) != data:
			raise ValueError('Submitted report differs from the actual native reviewer verdict')
		raw_payload = final_response.encode('utf-8')
		proof_paths.append(native_evidence)
	r = (independent, proof_paths, native, raw_payload)
	return r
# 2026-10-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
# https://github.com/dmitry-ai/harness/issues/12
def record(root, report, *, parent_id, reviewer_id, role='AA', native_evidence=None, risk=None):
	from .workflow import hashes, update, now, file_hash
	root = Path(root).resolve()
	if 'AA' != role or not _text(parent_id) or (not _text(reviewer_id)):
		raise ValueError('Observed A.A parent/reviewer IDs are required')
	source_payload = report if isinstance(report, bytes) else inside(root, report).read_bytes()
	data = _report_object(source_payload.decode('utf-8-sig'))
	package_path = data.get('package')
	if not _text(package_path):
		raise ValueError('Review report must identify its immutable package')
	package = read_package(root, package_path)
	package_sha = file_hash(inside(root, package_path))
	if data.get('package_sha256') != package_sha or package.get('parent_id') != parent_id:
		raise ValueError('Reviewer package hash/parent differs')
	if None is not risk and risk != package['risk']:
		raise ValueError('Risk is fixed in the reviewed package; record-review cannot change it')
	issues = report_issues(data, package)
	candidate = inside(root, package['response']['file']).read_text(encoding='utf-8')
	for item in data.get('claim_reviews', []):
		if isinstance(item, dict) and 'qualified' == item.get('outcome') and (item.get('response_qualification', '') not in candidate):
			issues.append('Claim qualification must occur verbatim in the exact response')
	if issues:
		raise ValueError('\n'.join(issues))
	independent, proof_paths, native, raw_payload = authenticate_report(root, package, package_path, data, source_payload, parent_id=parent_id, reviewer_id=reviewer_id, native_evidence=native_evidence)
	report_payload = json_data(data)
	review_id = digest((package_sha + '\x00' + reviewer_id + '\x00' + digest(raw_payload)).encode())
	folder = root / 'ꘖ/KB/Evidence/Reviews' / package_sha
	safe_reviewer = hashlib.sha256(reviewer_id.encode()).hexdigest()[:16]
	target = _immutable(folder / f'{safe_reviewer}-{review_id}-report.json', report_payload)
	original = _immutable(folder / f'{safe_reviewer}-{review_id}-authored.txt', raw_payload)
	report_path = target.relative_to(root).as_posix()
	proof_paths += [report_path, original.relative_to(root).as_posix()]
	for finding in data['findings']:
		if finding.get('status') in ('resolved', 'rejected'):
			evidence = finding['evidence'] if isinstance(finding['evidence'], list) else [finding['evidence']]
			proof_paths += [inside(root, e).relative_to(root).as_posix() for e in evidence]
	addresses_reviews = data.get('addresses_reviews', [])
	if not isinstance(addresses_reviews, list):
		raise ValueError('addresses_reviews must be an authored list of previous verdict resolutions')
	addressed_ids = []
	if addresses_reviews:
		from .workflow import load
		previous = {r.get('id'): r for r in load(root)['reviews']}
		if not independent or 'approved' != data['result']:
			raise ValueError('Only a new independent authored approval can address another reviewer verdict')
		for resolution in addresses_reviews:
			if not isinstance(resolution, dict) or not _text(resolution.get('review_id')):
				raise ValueError('Each addressed verdict requires its review_id')
			prior = previous.get(resolution['review_id'])
			if not prior or prior.get('subject_sha256') != package['subject_sha256'] or (not _text(resolution.get('basis'))) or (not isinstance(resolution.get('evidence'), list)) or (not resolution['evidence']):
				raise ValueError('Authored review resolution needs same-subject prior verdict, basis and saved evidence')
			proof_paths += [inside(root, e).relative_to(root).as_posix() for e in resolution['evidence']]
			addressed_ids.append(resolution['review_id'])
		if len(set(addressed_ids)) != len(addressed_ids):
			raise ValueError('Duplicate addressed review verdict')
	report_mode = 'falsifier' if ('falsifier' == data.get('review_mode') or ('disproved_claims' in data and 'claim_reviews' not in data)) else package.get('review_mode', 'standard')
	def change(state):
		read_package(root, package_path, state=state)
		if any((r.get('id') == review_id for r in state['reviews'])):
			return
		state['reviews'].append({'schema_version': REVIEW_SCHEMA, 'id': review_id, 'parent_id': parent_id, 'reviewer_id': reviewer_id, 'role': role, 'risk': package['risk'], 'review_mode': report_mode, 'package': package_path, 'package_sha256': package_sha, 'result': data['result'], 'subject_sha256': package['subject_sha256'], 'report': report_path, 'authored_response': original.relative_to(root).as_posix(), 'proof': hashes(root, proof_paths), 'independent': independent, 'kb_inputs': package['kb_inputs'], 'evidence_inputs': package['evidence_inputs'], 'response_sha256': package['response']['sha256'], 'requests': package['requests'], 'native_evidence': native_evidence, 'dispositions': [], 'addresses_reviews': addressed_ids, 'model_verification': native.get('model_verification', 'unverified'), 'time': now()})
	return update(root, {'action': 'review', 'reviewer_id': reviewer_id, 'result': data['result'], 'review_id': review_id}, change)
def _findings_closed(root, entry):
	from .workflow import receipt_current
	data = json.loads(inside(root, entry['report']).read_text(encoding='utf-8'))
	statuses = {f['id']: f.get('status') for f in data['findings']}
	for disposition in entry.get('dispositions', []):
		if not receipt_current(root, {'inputs': disposition['proof']}):
			return False
		saved = json.loads(inside(root, disposition['file']).read_text(encoding='utf-8'))
		statuses[saved['finding_id']] = saved['status']
	return all((status in ('resolved', 'rejected') for status in statuses.values()))
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
	if not entry or entry.get('schema_version') != REVIEW_SCHEMA or entry['parent_id'] != parent_id:
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
	from .workflow import receipt_current, questions_current, check_project
	from .metrics import verify_native_proof
	value = _analysis(root)
	is_finalized = state.get('stages', {}).get('finalize', {}).get('status') == 'complete'
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
			elif finalize_time and q_time and q_time > finalize_time:
				relevant_qs[qid] = q
		if relevant_qs and not questions_current(root, {**state, 'questions': relevant_qs}):
			raise ValueError('Complete current research questions/gaps before publication')
	response_sha = digest(response.encode('utf-8')) if None is not response else None
	groups, diagnostics = ({}, [])
	for entry in state['reviews']:
		if entry.get('schema_version') != REVIEW_SCHEMA:
			continue
		if package_path and entry.get('package') != package_path:
			continue
		if response_sha and entry.get('response_sha256') != response_sha:
			continue
		try:
			package = read_package(root, entry['package'], state=state)
			if not receipt_current(root, {'inputs': entry['proof']}):
				raise ValueError('Review proof changed')
			if 'approved' != entry['result'] or not _findings_closed(root, entry):
				raise ValueError('Reviewer needs changes or has open findings; parent disposition cannot replace an approval')
			if entry.get('independent'):
				native = json.loads(inside(root, entry['native_evidence']).read_text(encoding='utf-8'))
				observed = verify_native_proof(root, native, package=Path(entry['package']).name)
				original = inside(root, entry['authored_response']).read_bytes()
				if digest(original) != observed.get('final_response_sha256'):
					raise ValueError('Authored report differs from native final response')
			elif 'routine' != package['risk']:
				raise ValueError('Significant risk cannot use self-review')
			groups.setdefault(entry['package'], (package, []))[1].append(entry)
		except (ValueError, OSError, KeyError, TypeError) as exc:
			diagnostics.append(str(exc))
	for path, (package, reviews) in reversed(list(groups.items())):
		eligible = [r for r in reviews if 'routine' == package['risk'] or r.get('independent')]
		latest = _latest_for_subject(state, package)
		if _unhandled_verdicts(root, state, package, latest):
			continue
		eligible = [r for r in eligible if latest[r['reviewer_id']]['id'] == r['id']]
		has_escalation = significant_findings(root, state, package['subject_sha256']) or any(('approved' != r.get('result') for r in latest.values()))
		merkle_delta = package.get('merkle_delta') or {}
		all_merkle_cached = bool(merkle_delta.get('cached_claim_ids')) and not bool(merkle_delta.get('unverified_claim_ids'))
		is_falsifier_or_cached = ('falsifier' == package.get('review_mode')) or any(('falsifier' == r.get('review_mode') for r in eligible)) or all_merkle_cached
		required = 1 if ('routine' == package['risk'] or (is_falsifier_or_cached and not has_escalation)) else 2
		if len({r['reviewer_id'] for r in eligible}) >= required:
			update_verified_claims_cache(root, package, value)
			return {'package': path, 'package_sha256': digest(inside(root, path).read_bytes()), 'response_sha256': package['response']['sha256'], 'risk': package['risk'], 'review_ids': [r['id'] for r in eligible]}
	detail = '; '.join(dict.fromkeys(diagnostics))
	raise ValueError('Need current answer-bound approved A.A review; significant risk requires two independent reviewers' + (': ' + detail if detail else ''))
def approval_current(root, state, approval):
	from .workflow import receipt_current
	if not isinstance(approval, dict):
		return False
	try:
		package = read_package(root, approval['package'], state=state)
		if digest(inside(root, approval['package']).read_bytes()) != approval['package_sha256']:
			return False
		approved = {r['id']: r for r in state['reviews'] if r.get('schema_version') == REVIEW_SCHEMA}
		selected = [approved[ident] for ident in approval['review_ids']]
		latest = _latest_for_subject(state, package)
		if _unhandled_verdicts(root, state, package, latest):
			return False
		if any(('approved' != r.get('result') or latest[r['reviewer_id']].get('id') != r['id'] or (not _findings_closed(root, r)) or (not receipt_current(root, {'inputs': r['proof']})) for r in selected)):
			return False
		eligible = [r for r in selected if 'routine' == package['risk'] or r.get('independent')]
		has_escalation = significant_findings(root, state, package['subject_sha256']) or any(('approved' != r.get('result') for r in latest.values()))
		merkle_delta = package.get('merkle_delta') or {}
		all_merkle_cached = bool(merkle_delta.get('cached_claim_ids')) and not bool(merkle_delta.get('unverified_claim_ids'))
		is_falsifier_or_cached = ('falsifier' == package.get('review_mode')) or any(('falsifier' == r.get('review_mode') for r in eligible)) or all_merkle_cached
		required = 1 if ('routine' == package['risk'] or (is_falsifier_or_cached and not has_escalation)) else 2
		return len({r['reviewer_id'] for r in eligible}) >= required
	except (ValueError, OSError, KeyError, TypeError):
		return False
