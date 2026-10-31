# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
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
PROPERTIES = {'content', 'markup', 'dom', 'interaction', 'currency_transition', 'ip_country', 'admin_configuration', 'serp', 'platform_capability', 'calculation', 'causality', 'business_impact', 'architecture_change', 'pricing_change'}
HASH = re.compile('^[a-f0-9]{64}$')
ID = re.compile('^[A-Z][A-Z0-9-]*$')
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
	return {claim['id']: claim for claim in all_claims(value) if isinstance(claim.get('id'), str)}
# 2026-10-22 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Ban conditional conjunctions in limited claim qualifications and isolate closed admin access from proven public storefront facts":
# https://github.com/dmitry-ai/harness/issues/15
def claim_digest(claim):
	return hashlib.sha256(json.dumps(claim, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
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
def grounded_numbers_for_claim(claim, index=None, visited=None):
	if not isinstance(claim, dict):
		r = set()
	else:
		visited = set() if None is visited else visited
		ident = claim.get('id')
		if ident in visited:
			r = set()
		else:
			if isinstance(ident, str):
				visited = visited | {ident}
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
			corpus = '\n'.join(texts)
			numbers = {t.replace(',', '.') for t in re.findall('\\d+(?:[.,]\\d+)*', corpus)}
			for token in list(numbers):
				numbers.update(token.split('.'))
			if isinstance(index, dict):
				for dep in _dependencies(claim):
					dep_id = dep.get('claim_id') if isinstance(dep, dict) else None
					if dep_id and dep_id in index:
						numbers.update(grounded_numbers_for_claim(index[dep_id], index, visited))
				for addr_id in claim.get('addresses', []) if isinstance(claim.get('addresses'), list) else []:
					if isinstance(addr_id, str) and addr_id in index:
						numbers.update(grounded_numbers_for_claim(index[addr_id], index, visited))
			r = numbers
	return r
def contract_issues(value):
	if not isinstance(value, dict) or 3 != value.get('schema_version'):
		return []
	issues, seen, evidence_ids = ([], {}, set())
	def add(code, field, message, claim=None):
		issues.append(problem(code, field, message, claim_id=claim.get('id') if claim else None))
	if not isinstance(value.get('facts'), list):
		add('facts.list', '/facts', 'Version 3 requires first-class facts, including an explicit empty list')
	else:
		for number, item in enumerate(value['facts']):
			if not isinstance(item, dict):
				add('claim.object', f'/facts/{number}', 'Each fact must be an object')
	for field, section, claim in claim_locations(value):
		ident = claim.get('id')
		if not _text(ident) or not ID.fullmatch(ident) or ident in seen:
			add('claim.id', field + '/id', 'Invalid or duplicate claim ID across facts and all five stages', claim)
		else:
			seen[ident] = (field, section, claim)
		for key in ('essence', 'assessment_basis'):
			if not _text(claim.get(key)):
				add('claim.required', field + '/' + key, key + ' is required', claim)
		if not _enum(claim.get('knowledge_type'), KINDS):
			add('claim.knowledge_type', field + '/knowledge_type', 'Choose an explicit observation, client_report, hypothesis, recommendation or calculation', claim)
		if not _enum(claim.get('verification_status'), STATUSES):
			add('claim.verification_status', field + '/verification_status', 'Choose verified, limited, unverified, unavailable or stale', claim)
		if 'facts' == section and (not _enum(claim.get('knowledge_type'), {'observation', 'client_report', 'calculation'})):
			add('fact.knowledge_type', field, 'A fact is an observation, attributed client report or calculation; hypotheses belong to the five stages', claim)
		if 'methods' == section and 'recommendation' != claim.get('knowledge_type'):
			add('method.knowledge_type', field, 'Solution methods are recommendations with conditions and a validation plan', claim)
		if 'hypothesis' == claim.get('knowledge_type') and 'verified' == claim.get('verification_status'):
			add('hypothesis.status', field, 'An unproved explanation remains a hypothesis; a score cannot make it verified', claim)
		for key, allowed in (('materiality', {'routine', 'significant'}), ('novelty', {'new', 'restatement'}), ('category', {'descriptive', 'causal', 'architecture', 'pricing', 'interaction'})):
			if not _enum(claim.get(key), allowed):
				add('claim.' + key, field + '/' + key, 'Choose one of: ' + ', '.join(sorted(allowed)), claim)
		scope = claim.get('scope')
		if not isinstance(scope, dict) or not _text(scope.get('description')) or (not _strings(scope.get('sample'))) or (not _strings(scope.get('limitations'))):
			add('claim.scope', field + '/scope', 'Scope needs description, sampled objects and explicit limitations lists', claim)
		elif 'verified' == claim.get('verification_status') and (not scope['sample']):
			add('claim.scope', field + '/scope/sample', 'A verified claim must identify the objects actually examined', claim)
		properties = claim.get('properties')
		if not _strings(properties, nonempty=True) or any((x not in PROPERTIES for x in properties)):
			add('claim.properties', field + '/properties', 'List supported property types: ' + ', '.join(sorted(PROPERTIES)), claim)
		elif {'architecture_change', 'pricing_change'}.intersection(properties) and 'recommendation' != claim.get('knowledge_type'):
			add('claim.action_property', field + '/properties', 'Architecture/pricing changes are conditional recommendations', claim)
		checks = claim.get('missing_checks')
		if not _strings(checks):
			add('claim.missing_checks', field + '/missing_checks', 'List missing checks explicitly, including an empty list when resolved', claim)
		elif _enum(claim.get('verification_status'), {'limited', 'unverified', 'unavailable', 'stale'}) and (not checks):
			add('claim.missing_checks', field + '/missing_checks', 'An incomplete or stale claim needs actionable missing checks', claim)
		elif 'verified' == claim.get('verification_status') and checks:
			add('claim.verified_gap', field, 'A claim with unresolved required checks cannot be verified', claim)
		dependencies = claim.get('derived_from')
		if not isinstance(dependencies, list):
			add('claim.dependencies', field + '/derived_from', 'Record dependency IDs with exact claim sha256 revisions', claim)
		else:
			used = set()
			for number, dep in enumerate(dependencies):
				if not isinstance(dep, dict) or not _text(dep.get('claim_id')) or (not _hash(dep.get('sha256'))):
					add('claim.dependency', field + f'/derived_from/{number}', 'A dependency needs claim_id and canonical claim sha256', claim)
				elif dep['claim_id'] in used:
					add('claim.dependency', field + f'/derived_from/{number}', 'Duplicate dependency', claim)
				else:
					used.add(dep['claim_id'])
		evidence = claim.get('evidence')
		if not isinstance(evidence, list):
			add('claim.evidence', field + '/evidence', 'Record a list of primary references; KB prose is not primary evidence', claim)
		else:
			for number, ref in enumerate(evidence):
				ef = field + f'/evidence/{number}'
				if not isinstance(ref, dict):
					add('primary.reference', ef, 'A primary reference must be an object', claim)
					continue
				if not _text(ref.get('id')) or ref['id'] in evidence_ids:
					add('primary.id', ef + '/id', 'Evidence IDs must be nonempty and unique in this analysis', claim)
				else:
					evidence_ids.add(ref['id'])
				if not _enum(ref.get('kind'), {'observation', 'intake', 'attachment', 'experiment'}):
					add('primary.kind', ef + '/kind', 'Primary evidence needs observation, intake, attachment or experiment provenance', claim)
				if not _text(ref.get('source')) or not _text(ref.get('quote')) or (not _hash(ref.get('source_sha256'))):
					add('primary.source', ef, 'Supply exact source, quote and source_sha256', claim)
				locator = ref.get('locator')
				if not isinstance(locator, dict) or not _enum(locator.get('type'), {'text', 'json_pointer', 'anchor', 'lines'}) or (not _text(locator.get('value'))):
					add('primary.locator', ef + '/locator', 'Use an exact text, JSON pointer, anchor or line-range locator', claim)
				if 'documentation' in ref and type(ref['documentation']) is not bool:
					add('documentation.type', ef + '/documentation', 'documentation must be an explicit boolean', claim)
				if ref.get('documentation') and _text(ref.get('source')) and (not urldefrag(ref['source'])[1]):
					exception = ref.get('anchor_exception')
					if isinstance(locator, dict) and 'anchor' == locator.get('type'):
						add('documentation.locator', ef + '/source', 'Put the available documentation section anchor in the source URL itself', claim)
					elif not isinstance(exception, dict) or not all((_text(exception.get(k)) for k in ('section', 'observation'))):
						add('documentation.locator', ef + '/anchor_exception', 'Documentation needs its section anchor URL or a named section and saved no-anchor observation', claim)
				if 'observation' == ref.get('kind') and (not _text(ref.get('observation'))):
					add('primary.observation', ef, 'Observation metadata reference is required', claim)
				if 'experiment' == ref.get('kind') and (not _text(ref.get('experiment')) or not _text(ref.get('artifact_id'))):
					add('primary.experiment', ef, 'Experiment and exact artifact_id are required', claim)
				if _enum(ref.get('kind'), {'intake', 'attachment'}) and (not _text(ref.get('manifest'))):
					add('primary.manifest', ef, 'Bind intake/attachment bytes to the saved project snapshot or intake manifest', claim)
		if 'unavailable' != claim.get('verification_status') and (not evidence) and (not dependencies):
			add('claim.unsourced', field, 'A claim must trace to primary evidence through evidence or versioned dependencies', claim)
		if 'verified' == claim.get('verification_status') and _enum(claim.get('knowledge_type'), {'observation', 'client_report'}) and (not claim.get('calculation')) and (not _dependencies(claim)) and isinstance(evidence, list) and evidence:
			essence_nums = standalone_numbers(claim.get('essence', ''))
			ev_corpus = '\n'.join((str(ref.get('quote', '')) + '\n' + str((ref.get('locator') or {}).get('value', '')) for ref in evidence if isinstance(ref, dict)))
			ev_nums = {t.replace(',', '.') for t in re.findall('\\d+(?:[.,]\\d+)*', ev_corpus)}
			for token in list(ev_nums):
				ev_nums.update(token.split('.'))
			ungrounded = sorted(essence_nums - ev_nums)
			if ungrounded:
				add('claim.ungrounded_number', field + '/essence', 'Verified observation/client_report essence contains numeric figures absent from its primary evidence quotes: ' + ', '.join(ungrounded), claim)
		if 'causal' == claim.get('category') or section in ('causes', 'misconceptions'):
			if not _strings(claim.get('alternative_explanations'), nonempty=True) or not _text(claim.get('discriminating_check')):
				add('claim.causal', field, 'Causal and misconception explanations need plausible alternatives and a check that distinguishes them', claim)
		if 'hypothesis' == claim.get('knowledge_type') and 'verified' != claim.get('verification_status') and (section in ('causes', 'misconceptions') or 'causal' == claim.get('category') or bool(claim.get('alternative_explanations'))) and isinstance(claim.get('against'), list) and (not claim['against']) and isinstance(claim.get('probability_percent'), int) and (claim['probability_percent'] > 75):
			add('claim.counterevidence', field + '/probability_percent', 'An unverified or limited hypothesis with competing alternatives and no against arguments cannot exceed 75% probability; include counter-arguments from plausible alternatives or lower the probability', claim)
		if 'recommendation' == claim.get('knowledge_type'):
			if not _strings(claim.get('applicability'), nonempty=True) or not _text(claim.get('validation')):
				add('claim.recommendation', field, 'Recommendations need applicability conditions and an outcome validation plan', claim)
		impact = claim.get('impact')
		if not isinstance(impact, dict) or not _enum(impact.get('severity'), {'unknown', 'low', 'medium', 'high', 'critical'}) or (not _text(impact.get('basis'))) or (not _strings(impact.get('evidence_claim_ids'))):
			add('claim.impact', field + '/impact', 'Impact needs severity, substantive basis and evidence_claim_ids (empty if unknown)', claim)
		elif impact['severity'] in {'high', 'critical'} and (not impact['evidence_claim_ids']):
			add('claim.impact_evidence', field + '/impact', 'High/critical impact needs versioned evidence claims, not only an adjective', claim)
		calculation = claim.get('calculation')
		if 'calculation' == claim.get('knowledge_type') or 'calculation' in (properties if isinstance(properties, list) else []):
			issues.extend(_calculation_structure(calculation, field + '/calculation', claim))
		for_evidence_ids = {arg.get('evidence_id') for arg in (claim.get('for') if isinstance(claim.get('for'), list) else []) if isinstance(arg, dict) and _text(arg.get('evidence_id'))}
		for side in ('for', 'against'):
			for number, arg in enumerate(claim.get(side, []) if isinstance(claim.get(side), list) else []):
				if not isinstance(arg, dict):
					continue
				dep_ids = {x.get('claim_id') for x in _dependencies(claim) if isinstance(x, dict) and _text(x.get('claim_id'))}
				own_evidence = {x.get('id') for x in (evidence if isinstance(evidence, list) else []) if isinstance(x, dict) and _text(x.get('id'))}
				if arg.get('claim_id'):
					if not _text(arg['claim_id']) or arg['claim_id'] not in dep_ids:
						add('argument.dependency', field + f'/{side}/{number}', 'A claim argument must name a versioned derived_from dependency', claim)
				elif not _text(arg.get('evidence_id')) or arg.get('evidence_id') not in own_evidence:
					add('argument.primary', field + f'/{side}/{number}', 'Direct arguments must identify their own primary evidence_id, or use a versioned claim_id', claim)
				elif 'against' == side and arg.get('evidence_id') in for_evidence_ids:
					add('argument.contradictory_reuse', field + f'/against/{number}', 'An against argument cannot reuse the exact same evidence_id as a for argument on the same claim', claim)
				if (arg.get('claim_id') or arg.get('evidence_id')) and any((k in arg for k in ('source', 'source_id', 'quote', 'observation'))):
					add('argument.competing_reference', field + f'/{side}/{number}', 'Resolve the referenced claim/evidence instead of supplying competing source prose', claim)
	for ident, (field, section, claim) in seen.items():
		dep_ids = set()
		for dep in _dependencies(claim):
			if not isinstance(dep, dict) or not _text(dep.get('claim_id')):
				continue
			dep_ids.add(dep['claim_id'])
			target = seen.get(dep['claim_id'])
			if None is target:
				add('claim.reference', field + '/derived_from', 'Unknown dependency: ' + dep['claim_id'], claim)
			else:
				try:
					target_hash = claim_digest(target[2])
				except (TypeError, ValueError):
					target_hash = None
				if dep.get('sha256') != target_hash:
					add('claim.stale_dependency', field + '/derived_from', 'Dependency changed; reassess the dependent claim and record its new revision', claim)
				elif 'stale' == target[2].get('verification_status') and 'stale' != claim.get('verification_status'):
					add('claim.stale_dependency', field + '/derived_from', 'A dependent claim must be reassessed after a stale premise', claim)
		if 'hypothesis' == claim.get('knowledge_type') and 'verified' != claim.get('verification_status') and (section in ('causes', 'misconceptions') or 'causal' == claim.get('category')) and isinstance(claim.get('against'), list) and claim['against'] and isinstance(claim.get('probability_percent'), int) and (claim['probability_percent'] > 75):
			own_ev_kind = {ref.get('id'): ref.get('kind') for ref in (claim.get('evidence') if isinstance(claim.get('evidence'), list) else []) if isinstance(ref, dict) and _text(ref.get('id'))}
			for_ev_ids = {arg.get('evidence_id') for arg in (claim.get('for') if isinstance(claim.get('for'), list) else []) if isinstance(arg, dict) and _text(arg.get('evidence_id'))}
			for_claim_ids = {arg.get('claim_id') for arg in (claim.get('for') if isinstance(claim.get('for'), list) else []) if isinstance(arg, dict) and _text(arg.get('claim_id'))}
			has_counter_obs = False
			for arg in claim['against']:
				if not isinstance(arg, dict):
					continue
				ev_id = arg.get('evidence_id')
				c_id = arg.get('claim_id')
				if _text(ev_id) and ev_id not in for_ev_ids and (own_ev_kind.get(ev_id) in {'observation', 'experiment'}):
					has_counter_obs = True
					break
				if _text(c_id) and c_id not in for_claim_ids and (c_id in seen):
					target_claim = seen[c_id][2]
					if target_claim.get('knowledge_type') in {'observation', 'calculation'}:
						has_counter_obs = True
						break
			if not has_counter_obs:
				add('claim.counterevidence', field + '/probability_percent', 'An unverified causal or misconception hypothesis above 75% requires genuine observation/experiment counter-evidence in against (citing only client intake or reusing for-premises does not lift the 75% cap)', claim)
		impact = claim.get('impact', {})
		for ref in impact.get('evidence_claim_ids', []) if isinstance(impact, dict) and isinstance(impact.get('evidence_claim_ids'), list) else []:
			if not _text(ref) or ref not in dep_ids:
				add('claim.impact_reference', field + '/impact', 'Impact evidence must be a versioned derived_from dependency: ' + str(ref), claim)
	visited, active = (set(), set())
	def visit(ident):
		if ident in active:
			add('claim.cycle', seen[ident][0] + '/derived_from', 'Claim dependencies contain a cycle', seen[ident][2])
			return
		if ident in visited or ident not in seen:
			return
		active.add(ident)
		for dep in _dependencies(seen[ident][2]):
			if isinstance(dep, dict) and _text(dep.get('claim_id')):
				visit(dep['claim_id'])
		active.remove(ident)
		visited.add(ident)
	for ident in seen:
		visit(ident)
	return issues
def _calculation_structure(value, field, claim):
	message = None
	if not isinstance(value, dict) or 'percent_change' != value.get('operation') or '(new - old) / old * 100' != value.get('formula'):
		message = 'Supported calculation is percent_change with formula (new - old) / old * 100'
	elif type(value.get('rounding_places')) is not int or not 0 <= value['rounding_places'] <= 12 or 'ROUND_HALF_UP' != value.get('rounding'):
		message = 'Choose explicit ROUND_HALF_UP and 0..12 decimal places'
	elif not isinstance(value.get('operands'), dict) or set(value['operands']) != {'old', 'new'}:
		message = 'Supply old/new operands with exact decimal value, unit, claim_id and evidence_id'
	elif 'percent' != value.get('result_unit'):
		message = 'Percentage change requires explicit result_unit percent'
	else:
		for operand in value['operands'].values():
			if not isinstance(operand, dict) or not all((_text(operand.get(k)) for k in ('value', 'unit', 'claim_id', 'evidence_id'))):
				message = 'Each operand needs decimal string value, explicit unit, claim_id and evidence_id'
				break
			if operand['unit'] != operand['unit'].strip():
				message = 'Operand units must be canonical strings without surrounding whitespace'
				break
		if None is message and value['operands']['old']['unit'] != value['operands']['new']['unit']:
			message = 'Percent change requires matching operand units; perform and source any conversion as a separate claim first'
		if not _text(value.get('result')):
			message = 'Calculation result must be an explicit decimal string'
	r = [problem('calculation.contract', field, message, claim_id=claim.get('id'))] if message else []
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
	from .evidence import saved_source, contains_quote
	locator = ref['locator']
	saved = saved_source(root, _with_locator(ref['source'], locator), observation)
	actual_hash = saved.get('sha256') or saved.get('meta', {}).get('body_sha256')
	if actual_hash != ref['source_sha256']:
		raise ValueError('Primary source bytes changed from source_sha256')
	if 'html' != saved['kind']:
		text = saved['text']
		if ref.get('documentation') and (not saved.get('fragment')):
			raise ValueError('No-anchor documentation exception requires a verifiable saved HTML section')
	else:
		data, fragment = (saved['data'], saved.get('fragment'))
		if data.get('browser_check_required') or re.search('(?i)verify you are human|checking your browser|__LS_SEQ_LOADER__', data['text'] + saved['raw'][:8000]):
			raise ValueError('A challenge page cannot establish the intended page content')
		if fragment:
			if fragment not in data['anchors'] or fragment in data.get('ambiguous_anchors', []):
				raise ValueError('Primary anchor is absent or ambiguous')
			scopes = [h['content'] for h in data['sections'] if h.get('anchor') == fragment] or data['anchor_content'].get(fragment, [])
			if not scopes or not any((contains_quote(text, ref['quote'], ref.get('quote_match', 'exact')) for text in scopes)):
				raise ValueError('Quote does not belong to the primary anchor')
			text = '\n'.join(scopes)
		elif not ref.get('documentation'):
			text = data['text'] + '\n' + saved['raw']
		else:
			exception = ref.get('anchor_exception', {})
			if not isinstance(exception, dict):
				raise ValueError('Documentation without an anchor needs a named saved section')
			if not observation or exception.get('observation') != observation:
				raise ValueError('Documentation anchor exception must bind the exact primary observation')
			matches = [section for section in data['sections'] if section['text'] == exception.get('section')]
			if 1 != len(matches):
				raise ValueError('Documentation section is missing or ambiguous')
			if matches[0].get('anchor') or matches[0].get('ancestor_anchors'):
				raise ValueError('Documentation section has an available anchor; use its verified address')
			text = matches[0]['content']
	saved['quantity_context'] = saved['data']['text'] if 'html' == saved['kind'] and (not saved.get('fragment')) and (not ref.get('documentation')) else text
	if 'lines' == locator['type']:
		match = re.fullmatch('([1-9][0-9]*)-([1-9][0-9]*)', locator['value'])
		if not match or int(match[2]) < int(match[1]) or int(match[2]) > len(text.splitlines()):
			raise ValueError('Line locator must name an existing inclusive line range')
		text = '\n'.join(text.splitlines()[int(match[1]) - 1:int(match[2])])
	if 'text' == locator['type'] and (not contains_quote(text, locator['value'], ref.get('quote_match', 'exact'))):
		raise ValueError('Exact text locator is absent from primary source')
	if 'text' == locator['type']:
		text = locator['value']
	if not contains_quote(text, ref['quote'], ref.get('quote_match', 'exact')):
		raise ValueError('Exact quote is absent from the located primary source')
	r = saved
	return r
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
def evidence_contract_issues(root, value):
	if not isinstance(value, dict) or 3 != value.get('schema_version'):
		return []
	structural = contract_issues(value)
	if structural:
		return structural
	issues, capabilities, refs, index = ([], {}, {}, claim_index(value))
	direct_obs_urls, direct_obs_metas = ({}, {})
	def add(code, field, message, claim):
		issues.append(problem(code, field, message, claim_id=claim.get('id')))
	for field, _, claim in claim_locations(value):
		ident = claim.get('id')
		if not _text(ident):
			add('primary.claim_id', field + '/id', 'Primary evidence needs a valid claim ID', claim)
			continue
		capabilities[ident] = set()
		direct_obs_urls[ident] = set()
		direct_obs_metas[ident] = []
		for number, ref in enumerate(claim.get('evidence', []) if isinstance(claim.get('evidence'), list) else []):
			if not isinstance(ref, dict):
				continue
			try:
				caps, saved = _primary_capabilities(root, ref)
				capabilities[ident].update(caps)
				refs[ref.get('id')] = (claim, ref, saved)
				if 'observation' == ref.get('kind'):
					direct_obs_urls[ident].add(ref.get('source', ''))
					if isinstance(saved, dict) and isinstance(saved.get('meta'), dict):
						direct_obs_metas[ident].append(saved['meta'])
			except (OSError, ValueError, KeyError, IndexError, TypeError, UnicodeError, ImportError) as exc:
				add('primary.unconfirmed', field + f'/evidence/{number}', str(exc), claim)
	memo = {}
	def inherited(ident, active=None):
		active = set() if None is active else active
		if ident in memo:
			r = memo[ident]
		elif ident in active or ident not in index:
			r = set()
		else:
			active = active | {ident}
			result = set(capabilities.get(ident, set()))
			for dep in _dependencies(index[ident]):
				if isinstance(dep, dict) and dep.get('claim_id') in index:
					result.update(inherited(dep['claim_id'], active))
			memo[ident] = result
			r = result
		return r
	def inherited_urls(ident, active=None):
		active = set() if None is active else active
		if ident in active or ident not in index:
			r = set()
		else:
			active = active | {ident}
			result = set(direct_obs_urls.get(ident, set()))
			for dep in _dependencies(index[ident]):
				if isinstance(dep, dict) and dep.get('claim_id') in index:
					result.update(inherited_urls(dep['claim_id'], active))
			r = result
		return r
	def inherited_metas(ident, active=None):
		active = set() if None is active else active
		if ident in active or ident not in index:
			r = []
		else:
			active = active | {ident}
			result = list(direct_obs_metas.get(ident, []))
			for dep in _dependencies(index[ident]):
				if isinstance(dep, dict) and dep.get('claim_id') in index:
					result.extend(inherited_metas(dep['claim_id'], active))
			r = result
		return r
	for field, _, claim in claim_locations(value):
		if not _text(claim.get('id')):
			continue
		ident = claim['id']
		caps = inherited(ident)
		obs_urls = inherited_urls(ident)
		obs_metas = inherited_metas(ident)
		status = claim.get('verification_status')
		text_blob = str(claim.get('essence', '')) + ' ' + str(claim.get('assessment_basis', ''))
		if re.search('(?i)\\bgetaddrinfo\\b|\\bnxdomain\\b|\\u043d\\u0435\\s+\\u0440\\u0435\\u0437\\u043e\\u043b\\u0432\\u0438\\u0442\\u0441\\u044f(?:\\s+\\u043d\\u0430\\s+\\u0443\\u0440\\u043e\\u0432\\u043d\\u0435\\s+dns)?|dns\\s+(?:resolution\\s+failed|\\u043d\\u0435\\s+\\u0440\\u0435\\u0437\\u043e\\u043b\\u0432)', text_blob):
			has_dns_err = any(('dns_error' == m.get('error_kind') or False is m.get('dns_resolved') for m in obs_metas))
			if not has_dns_err and root:
				http_root = Path(root).resolve() / 'ꘖ/KB/Evidence/HTTP'
				if http_root.is_dir():
					for obs_file in http_root.rglob('observation.json'):
						try:
							m = json.loads(obs_file.read_text(encoding='utf-8'))
							if 'dns_error' == m.get('error_kind') or False is m.get('dns_resolved'):
								has_dns_err = True
								break
						except (OSError, ValueError):
							pass
			if not has_dns_err:
				add('claim.unverified_dns', field + '/essence', 'Claim asserts DNS non-resolution (getaddrinfo/NXDOMAIN) without a saved observation showing error_kind == dns_error; distinguish TCP timeout from DNS failure', claim)
		if 'verified' == status:
			for prop in claim.get('properties', []) if isinstance(claim.get('properties'), list) else []:
				if 'calculation' == prop:
					continue
				if not _text(prop) or prop not in caps:
					add('claim.method_insufficient', field + '/properties', 'Saved methods cannot verify property ' + prop + '; keep a limited hypothesis and list the missing check', claim)
			for dep in _dependencies(claim):
				target = index.get(dep.get('claim_id')) if isinstance(dep, dict) and _text(dep.get('claim_id')) else None
				if target and 'verified' != target.get('verification_status'):
					add('claim.unverified_premise', field + '/derived_from', 'A verified conclusion cannot rely on an incomplete or hypothetical premise', claim)
			if set(claim.get('properties', [])) & {'content', 'markup', 'dom'} and obs_urls:
				observed_paths = {urlsplit(urldefrag(u)[0]).path.rstrip('/') or '/' for u in obs_urls if u}
				sample_items = (claim.get('scope') or {}).get('sample') or []
				sample_urls = [s.strip() for s in sample_items if isinstance(s, str) and (s.strip().startswith(('http://', 'https://')) or s.strip().startswith('/')) and ('example.invalid' not in s)]
				sample_paths = {urlsplit(urldefrag(s)[0]).path.rstrip('/') or '/' for s in sample_urls}
				if observed_paths and all((p.lower().endswith(('sitemap.xml', 'robots.txt')) for p in observed_paths)):
					non_sitemap_samples = {p for p in sample_paths if not p.lower().endswith(('sitemap.xml', 'robots.txt'))}
					if non_sitemap_samples or re.search('(?i)(?:\\u0434\\u0435\\u043c\\u043e-\\u0437\\u0430\\u043f\\u0438\\u0441|\\u0434\\u0435\\u043c\\u043e-\\u0441\\u0442\\u0440\\u0430\\u043d\\u0438\\u0446|\\u0448\\u0430\\u0431\\u043b\\u043e\\u043d\\u043d\\w+\\s+\\u0437\\u0430\\u0433\\u043b\\u0443\\u0448\\u043a|\\u043f\\u0443\\u0441\\u0442\\w+\\s+\\u0441\\u0442\\u0440\\u0430\\u043d\\u0438\\u0446|demo\\s+post|placeholder\\s+page|thin\\s+content)', str(claim.get('essence', ''))):
						add('claim.sitemap_insufficient', field + '/evidence', 'A sitemap.xml/robots.txt observation only proves URL listing in XML, not the HTTP status, content or markup of target pages; collect the target page URLs or CMS JSON first', claim)
				if sample_paths and (len(sample_paths) > len(observed_paths) or (any((p not in ('/', '/sitemap.xml', '/robots.txt') for p in sample_paths)) and observed_paths.issubset({'/', '/sitemap.xml', '/robots.txt'}))):
					add('claim.unobserved_sample', field + '/scope/sample', 'Verified claim scope.sample lists page URLs that were not observed in primary evidence; collect every sampled URL or narrow scope.sample', claim)
				non_sitemap_observed = {p for p in observed_paths if not p.lower().endswith(('sitemap.xml', 'robots.txt'))}
				if len(non_sitemap_observed) <= 1 and re.search('(?i)(?:\\u043d\\u0430\\s+(?:\\u0432\\u0441\\u0451\\u043c\\s+)?\\u0441\\u0430\\u0439\\u0442\\u0435|\\u043f\\u043e\\u043b\\u043d\\u043e\\u0441\\u0442\\u044c\\u044e\\s+\\u043e\\u0442\\u0441\\u0443\\u0442\\u0441\\u0442\\u0432\\u0443|\\u043e\\u0442\\u0441\\u0443\\u0442\\u0441\\u0442\\u0432\\u0443\\u044e\\u0442\\s+\\u0441\\u0445\\u0435\\u043c\\u044b\\s+`?(?:Product|Offer|Article)|absent\\s+across\\s+the\\s+entire\\s+site|no\\s+(?:Product|Offer|Article)\\s+schema\\s+on\\s+the\\s+site)', str(claim.get('essence', ''))):
					add('claim.scope_extrapolation', field + '/scope', 'Homepage/single-page/sitemap observations alone cannot verify site-wide absence of Product/Offer/Article structured data; observe representative product/article pages or keep status limited', claim)
		if 'calculation' == claim.get('knowledge_type') or 'calculation' in (claim.get('properties') or []):
			try:
				_check_calculation(claim, index, refs)
			except (ValueError, KeyError, TypeError, InvalidOperation, ZeroDivisionError) as exc:
				add('calculation.unconfirmed', field + '/calculation', str(exc), claim)
	return issues
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
	if 0 == operands['old']:
		raise ValueError('Percentage change denominator old must be nonzero')
	with localcontext() as context:
		context.prec = 50
		expected = ((operands['new'] - operands['old']) / operands['old'] * Decimal(100)).quantize(Decimal(1).scaleb(-value['rounding_places']), rounding=ROUND_HALF_UP)
	actual = Decimal(value['result'])
	if not actual.is_finite() or actual != expected:
		raise ValueError(f"Percentage change is {expected}, not {value['result']}; formula includes the declared denominator and rounding")
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
