# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from pathlib import Path
import hashlib
import json
import re
from .diagnostics import problem, require_valid
from .storage import create_bytes, data_dir_for, locked, replace_bytes, write_immutable_bytes
SECTIONS = ('identity', 'concerns', 'misconceptions', 'causes', 'methods')
TITLES = ('Client Identification', 'Client Concerns', 'Possible Misconceptions', 'Causes of the Problem in This Client System', 'Solution Methods')
# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
def analysis_issues(value):
	issues, claims, references = ([], {}, [])
	def add(code, field, message, ident=None, hint=None):
		issues.append(problem(code, field, message, claim_id=ident, hint=hint))
	if not isinstance(value, dict):
		r = [problem('analysis.object', '/', 'Analysis must be a JSON object')]
	else:
		if type(value.get('schema_version', 1)) is not int or value.get('schema_version', 1) not in (1, 2, 3):
			add('analysis.version', '/schema_version', 'Supported versions: legacy 1/2 (read only), 3 (current)')
		notes = value.get('notes', {})
		if not isinstance(notes, dict):
			add('analysis.notes', '/notes', 'Analysis notes must be an object')
			notes = {}
		registry = value.get('sources', {})
		if not isinstance(registry, dict):
			add('source.registry', '/sources', 'Sources must be an object')
			registry = {}
		for source_id, source in registry.items():
			if not isinstance(source, str) or not source.strip():
				add('source.registry', f'/sources/{source_id}', 'Source ID must resolve to a nonempty source URI')
		for section in SECTIONS:
			items = value.get(section)
			if not isinstance(items, list):
				add('analysis.section', '/' + section, f'Analysis requires list: {section}')
				continue
			if not items and (not (isinstance(notes.get(section), str) and notes[section].strip())):
				add('analysis.empty', '/' + section, 'Explain what is unknown/not established in notes')
			for index, item in enumerate(items):
				field = f'/{section}/{index}'
				if not isinstance(item, dict):
					add('claim.object', field, 'Each claim must be an object')
					continue
				ident = item.get('id')
				if not isinstance(ident, str) or not re.fullmatch('[A-Z][A-Z0-9-]*', ident) or ident in claims:
					add('claim.id', field + '/id', 'Invalid or duplicate claim ID', str(ident))
				else:
					claims[ident] = section
				for key in ('essence', 'assessment_basis') + (('criterion',) if 'methods' == section else ()):
					if not isinstance(item.get(key), str) or not item[key].strip():
						add('claim.required', field + '/' + key, f'{key} is required', ident)
				score_key = 'score_percent' if 'methods' == section else 'probability_percent'
				score = item.get(score_key)
				if type(score) is not int or not 0 <= score <= 100:
					add('claim.score', field + '/' + score_key, 'Assessment must be an integer from 0 to 100', ident)
				addresses = item.get('addresses', [])
				if not isinstance(addresses, list) or any((not isinstance(x, str) for x in addresses)):
					add('claim.addresses', field + '/addresses', 'addresses must be a list of claim IDs', ident)
				else:
					references.append((field, ident, section, addresses))
					if section in ('causes', 'methods') and (not addresses):
						add('claim.addresses', field + '/addresses', 'Link causes to concerns, methods to causes/tasks', ident)
				for side in ('for', 'against'):
					arguments = item.get(side)
					if not isinstance(arguments, list):
						add('argument.list', field + '/' + side, f'{side} must be a list', ident)
						continue
					if not arguments:
						gap = item.get('counterevidence', {}) if 'against' == side else {}
						if 'against' != side or not valid_gap(gap):
							add('argument.empty', field + '/' + side, 'Concrete arguments required; empty against needs documented counterevidence status', ident)
					for number, arg in enumerate(arguments):
						af = f'{field}/{side}/{number}'
						if not isinstance(arg, dict):
							add('argument.object', af, 'Each argument must be an object', ident)
							continue
						if 3 == value.get('schema_version') and (arg.get('claim_id') or arg.get('evidence_id')):
							if not isinstance(arg.get('argument'), str) or not arg['argument'].strip():
								add('argument.required', af + '/argument', 'argument is required', ident)
							if arg.get('claim_id') and arg.get('evidence_id'):
								add('argument.source', af, 'Use one claim_id or evidence_id reference', ident)
							continue
						for key in ('argument', 'quote'):
							if not isinstance(arg.get(key), str) or not arg[key].strip():
								add('argument.required', af + '/' + key, f'{key} is required', ident)
						source = source_uri(arg, registry)
						if not isinstance(source, str) or not source.strip():
							add('argument.source', af + '/source', 'Needs a source or a resolvable source_id', ident)
						if arg.get('source') and arg.get('source_id'):
							add('argument.source', af, 'Use source or source_id, not two competing references', ident)
						if arg.get('documentation') and isinstance(source, str) and ('#' not in source or not source.split('#', 1)[1]):
							locator = arg.get('anchor_exception')
							if not isinstance(locator, dict) or not all((isinstance(locator.get(k), str) and locator[k].strip() for k in ('section', 'observation'))):
								add('documentation.locator', af + '/anchor_exception', 'Documentation needs a section anchor or section + saved observation', ident, 'collect the page; record its section and observation URI; verify evidence')
		for field, ident, section, addresses in references:
			for target in addresses:
				if target not in claims:
					add('claim.reference', field + '/addresses', f'Unknown claim reference: {target}', ident)
			allowed = ('concerns',) if 'causes' == section else ('concerns', 'causes')
			if section in ('causes', 'methods') and addresses and (not any((claims.get(x) in allowed for x in addresses))):
				add('claim.reference_kind', field + '/addresses', 'Reference must address a concern or applicable cause', ident)
		from .red_flags import red_flag_issues
		issues.extend(red_flag_issues(value, claims))
		from .knowledge import website_issues
		issues.extend(website_issues(value))
		from .claims import contract_issues
		issues.extend(contract_issues(value))
		r = issues
	return r
def valid_gap(gap):
	return isinstance(gap, dict) and gap.get('status') in ('not_found', 'unavailable') and isinstance(gap.get('reviewed_sources'), list) and bool(gap['reviewed_sources']) and all((isinstance(x, str) and x.strip() for x in gap['reviewed_sources'])) and isinstance(gap.get('limitations'), str) and bool(gap['limitations'].strip())
def source_uri(argument, registry):
	if 'source_id' not in argument:
		r = argument.get('source')
	else:
		ident = argument.get('source_id')
		r = registry.get(ident) if isinstance(ident, str) and ident else None
	return r
def validate_analysis(value):
	require_valid(analysis_issues(value))
def save_analysis(root, candidate, expected_sha256=None):
	from .research import inside
	root = Path(root).resolve()
	value = candidate if isinstance(candidate, dict) else json.loads(inside(root, candidate).read_text(encoding='utf-8-sig'))
	validate_analysis(value)
	require_current_contract(value)
	from .evidence import evidence_issues
	require_valid(evidence_issues(root, value))
	payload = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
	target = root / 'ꘖ/KB/Analysis.json'
	target.parent.mkdir(parents=True, exist_ok=True)
	with locked(root / 'ꘖ/data/analysis.lock'):
		previous = target.read_bytes() if target.exists() else None
		if None is not previous and digest(previous) != expected_sha256:
			raise ValueError('Analysis changed or expected hash was not supplied; read current KB and reconcile the candidate')
		if None is previous and None is not expected_sha256:
			raise ValueError('Expected existing analysis is missing; preserve candidate and inspect state')
		if None is not previous and previous != payload:
			write_immutable_bytes(root / 'ꘖ/data/analysis-history' / (digest(previous) + '.json'), previous)
		if (target.read_bytes() if target.exists() else None) != previous:
			raise ValueError('Analysis changed during commit; external edit preserved')
		if None is previous:
			create_bytes(target, payload)
		elif previous != payload:
			replace_bytes(target, payload)
	r = {'target': str(target), 'sha256': digest(payload), 'schema_valid': True, 'evidence_checked': True, 'detail': 'Primary references checked; update dependent agent KB modules before independent semantic review'}
	return r
def require_current_contract(value):
	require_valid([] if isinstance(value, dict) and 3 == value.get('schema_version') else [problem('analysis.current_contract', '/schema_version', 'New saved/published analyses require schema_version 3 and explicit provenance; preserve legacy files and reconcile a candidate')])
def iter_arguments(value):
	registry = value.get('sources', {})
	registry = registry if isinstance(registry, dict) else {}
	for section in SECTIONS:
		for index, item in enumerate(value.get(section, []) if isinstance(value.get(section), list) else []):
			if not isinstance(item, dict):
				continue
			for side in ('for', 'against'):
				for number, arg in enumerate(item.get(side, []) if isinstance(item.get(side), list) else []):
					if isinstance(arg, dict):
						yield (item.get('id'), f'/{section}/{index}/{side}/{number}', arg, source_uri(arg, registry))
def render_analysis(value):
	validate_analysis(value)
	from .red_flags import render_red_flags
	from .links import markdown_link
	lines = [render_red_flags(value)] if value.get('red_flags') else []
	if 3 == value.get('schema_version'):
		lines.extend(['# Primary Observations and Calculations', ''])
		for fact in value['facts']:
			lines.extend([f"## {fact['id']}", fact['essence'], '', *_render_claim_contract(fact)])
	for number, (key, title) in enumerate(zip(SECTIONS, TITLES), 1):
		lines.extend([f'# {number}. {title}', ''])
		if not value[key]:
			lines.extend([value['notes'][key], ''])
		for item in value[key]:
			lines.extend([f"## {item['id']}", item['essence'], ''])
			if 3 == value.get('schema_version'):
				lines.extend(_render_claim_contract(item))
			if item.get('addresses'):
				lines.extend(['Addresses: ' + ', '.join((f'[{i}](#{i.lower()})' for i in item['addresses'])) + '.', ''])
			for side, label in (('for', 'For'), ('against', 'Against')):
				lines.append(f'### {label}')
				for arg in item[side]:
					if 3 == value.get('schema_version') and (arg.get('claim_id') or arg.get('evidence_id')):
						target = arg.get('claim_id') or arg['evidence_id']
						lines.extend([arg['argument'], f'[Basis: {target}](#{target.lower()})', ''])
						continue
					source = source_uri(arg, value.get('sources', {}))
					lines.extend([arg['argument'], '> ' + arg['quote'].replace('\n', '\n> '), markdown_link('Source', source), ''])
					if arg.get('anchor_exception'):
						locator = arg['anchor_exception']
						lines.extend([f"Section: {locator['section']}.", markdown_link('Address verification', locator['observation']), ''])
				if 'against' == side and (not item[side]):
					gap = item['counterevidence']
					lines.extend([f"Counterevidence status: {gap['status']}.", gap['limitations'], ''])
					lines.extend((markdown_link('Reviewed source', x) for x in gap['reviewed_sources']))
					lines.append('')
			if 'methods' == key:
				lines.append(f"Score: {item['score_percent']}% ({item['criterion']}).")
			else:
				lines.append(f"Expert plausibility: {item['probability_percent']}%.")
			lines.extend([item['assessment_basis'], ''])
	r = '\n'.join(lines)
	return r
def _render_claim_contract(claim):
	from .links import markdown_link
	lines = [f"Kind: {claim['knowledge_type']}. Verification status: {claim['verification_status']}.", 'Scope: ' + claim['scope']['description'], '']
	if claim['scope']['sample']:
		lines.extend(['Verified objects: ' + '; '.join(claim['scope']['sample']) + '.', ''])
	for limitation in claim['scope']['limitations']:
		lines.extend(['Limitation: ' + limitation, ''])
	for dep in claim['derived_from']:
		lines.extend([f"Dependency: [{dep['claim_id']}](#{dep['claim_id'].lower()}), version `{dep['sha256']}`.", ''])
	for ref in claim['evidence']:
		lines.extend([f"### {ref['id']}", '> ' + ref['quote'].replace('\n', '\n> '), markdown_link('Primary source', ref['source']), f"Locator: {ref['locator']['type']}: {ref['locator']['value']}. SHA-256: `{ref['source_sha256']}`.", ''])
		if ref.get('anchor_exception'):
			exception = ref['anchor_exception']
			lines.extend(['Documentation section: ' + exception['section'] + '.', markdown_link('Saved anchor-absence verification', exception['observation']), ''])
	for missing in claim['missing_checks']:
		lines.extend(['Missing check: ' + missing, ''])
	if claim.get('alternative_explanations'):
		lines.extend(['Alternatives: ' + '; '.join(claim['alternative_explanations']) + '.', claim['discriminating_check'], ''])
	if claim.get('applicability'):
		lines.extend(['Applicability conditions: ' + '; '.join(claim['applicability']) + '.', 'Result validation: ' + claim['validation'], ''])
	lines.extend(['Impact: ' + claim['impact']['severity'] + '. ' + claim['impact']['basis'], ''])
	if claim.get('calculation'):
		calc = claim['calculation']
		lines.extend([f"Calculation: `{calc['formula']}`; old={calc['operands']['old']['value']} {calc['operands']['old']['unit']}; new={calc['operands']['new']['value']} {calc['operands']['new']['unit']}; result {calc['result']}%; rounding {calc['rounding']} to {calc['rounding_places']} places.", ''])
	r = lines
	return r
def publish_analysis(source, target=None):
	from .red_flags import sync_project_red_flags
	source = Path(source).resolve()
	value = json.loads(source.read_text(encoding='utf-8-sig'))
	require_current_contract(value)
	if not ('Analysis.json' == source.name and 'KB' == source.parent.name and ('ꘖ' == source.parent.parent.name)):
		raise ValueError('Publish a reconciled schema 3 candidate from its project ꘖ/KB/Analysis.json')
	from .evidence import evidence_issues
	validate_analysis(value)
	require_valid(evidence_issues(source.parents[2], value))
	result = publish_owned(target or source.with_suffix('.md'), render_analysis(value), source=source)
	if 'conflict' == result['status']:
		r = result
	else:
		if 'Analysis.json' == source.name and 'KB' == source.parent.name and ('ꘖ' == source.parent.parent.name):
			from .knowledge import sync_website_card
			result['website_card'] = sync_website_card(source.parents[2], value)
			card = sync_project_red_flags(source.parents[2], value)
			result['project_card'] = card
			if 'conflict' == card['status']:
				result['status'] = 'conflict'
			if 'conflict' == result['website_card']['status']:
				result['status'] = 'conflict'
		r = result
	return r
def digest(data):
	return hashlib.sha256(data).hexdigest()
def publish_owned(target, content, *, source=None, history=True):
	target = Path(target).resolve()
	payload = content.encode('utf-8') if isinstance(content, str) else content
	if target.suffix.lower() in ('.md', '.markdown', '.txt', '.html', '.htm'):
		from .links import readable_link_issues
		issues = readable_link_issues(payload.decode('utf-8'))
		if issues:
			raise ValueError('\n'.join(issues))
	state_dir = data_dir_for(target)
	state_file = state_dir / 'rendered.json'
	with locked(state_dir / 'render.lock'):
		receipt = json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else {}
		key = str(target)
		previous = target.read_bytes() if target.exists() else None
		expected = receipt.get(key, {}).get('sha256')
		if None is not previous and previous != payload and (digest(previous) != expected):
			candidate = write_immutable_bytes(state_dir / 'render-candidates' / (digest(key.encode())[:16] + '-' + digest(payload)[:16] + target.suffix), payload)
			r = {'status': 'conflict', 'target': str(target), 'candidate': str(candidate), 'detail': 'Existing file is untracked or changed; preserved for reconciliation'}
		else:
			if history and None is not previous and (previous != payload):
				write_immutable_bytes(state_dir / 'render-history' / digest(key.encode())[:16] / (digest(previous) + target.suffix), previous)
			target.parent.mkdir(parents=True, exist_ok=True)
			if (target.read_bytes() if target.exists() else None) != previous:
				raise ValueError('Target changed during publication; preserve the external edit and retry reconciliation')
			if previous != payload:
				replace_bytes(target, payload)
			if target.read_bytes() != payload:
				raise OSError('Published file failed read-back verification')
			receipt[key] = {**receipt.get(key, {}), 'sha256': digest(payload), 'source': source if isinstance(source, dict) else str(source) if source else None}
			replace_bytes(state_file, (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode())
			r = {'status': 'unchanged' if previous == payload else 'published', 'target': str(target), 'sha256': digest(payload)}
	return r
