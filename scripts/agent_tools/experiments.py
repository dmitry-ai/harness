# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from .research import inside, json_data, load_observation, observation_capabilities, request_context
from .storage import create_bytes
STATUSES = ('verified', 'refuted', 'unverified', 'unavailable')
METHODS = ('http', 'dom', 'browser_scenario', 'admin', 'serp', 'geolocation')
OPERATORS = ('equals', 'not_equals', 'contains', 'gt', 'gte', 'lt', 'lte')
PROPERTY_METHODS = {'content': set(METHODS), 'markup': {'http', 'dom', 'browser_scenario'}, 'dom': {'dom', 'browser_scenario'}, 'interaction': {'browser_scenario'}, 'currency_transition': {'browser_scenario'}, 'ip_country': {'geolocation', 'browser_scenario'}, 'admin_configuration': {'admin'}, 'serp': {'serp'}, 'platform_capability': {'http', 'dom'}, 'causality': set(), 'business_impact': set()}
def digest(value):
	return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
def _text(value):
	return isinstance(value, str) and bool(value.strip())
def requirement_issues(requirements):
	issues, seen = ([], set())
	if not isinstance(requirements, list) or not requirements:
		r = ['Research needs nonempty property-specific experimental requirements']
	else:
		for number, requirement in enumerate(requirements, 1):
			label = f'Requirement {number}'
			if not isinstance(requirement, dict):
				issues.append(label + ': object required')
				continue
			ident = requirement.get('id')
			if not _text(ident) or ident in seen:
				issues.append(label + ': unique nonempty id required')
			if isinstance(ident, str):
				seen.add(ident)
			for field in ('claim', 'expected', 'falsification', 'discriminating_test', 'completion_criterion'):
				if not _text(requirement.get(field)):
					issues.append(label + f': {field} required')
			alternatives = requirement.get('alternatives')
			if not isinstance(alternatives, list) or not alternatives or (not all((_text(x) for x in alternatives))):
				issues.append(label + ': explicit alternative explanations required')
			prop, method = (requirement.get('property'), requirement.get('method'))
			if prop not in PROPERTY_METHODS or method not in METHODS:
				issues.append(label + ': supported property and measurement method required')
			elif method not in PROPERTY_METHODS[prop]:
				issues.append(label + ': method cannot establish the requested property; split the observation from the inference')
			scope = requirement.get('scope')
			if not isinstance(scope, dict) or not isinstance(scope.get('objects'), list) or (not scope['objects']) or (not all((_text(x) for x in scope['objects']))):
				issues.append(label + ': scope.objects must identify the exact sampled objects')
			if not isinstance(requirement.get('conditions'), dict):
				issues.append(label + ': explicit conditions object required')
			assertions = requirement.get('assertions', [])
			if not isinstance(assertions, list):
				issues.append(label + ': assertions must be a list')
				continue
			assertion_ids = set()
			for assertion in assertions:
				if not isinstance(assertion, dict):
					issues.append(label + ': deterministic assertion object required')
					continue
				if not _text(assertion.get('id')) or assertion.get('id') in assertion_ids:
					issues.append(label + ': assertion needs a unique id')
				if isinstance(assertion.get('id'), str):
					assertion_ids.add(assertion['id'])
				if bool(_text(assertion.get('artifact_id'))) == bool(_text(assertion.get('artifact_role'))):
					issues.append(label + ': assertion prebinds exactly one logical artifact ID or role')
				locator = assertion.get('locator', {})
				if not isinstance(locator, dict) or locator.get('type') not in ('json_pointer', 'text') or (not isinstance(locator.get('value'), str)) or ('json_pointer' == locator.get('type') and locator['value'] and (not locator['value'].startswith('/'))):
					issues.append(label + ': assertion needs an exact JSON pointer or text locator')
				for comparison in (assertion, assertion.get('disconfirming', {})):
					if not isinstance(comparison, dict) or comparison.get('operator') not in OPERATORS or 'expected' not in comparison or isinstance(comparison.get('expected'), (dict, list)):
						issues.append(label + ': explicit positive and disconfirming deterministic comparisons required')
		r = issues
	return r
def _compare(actual, operator, expected):
	if operator in ('equals', 'not_equals'):
		equal = type(actual) is type(expected) and actual == expected
		if type(actual) in (int, float) and type(expected) in (int, float):
			equal = actual == expected
		r = equal if 'equals' == operator else not equal
	elif 'contains' == operator:
		if not isinstance(actual, str) or not isinstance(expected, str):
			raise ValueError('contains needs text')
		r = expected in actual
	else:
		if type(actual) not in (int, float) or type(expected) not in (int, float):
			raise ValueError('Numeric comparison needs JSON numbers')
		r = {'gt': lambda: actual > expected, 'gte': lambda: actual >= expected, 'lt': lambda: actual < expected, 'lte': lambda: actual <= expected}[operator]()
	return r
def _select_raw(raw, locator):
	if 'text' == locator['type']:
		text = raw.decode('utf-8')
		if locator['value'] and locator['value'] not in text:
			raise ValueError('Text locator absent')
		r = locator['value'] or text
	else:
		def invalid_constant(value):
			raise ValueError('Non-finite JSON number')
		value = json.loads(raw, parse_constant=invalid_constant)
		for token in locator['value'].split('/')[1:] if locator['value'] else []:
			token = token.replace('~1', '/').replace('~0', '~')
			if isinstance(value, list):
				if not re.fullmatch('0|[1-9][0-9]*', token):
					raise ValueError('Invalid JSON array pointer')
				value = value[int(token)]
			elif isinstance(value, dict):
				value = value[token]
			else:
				raise ValueError('JSON pointer enters a scalar')
		r = value
	return r
def evaluate_assertions(run, contents):
	assertions = run['requirement'].get('assertions', [])
	artifacts = _artifact_map(run)
	results = []
	for assertion in assertions:
		matches = [item for item in artifacts.values() if item.get('id') == assertion['artifact_id']] if assertion.get('artifact_id') else [item for item in artifacts.values() if item.get('role') == assertion.get('artifact_role')]
		result = {'assertion_id': assertion['id'], 'status': 'unverified'}
		try:
			if 1 != len(matches):
				raise ValueError('Assertion must select exactly one primary artifact')
			artifact = matches[0]
			method = run['requirement']['method']
			primary = artifact.get('observation_kind') == method and bool(artifact.get('source_observation'))
			if artifact.get('native_event_id'):
				event = next((item for item in run.get('native_trace', {}).get('events', []) if item.get('id') == artifact['native_event_id']), {})
				primary = bool(_event_actions(event)) and None is not _event_browser_identity(event) if method in ('browser_scenario', 'admin', 'geolocation') else 'serp' == method and True is event.get('successful')
			if 'geolocation' == method and True is artifact.get('geolocation_verified'):
				primary = True
			if not primary:
				raise ValueError('Assertion does not select an authentic primary measurement of this method')
			actual = _select_raw(contents[artifact['id']], assertion['locator'])
			positive = _compare(actual, assertion['operator'], assertion['expected'])
			disconfirming = assertion['disconfirming']
			negative = _compare(actual, disconfirming['operator'], disconfirming['expected'])
			result.update(artifact_id=artifact['id'], artifact_sha256=artifact['sha256'], positive=positive, disconfirming=negative, selected_value_sha256=digest(actual), status='verified' if positive and (not negative) else 'refuted' if negative and (not positive) else 'unverified')
		except (ValueError, TypeError, KeyError, IndexError, UnicodeError) as exc:
			result['reason'] = type(exc).__name__ + ': missing, ambiguous or unparsable primary measurement'
		results.append(result)
	statuses = {item['status'] for item in results}
	status = 'refuted' if 'refuted' in statuses else 'unverified' if not results or 'unverified' in statuses else 'verified'
	r = {'status': status, 'assertions': results, 'interpretation': 'Restricted predicates establish only the preregistered raw property; A.A checks semantic entailment and alternative explanations'}
	return r
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
def prepare_experiment(root, requirement, *, amendment_of=None, amendment_reason=None):
	issues = requirement_issues([requirement])
	if issues:
		raise ValueError('; '.join(issues))
	root = Path(root).resolve()
	previous = None
	if None is not amendment_of:
		previous = load_plan(root, amendment_of)
		if not _text(amendment_reason):
			raise ValueError('Plan amendment needs an explicit reason')
		if previous['requirement']['id'] != requirement['id']:
			raise ValueError('An amendment must preserve the experimental requirement ID')
	elif amendment_reason:
		raise ValueError('Amendment reason needs the exact previous immutable plan')
	plan = {'schema_version': 1, 'kind': 'experiment_plan', 'prepared_at': datetime.now(timezone.utc).isoformat(timespec='microseconds'), 'requirement': requirement, 'requirement_sha256': digest(requirement), 'revision': previous['revision'] + 1 if previous else 1, 'amendment_of': amendment_of, 'amendment_reason': amendment_reason, 'previous_plan_sha256': digest(previous) if previous else None}
	directory = root / 'ꘖ/KB/Evidence/Experiments/Plans' / digest(plan)
	directory.mkdir(parents=True, exist_ok=False)
	path = directory / 'plan.json'
	create_bytes(path, json_data(plan))
	r = {'upwork_experiment_plan': 1, 'project_root': str(root), 'plan': path.relative_to(root / 'ꘖ/KB').as_posix(), 'plan_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), **plan}
	return r
def load_plan(root, reference):
	path = inside(Path(root).resolve() / 'ꘖ/KB', reference)
	base = Path(root).resolve() / 'ꘖ/KB/Evidence/Experiments/Plans'
	plan = json.loads(path.read_text(encoding='utf-8'))
	if not path.is_relative_to(base) or 'plan.json' != path.name or path.parent.name != digest(plan) or (1 != plan.get('schema_version')) or ('experiment_plan' != plan.get('kind')) or (plan.get('requirement_sha256') != digest(plan.get('requirement'))) or requirement_issues([plan.get('requirement')]):
		raise ValueError('Missing/changed immutable experimental plan')
	if plan.get('amendment_of'):
		previous = load_plan(root, plan['amendment_of'])
		if plan.get('previous_plan_sha256') != digest(previous) or plan.get('revision') != previous['revision'] + 1:
			raise ValueError('Plan revision chain changed')
	r = plan
	return r
def _after_plan(value, prepared_at):
	try:
		observed = datetime.fromisoformat(value.replace('Z', '+00:00'))
		prepared = datetime.fromisoformat(prepared_at)
		r = None is not observed.tzinfo and observed > prepared
	except (ValueError, TypeError, AttributeError):
		r = False
	return r
def _preregistration_issues(root, run):
	try:
		plan = load_plan(root, run['plan'])
		path = inside(Path(root) / 'ꘖ/KB', run['plan'])
		if hashlib.sha256(path.read_bytes()).hexdigest() != run.get('plan_sha256'):
			return ['Run does not bind the exact immutable plan hash']
		if plan['requirement_sha256'] != run.get('requirement_sha256'):
			return ['Run changed the preregistered statement, test, expected or falsifying outcomes']
	except (OSError, KeyError, ValueError, TypeError):
		return ['Run needs a valid immutable plan committed before observations']
	if run.get('status') not in ('verified', 'refuted'):
		return []
	issues = []
	observed = [item.get('observed_at') for item in run.get('artifacts', []) if item.get('source_observation')]
	events = run.get('native_trace', {}).get('events', [])
	commits = [event for event in events if _plan_commit(root, run, event)]
	observed += [event.get('created_at') for event in events if event not in commits]
	if not observed or any((not _after_plan(value, plan['prepared_at']) for value in observed)):
		issues.append('Verified/refuted run requires fresh timestamped observations/actions after this exact plan; saved data cannot masquerade as a newly performed test')
	if run['requirement']['method'] in ('browser_scenario', 'admin', 'serp'):
		actions = [event for event in events if event not in commits]
		if not commits or not actions or (not any((commit.get('output_step', -1) < min((event.get('step', -1) for event in actions)) for commit in commits))):
			issues.append('Native plan commitment receipt must precede the actual native observations/actions; a backdated file alone is not preregistration')
	expected_conditions = plan['requirement']['conditions']
	actual_conditions = run.get('conditions', {})
	for key in ('url_country', 'language', 'selected_country', 'currency', 'session_id'):
		if key in expected_conditions and actual_conditions.get(key) != expected_conditions[key]:
			issues.append('Actual experimental condition differs from preregistered ' + key)
	for key, field in (('session', 'mode'), ('egress', 'country')):
		value = expected_conditions.get(key, {}).get(field) if isinstance(expected_conditions.get(key), dict) else None
		if value not in (None, 'unknown') and actual_conditions.get(key, {}).get(field) != value:
			issues.append('Actual experimental condition differs from preregistered ' + key + '.' + field)
	return issues
def _result_bytes(value):
	return value.encode('utf-8') if isinstance(value, str) else json_data(value)
def _unconditional_browser_calls(code):
	token = re.compile('\\s+|"(?:\\\\.|[^"\\\\\\r\\n])*"|\'(?:\\\\.|[^\'\\\\\\r\\n])*\'|/\\*[\\s\\S]*?\\*/|//[^\\n]*|[A-Za-z_$][\\w$]*|-?(?:0|[1-9]\\d*)(?:\\.\\d+)?(?:[eE][+-]?\\d+)?|[.(),:{}\\[\\];]')
	tokens, position = ([], 0)
	while position < len(code):
		match = token.match(code, position)
		if not match:
			return []
		value = match.group()
		position = match.end()
		if value.isspace() or value.startswith(('//', '/*')):
			continue
		tokens.append(value)
	index = 0
	def take(value=None):
		nonlocal index
		if index >= len(tokens) or (None is not value and tokens[index] != value):
			raise ValueError('Unsupported browser syntax')
		result = tokens[index]
		index += 1
		r = result
		return r
	def literal(depth=0):
		if depth > 20:
			raise ValueError('Browser argument nesting exceeds supported grammar')
		value = take()
		if '{' == value:
			if index < len(tokens) and '}' == tokens[index]:
				take('}')
				return
			while True:
				key = take()
				if not (re.fullmatch('[A-Za-z_$][\\w$]*', key) or key.startswith(('"', "'"))):
					raise ValueError('Literal object key required')
				take(':')
				literal(depth + 1)
				if index < len(tokens) and '}' == tokens[index]:
					take('}')
					return
				take(',')
		elif '[' == value:
			if index < len(tokens) and ']' == tokens[index]:
				take(']')
				return
			while True:
				literal(depth + 1)
				if index < len(tokens) and ']' == tokens[index]:
					take(']')
					return
				take(',')
		elif not (value.startswith(('"', "'")) or value in ('true', 'false', 'null') or re.fullmatch('-?(?:0|[1-9]\\d*)(?:\\.\\d+)?(?:[eE][+-]?\\d+)?', value)):
			raise ValueError('Literal browser arguments required')
	terminal = {'click': 'click', 'selectOption': 'select', 'fill': 'fill', 'press': 'press', 'goto': 'navigate', 'navigate': 'navigate', 'getSnapshot': 'read', 'getDOMSnapshot': 'read', 'getAXState': 'read', 'domSnapshot': 'read', 'getState': 'inspect', 'screenshot': 'read'}
	locators = {'getByRole', 'getByText', 'getByLabel', 'getByPlaceholder', 'getByTestId', 'locator', 'nth', 'first', 'last'}
	calls = []
	try:
		while index < len(tokens):
			take('await')
			receiver = take()
			if not re.fullmatch('[A-Za-z_$][\\w$]*', receiver):
				raise ValueError('Browser receiver required')
			take('.')
			method = take()
			if 'playwright' == method:
				take('.')
				method = take()
			while True:
				take('(')
				if index < len(tokens) and ')' != tokens[index]:
					while True:
						literal()
						if index < len(tokens) and ')' == tokens[index]:
							break
						take(',')
				take(')')
				if method in terminal:
					calls.append((receiver, terminal[method]))
					break
				if method not in locators:
					raise ValueError('Unsupported browser method')
				take('.')
				method = take()
			if index < len(tokens):
				take(';')
		if 1 != len({receiver for receiver, action in calls}):
			return []
		if sum((action not in ('read', 'inspect') for receiver, action in calls)) > 1:
			return []
		return calls
	except (ValueError, IndexError):
		return []
def _native_tool_name(event):
	name = str(event.get('name', '')).casefold().replace('.', '__')
	namespace = str(event.get('namespace') or '').casefold().replace('.', '__')
	r = namespace + '__' + name if namespace and (not name.startswith(namespace + '__')) else name
	return r
def _event_actions(event):
	if True is not event.get('successful'):
		return set()
	name = _native_tool_name(event)
	args = event.get('arguments') or {}
	if not isinstance(args, dict):
		return set()
	direct = {'click_browser_element': 'click', 'browser_click': 'click', 'select_browser_option': 'select', 'browser_select_option': 'select', 'browser_navigate': 'navigate', 'read_browser_dom': 'read', 'browser_screenshot': 'read', 'browser_get_state': 'inspect'}
	for suffix, action in direct.items():
		if name == suffix or name.endswith('__' + suffix):
			return {action}
	if not (name.endswith('cua_repl__js') or name.endswith('browser__run')):
		return set()
	code = args.get('code', '')
	if not isinstance(code, str):
		return set()
	return {action for receiver, action in _unconditional_browser_calls(code)}
def _browser_identity_objects(value):
	if isinstance(value, dict):
		yield value
		for key in ('metadata', 'browser_context', 'browserContext', 'state', 'result', 'value', 'content'):
			if key in value:
				yield from _browser_identity_objects(value[key])
		if value.get('type') in ('input_text', 'text') and isinstance(value.get('text'), str):
			yield from _browser_identity_objects(value['text'])
	elif isinstance(value, list):
		for part in value:
			yield from _browser_identity_objects(part)
	elif isinstance(value, str):
		try:
			parsed = json.loads(value)
		except ValueError:
			return
		if not isinstance(parsed, str):
			yield from _browser_identity_objects(parsed)
def _event_browser_identity(event):
	if not _event_actions(event):
		return None
	aliases = {'browser_id': ('browser_id', 'browserId'), 'tab_id': ('tab_id', 'tabId', 'providerTabId'), 'context_id': ('context_id', 'contextId', 'browser_context_id', 'browserContextId'), 'session_id': ('session_id', 'sessionId')}
	def identity(value):
		result = {}
		for key, fields in aliases.items():
			values = {str(value[field]) for field in fields if isinstance(value.get(field), (str, int)) and str(value[field]).strip()}
			if len(values) > 1:
				return None
			if values:
				result[key] = values.pop()
		return result
	name = _native_tool_name(event)
	is_script = name.endswith(('cua_repl__js', 'browser__run'))
	candidates = [] if is_script else [identity(event.get('arguments', {}))]
	candidates += [identity(value) for value in _browser_identity_objects(event.get('result'))]
	if any((None is value for value in candidates)):
		return None
	candidates = [value for value in candidates if value]
	if not candidates:
		return None
	merged = {}
	for candidate in candidates:
		for key, value in candidate.items():
			if key in merged and merged[key] != value:
				return None
			merged[key] = value
	return merged if all((key in merged for key in ('browser_id', 'tab_id'))) else None
def _browser_context_issues(run):
	method = run['requirement']['method']
	if method not in ('browser_scenario', 'admin', 'serp'):
		r = []
	else:
		events = {event.get('id'): event for event in run.get('native_trace', {}).get('events', [])}
		relevant = [event for event in events.values() if _event_actions(event)]
		if 'browser_scenario' == method:
			for step in run.get('actual_steps', []):
				if not isinstance(step, dict):
					continue
				event = events.get(step.get('native_event_id'))
				if event and event not in relevant:
					relevant.append(event)
				for phase in ('before', 'after'):
					state = step.get(phase, {})
					if isinstance(state, dict):
						for event in _native_texts(run, state.get('evidence', [])):
							if event not in relevant:
								relevant.append(event)
		conditions = run.get('conditions', {})
		for key in ('session', 'egress'):
			condition = conditions.get(key, {})
			if isinstance(condition, dict) and 'verified' == condition.get('verification'):
				for event in _native_texts(run, condition.get('evidence', [])):
					if event not in relevant:
						relevant.append(event)
		if not relevant:
			r = [] if 'serp' == method else ['Native browser context/tab identity is unknown']
		else:
			identities = [_event_browser_identity(event) for event in relevant]
			if any((None is identity for identity in identities)):
				r = ['Actual native browser/context/tab identity is unknown; record unverified, not an interaction proof']
			elif any((identity != identities[0] for identity in identities[1:])):
				r = ['Native before/action/after/egress browser, context, tab or session identities differ; record unverified']
			else:
				r = []
	return r
def _artifact_map(run):
	return {item.get('id'): item for item in run.get('artifacts', []) if isinstance(item, dict)}
def _evidence_issues(ids, artifacts, label):
	if not isinstance(ids, list) or not ids or any((not isinstance(x, str) or x not in artifacts for x in ids)):
		r = [label + ': recorded primary artifact IDs required']
	else:
		r = []
	return r
def _native_texts(run, ids):
	artifacts = _artifact_map(run)
	events = {event['id']: event for event in run.get('native_trace', {}).get('events', [])}
	r = [events[item['native_event_id']] for ident in ids if (item := artifacts.get(ident, {})).get('native_event_id') in events]
	return r
def _objects(value):
	if isinstance(value, dict):
		yield value
		for child in value.values():
			yield from _objects(child)
	elif isinstance(value, list):
		for child in value:
			yield from _objects(child)
	elif isinstance(value, str):
		try:
			parsed = json.loads(value)
		except ValueError:
			decoder, start = (json.JSONDecoder(), 0)
			while (start := value.find('{', start)) >= 0:
				try:
					parsed, size = decoder.raw_decode(value[start:])
				except ValueError:
					start += 1
					continue
				yield from _objects(parsed)
				start += size
		else:
			if not isinstance(parsed, str):
				yield from _objects(parsed)
def _plan_commit(root, run, event):
	if True is not event.get('successful'):
		r = False
	else:
		args = json.dumps(event.get('arguments'), ensure_ascii=False)
		if not re.search('\\bprepare-experiment\\b', args) or 'upwork_project.py' not in args:
			r = False
		else:
			r = any((1 == receipt.get('upwork_experiment_plan') and receipt.get('project_root') == str(Path(root).resolve()) and (receipt.get('plan') == run.get('plan')) and (receipt.get('plan_sha256') == run.get('plan_sha256')) and (receipt.get('requirement_sha256') == run.get('requirement_sha256')) for receipt in _objects(event.get('result'))))
	return r
def _native_geolocation(event):
	from urllib.parse import urlsplit
	if not _event_actions(event) & {'read', 'inspect', 'navigate'}:
		return None
	args = event.get('arguments', {})
	targets = [value for key, value in args.items() if key.casefold() in ('url', 'target_url') and isinstance(value, str)]
	targets += re.findall('https?://[^\\s\\\'"<>]+', args.get('code', ''))
	if not any(((urlsplit(target).hostname or '').casefold() in ('ipapi.co', 'ipinfo.io', 'api.iplocation.net') for target in targets)):
		return None
	for data in _objects(event.get('result')):
		country = data.get('country_code') or data.get('country')
		if re.fullmatch('[A-Z]{2}', str(country)) and _text(data.get('ip')):
			return country
	return None
def _condition_issues(run):
	issues = []
	conditions, artifacts = (run.get('conditions', {}), _artifact_map(run))
	if not isinstance(conditions, dict):
		r = ['Experimental conditions must be an object']
	else:
		context_fields = {'session', 'egress', 'url_country', 'language', 'selected_country', 'currency', 'session_id', 'state_fingerprint'}
		try:
			request_context({key: value for key, value in conditions.items() if key in context_fields})
		except (ValueError, TypeError):
			issues.append('Invalid session/egress conditions')
		session = conditions.get('session', {})
		if isinstance(session, dict) and 'verified' == session.get('verification'):
			ids = session.get('evidence', [])
			issues += _evidence_issues(ids, artifacts, 'Verified browser mode')
			mode = session.get('mode')
			events = [e for e in _native_texts(run, ids) if 'inspect' in _event_actions(e)]
			texts = '\n'.join((json.dumps(e.get('result'), ensure_ascii=False) for e in events))
			pattern = {'incognito': '"(?:incognito|isIncognito)"\\s*:\\s*true', 'normal': '"(?:incognito|isIncognito)"\\s*:\\s*false', 'isolated': '"isolated"\\s*:\\s*true'}.get(mode)
			if not pattern or not re.search(pattern, texts.replace('\\"', '"')):
				issues.append('Browser mode needs native browser context inspection; no cookies does not prove Incognito')
		egress = conditions.get('egress', {})
		if isinstance(egress, dict) and 'verified' == egress.get('verification'):
			ids = egress.get('evidence', [])
			issues += _evidence_issues(ids, artifacts, 'Verified IP country')
			candidates = [artifacts.get(ident, {}) for ident in ids]
			if not any(('geolocation' == item.get('role') and True is item.get('geolocation_verified') and (item.get('country') == egress.get('country')) for item in candidates)):
				issues.append('IP country needs a saved same-transport geolocation measurement, not a regional URL or language')
			method = run['requirement']['method']
			if method in ('browser_scenario', 'admin', 'serp') and any(('native-browser' != item.get('transport') for item in candidates)):
				issues.append('Browser IP geography must be measured in that native browser transport; a Python HTTP client can have different proxy/egress')
		r = issues
	return r
def _run_issues(run):
	issues = requirement_issues([run.get('requirement')])
	if 1 != run.get('schema_version') or 'experiment' != run.get('kind') or run.get('status') not in STATUSES:
		issues.append('Unknown experimental run schema/status')
	if not _text(run.get('actual_result')):
		issues.append('Actual result required; executable planned code is not a performed result')
	if run.get('status') in ('unverified', 'unavailable') and (not _text(run.get('limitation'))):
		issues.append('Unverified/unavailable run needs an explicit limitation')
	if not isinstance(run.get('actual_steps'), list):
		issues.append('Actual performed steps must be a list')
	if issues:
		r = issues
	else:
		issues += _condition_issues(run)
		artifacts = _artifact_map(run)
		if len(artifacts) != len(run.get('artifacts', [])):
			issues.append('Primary artifact IDs must be unique')
		if run['status'] in ('unverified', 'unavailable'):
			r = issues
		else:
			issues += _browser_context_issues(run)
			if not artifacts:
				issues.append('A verified/refuted result needs recorded primary evidence')
			method = run['requirement']['method']
			if method in ('http', 'dom'):
				if not any((item.get('observation_kind') == method for item in artifacts.values())):
					issues.append('HTTP/DOM run requires a hash-checked collector observation of that actual kind')
			else:
				events = {e.get('id'): e for e in run.get('native_trace', {}).get('events', [])}
				if 'browser_scenario' == method:
					if not run['actual_steps']:
						issues.append('Browser interaction needs actual action steps, not only snapshots')
					for step in run['actual_steps']:
						if not isinstance(step, dict):
							issues.append('Actual step object required')
							continue
						action = step.get('action')
						event = events.get(step.get('native_event_id'), {})
						if action not in ('click', 'select', 'fill', 'press', 'navigate') or action not in _event_actions(event):
							issues.append('Actual UI action must match a successful native browser tool event')
						for phase in ('before', 'after'):
							state = step.get(phase)
							if not isinstance(state, dict):
								issues.append('Browser action needs before/after states')
								continue
							if not _text(state.get('url')) or any((key not in state for key in ('currency', 'language', 'selected_country'))):
								issues.append('Before/after states must record URL, currency, language and selected country (unknown may be null)')
							issues += _evidence_issues(state.get('evidence'), artifacts, 'Browser ' + phase)
							state_events = _native_texts(run, state.get('evidence', []))
							if not state_events:
								issues.append('Browser state must bind to actual native browser output, not an authored summary')
							elif not any((_event_actions(e) & {'read', 'inspect', 'navigate', 'click', 'select', 'press', 'fill'} for e in state_events)):
								issues.append('Browser state evidence is not a native UI measurement')
							if event:
								positions = [e.get('output_step', -1) for e in state_events]
								if 'before' == phase and (not positions or max(positions) >= event.get('step', -1)):
									issues.append('Before state must be captured before the actual native action')
								if 'after' == phase and (not positions or min(positions) < event.get('output_step', -1)):
									issues.append('After state must follow actual native action completion')
							values = [str(state[key]) for key in ('url', 'currency', 'language', 'selected_country') if None is not state.get(key)]
							raw_text = '\n'.join((json.dumps(e.get('result'), ensure_ascii=False) for e in state_events))
							if any((value not in raw_text for value in values)):
								issues.append('Declared browser state contains values absent from its raw native output')
						issues += _evidence_issues(step.get('evidence'), artifacts, 'Browser action')
				elif 'admin' == method:
					if not _text(run.get('conditions', {}).get('admin_url')) or not _text(run.get('conditions', {}).get('admin_object')):
						issues.append('Admin observation needs exact authenticated setting URL and object scope')
					if not any((_event_actions(e) & {'read', 'inspect'} and run.get('conditions', {}).get('admin_url', '') in json.dumps(e.get('result'), ensure_ascii=False) for e in events.values())):
						issues.append('Admin observation needs native browser inspection; public documentation is not store configuration')
				elif 'serp' == method:
					search = run.get('conditions', {}).get('search', {})
					if not isinstance(search, dict) or not all((_text(search.get(k)) for k in ('query', 'language', 'country'))):
						issues.append('SERP run needs exact query, search language and country conditions')
					if not any((_event_actions(e) & {'read', 'inspect'} or (e.get('name', '').casefold().split('.')[-1].split('__')[-1] in ('search_web', 'search_query', 'run') and ('search_query' in e.get('arguments', {}) or 'query' in e.get('arguments', {}))) for e in events.values() if True is e.get('successful'))):
						issues.append('SERP run needs a recorded successful native search/browser result')
				elif 'geolocation' == method:
					if 'verified' != run.get('conditions', {}).get('egress', {}).get('verification'):
						issues.append('Geolocation run needs a verified IP-country measurement')
			r = issues
	return r
def _capabilities(run):
	if run.get('status') not in ('verified', 'refuted'):
		r = []
	else:
		method, artifacts = (run['requirement']['method'], run['artifacts'])
		capabilities = set()
		for artifact in artifacts:
			capabilities.update(artifact.get('observation_capabilities', []))
		if 'browser_scenario' == method:
			capabilities.update(('content', 'dom', 'interaction'))
			if 'currency_transition' == run['requirement']['property'] and all((isinstance(step.get(phase, {}).get('currency'), str) for step in run['actual_steps'] for phase in ('before', 'after'))):
				capabilities.add('currency_transition')
		if 'admin' == method:
			capabilities.update(('content', 'admin_configuration'))
		if 'serp' == method:
			capabilities.update(('content', 'serp'))
		if 'verified' == run.get('conditions', {}).get('egress', {}).get('verification'):
			capabilities.add('ip_country')
		r = sorted(capabilities)
	return r
def _collector_artifact(root, item):
	meta = load_observation(root, item['observation'])
	source = inside(Path(root) / 'ꘖ/KB', item['observation'])
	body = source.parent / 'response.bin'
	artifact = {'id': item['id'], 'role': item.get('role', 'observation'), 'source_observation': item['observation'], 'source_observation_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'observation_kind': meta.get('kind'), 'observation_capabilities': sorted(observation_capabilities(meta)), 'source_url': meta.get('url'), 'observed_at': meta.get('observed_at')}
	if 'geolocation' == artifact['role']:
		from urllib.parse import urlsplit
		host = (urlsplit(meta.get('url', '')).hostname or '').casefold()
		if host in ('ipapi.co', 'ipinfo.io', 'api.iplocation.net') and 'content' in artifact['observation_capabilities']:
			try:
				data = json.loads(body.read_bytes())
				country = data.get('country_code') or data.get('country')
				if re.fullmatch('[A-Z]{2}', str(country)) and _text(data.get('ip')):
					artifact.update(country=country, geolocation_verified=True, transport='http-client')
			except (ValueError, TypeError, AttributeError):
				pass
	r = (artifact, body.read_bytes())
	return r
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
def record_experiment(root, specification, *, tool_trace=None):
	root = Path(root).resolve()
	if not isinstance(specification, dict):
		raise ValueError('Experimental run object required')
	run = json.loads(json.dumps(specification, ensure_ascii=False, allow_nan=False))
	if any((key in run for key in ('capabilities', 'recorded_at', 'requirement_sha256', 'evaluation'))):
		raise ValueError('Capabilities, timestamps and requirement hash are recorder-owned')
	if not _text(run.get('plan')) or not _text(run.get('plan_sha256')):
		raise ValueError('Run requires the exact preregistered plan reference and hash')
	plan = load_plan(root, run['plan'])
	if 'requirement' not in run:
		run['requirement'] = plan['requirement']
	run.update(schema_version=1, kind='experiment', recorded_at=datetime.now(timezone.utc).isoformat(timespec='microseconds'))
	issues = requirement_issues([run.get('requirement')])
	if issues:
		raise ValueError('; '.join(issues))
	run['requirement_sha256'] = digest(run['requirement'])
	raw_artifacts = run.pop('artifacts', [])
	if not isinstance(raw_artifacts, list):
		raise ValueError('Artifacts list required')
	saved, contents, native_aliases = ([], {}, [])
	for item in raw_artifacts:
		if not isinstance(item, dict) or not re.fullmatch('[A-Za-z0-9_-]{1,100}', str(item.get('id', ''))):
			raise ValueError('Artifact needs a filename-safe stable id')
		if item['id'] in contents:
			raise ValueError('Duplicate artifact id')
		if item.get('native_event_id'):
			native_aliases.append(item)
			continue
		if item.get('observation'):
			artifact, raw = _collector_artifact(root, item)
		else:
			source = inside(root, item.get('path', ''))
			if not source.is_file():
				raise ValueError('Primary artifact file required')
			raw = source.read_bytes()
			artifact = {'id': item['id'], 'role': item.get('role', 'observation'), 'source_file': source.relative_to(root).as_posix(), 'source_kind': 'imported-file'}
		artifact['sha256'] = hashlib.sha256(raw).hexdigest()
		artifact['bytes'] = len(raw)
		saved.append(artifact)
		contents[item['id']] = raw
	trace_request = tool_trace if None is not tool_trace else run.pop('native_trace', None)
	run.pop('native_trace', None)
	if trace_request:
		from .metrics import native_tool_trace
		trace = native_tool_trace(root, trace_request)
		run['native_trace'] = trace
		for event in trace['events']:
			ident = 'tool-' + re.sub('[^A-Za-z0-9_-]', '_', event['id'])
			if ident in contents:
				raise ValueError('Artifact id collides with recorder-owned native event')
			raw = _result_bytes(event['result'])
			saved.append({'id': ident, 'role': 'native-tool-output', 'native_event_id': event['id'], 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
			contents[ident] = raw
		events = {event['id']: event for event in trace['events']}
		for item in native_aliases:
			if item['id'] in contents or item['native_event_id'] not in events:
				raise ValueError('Native logical artifact needs a unique id and actual selected native event')
			event = events[item['native_event_id']]
			raw = _result_bytes(event['result'])
			saved.append({'id': item['id'], 'role': item.get('role', 'native-tool-output'), 'native_event_id': event['id'], 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
			contents[item['id']] = raw
			if 'geolocation' == item.get('role') and (country := _native_geolocation(event)):
				saved[-1].update(country=country, geolocation_verified=True, transport='native-browser')
	elif native_aliases:
		raise ValueError('Native artifact aliases require an actual selected native trace')
	run['artifacts'] = saved
	run['evaluation'] = evaluate_assertions(run, contents)
	issues = _run_issues(run) + _preregistration_issues(root, run)
	if run.get('status') in ('verified', 'refuted') and run['status'] != run['evaluation']['status']:
		issues.append('Submitted verdict contradicts preregistered raw predicates or lacks a decisive deterministic measurement')
	if issues:
		raise ValueError('; '.join(issues))
	capabilities = _capabilities(run)
	if run.get('status') in ('verified', 'refuted') and run['requirement']['property'] not in capabilities:
		issues.append('Recorded method/evidence does not establish the requested property')
	if issues:
		raise ValueError('; '.join(issues))
	run['capabilities'] = capabilities
	content_hash = digest(run)
	directory = root / 'ꘖ/KB/Evidence/Experiments' / content_hash
	directory.mkdir(parents=True, exist_ok=False)
	for artifact in saved:
		path = directory / (artifact['id'] + '.bin')
		create_bytes(path, contents[artifact['id']])
		artifact['path'] = path.relative_to(root / 'ꘖ/KB').as_posix()
	target = directory / 'experiment.json'
	create_bytes(target, json_data(run))
	r = {'experiment': target.relative_to(root / 'ꘖ/KB').as_posix(), 'experiment_sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'requirement_id': run['requirement']['id'], 'status': run['status'], 'capabilities': capabilities, 'limitation': run.get('limitation')}
	return r
def load_experiment(root, reference):
	path = inside(Path(root).resolve() / 'ꘖ/KB', reference)
	run = json.loads(path.read_text(encoding='utf-8'))
	if not path.is_relative_to(Path(root).resolve() / 'ꘖ/KB/Evidence/Experiments'):
		raise ValueError('Experiment must be a recorder-owned immutable run')
	if run.get('requirement_sha256') != digest(run.get('requirement')):
		raise ValueError('Experimental requirement changed after measurement')
	contents = {}
	for artifact in run.get('artifacts', []):
		if artifact.get('observation_kind') and (not artifact.get('source_observation')):
			raise ValueError('Observation capability label lacks its actual collector source')
		source = inside(Path(root).resolve() / 'ꘖ/KB', artifact['path'])
		if not source.is_relative_to(path.parent):
			raise ValueError('Experimental artifact escapes immutable run')
		raw = source.read_bytes()
		contents[artifact['id']] = raw
		if len(raw) != artifact.get('bytes') or hashlib.sha256(raw).hexdigest() != artifact.get('sha256'):
			raise ValueError('Primary experimental artifact differs from its saved hash/size')
		if artifact.get('source_observation'):
			expected, body = _collector_artifact(root, {'id': artifact['id'], 'role': artifact.get('role'), 'observation': artifact['source_observation']})
			if any((artifact.get(key) != value for key, value in expected.items())) or body != raw:
				raise ValueError('Experimental artifact provenance differs from its actual collector source')
		if artifact.get('geolocation_verified'):
			if artifact.get('native_event_id'):
				event = next((e for e in run.get('native_trace', {}).get('events', []) if e.get('id') == artifact['native_event_id']), {})
				if _native_geolocation(event) != artifact.get('country') or 'native-browser' != artifact.get('transport'):
					raise ValueError('Geolocation country differs from native measurement')
			elif not artifact.get('source_observation'):
				raise ValueError('Geolocation capability lacks a measured source')
	if run.get('native_trace'):
		from .metrics import native_tool_trace
		trace = run['native_trace']
		request = {key: trace[key] for key in ('surface', 'conversation_id', 'call_ids', 'step_indices', 'native_profile_home') if key in trace}
		current = native_tool_trace(root, request)
		if current['events'] != trace.get('events'):
			raise ValueError('Experimental native actions/output differ from the actual selected native events')
		events = {event['id']: event for event in trace['events']}
		for artifact in run['artifacts']:
			if artifact.get('native_event_id'):
				event = events.get(artifact['native_event_id'])
				if not event or _result_bytes(event['result']) != inside(Path(root) / 'ꘖ/KB', artifact['path']).read_bytes():
					raise ValueError('Saved native primary output differs from native authored tool result')
	unsigned = json.loads(json.dumps(run))
	for artifact in unsigned.get('artifacts', []):
		artifact.pop('path', None)
	if path.parent.name != digest(unsigned):
		raise ValueError('Immutable experimental run metadata changed')
	issues = _run_issues(run) + _preregistration_issues(root, run)
	if run.get('evaluation') != evaluate_assertions(run, contents):
		issues.append('Recorded interpretation differs from preregistered raw predicate results')
	if run.get('status') in ('verified', 'refuted') and run['status'] != run.get('evaluation', {}).get('status'):
		issues.append('Verified/refuted status contradicts the raw deterministic results')
	if issues or run.get('capabilities') != _capabilities(run):
		raise ValueError('; '.join(issues or ['Experimental capabilities differ from recorded measurements']))
	r = run
	return r
def result_issues(root, requirement, result):
	if not isinstance(result, dict):
		r = ['Property result object required']
	else:
		issues = []
		if result.get('requirement_id') != requirement.get('id') or result.get('status') not in STATUSES:
			issues.append('Property result must identify the exact requirement and valid status')
		try:
			path = inside(Path(root).resolve() / 'ꘖ/KB', result.get('experiment', ''))
			run = load_experiment(root, result.get('experiment', ''))
			if hashlib.sha256(path.read_bytes()).hexdigest() != result.get('experiment_sha256'):
				issues.append('Experimental result hash differs from immutable run')
			if run['requirement_sha256'] != digest(requirement):
				issues.append('Experimental run was performed for a different requirement version')
			if run['status'] != result.get('status'):
				issues.append('Reported result status differs from the actual recorded run')
		except (OSError, ValueError, TypeError, KeyError) as exc:
			issues.append('Experimental run is missing, invalid or changed: ' + str(exc))
		if result.get('status') in ('unverified', 'unavailable') and (not _text(result.get('limitation'))):
			issues.append('Property result needs an explicit limitation')
		r = issues
	return r
