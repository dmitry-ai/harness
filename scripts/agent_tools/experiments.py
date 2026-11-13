# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Decompose experiments.py into ExperimentPlanStore, BrowserTraceInspector, and ExperimentRunValidator classes and unify raw_decode JSON object scanning":
# https://github.com/dmitry-ai/harness/issues/72
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
from urllib.parse import urlsplit
from .evidence import resolve_pointer
from .research import inside, json_data, load_observation, observation_capabilities, request_context
from .storage import create_bytes, iter_embedded_json_objects
STATUSES = ('verified', 'refuted', 'unverified', 'unavailable')
METHODS = ('http', 'dom', 'browser_scenario', 'admin', 'serp', 'geolocation')
OPERATORS = ('equals', 'not_equals', 'contains', 'gt', 'gte', 'lt', 'lte')
PROPERTY_METHODS = {'content': set(METHODS), 'markup': {'http', 'dom', 'browser_scenario'}, 'dom': {'dom', 'browser_scenario'}, 'interaction': {'browser_scenario'}, 'currency_transition': {'browser_scenario'}, 'ip_country': {'geolocation', 'browser_scenario'}, 'admin_configuration': {'admin'}, 'serp': {'serp'}, 'platform_capability': {'http', 'dom'}, 'causality': set(), 'business_impact': set()}
class BrowserTraceInspector:
	DIRECT_ACTIONS = {'click_browser_element': 'click', 'browser_click': 'click', 'select_browser_option': 'select', 'browser_select_option': 'select', 'browser_navigate': 'navigate', 'read_browser_dom': 'read', 'browser_screenshot': 'read', 'browser_get_state': 'inspect'}
	GEO_HOSTS = ('ipapi.co', 'ipinfo.io', 'api.iplocation.net')
	IDENTITY_ALIASES = {'browser_id': ('browser_id', 'browserId'), 'tab_id': ('tab_id', 'tabId', 'providerTabId'), 'context_id': ('context_id', 'contextId', 'browser_context_id', 'browserContextId'), 'session_id': ('session_id', 'sessionId')}
	LOCATORS = {'getByRole', 'getByText', 'getByLabel', 'getByPlaceholder', 'getByTestId', 'locator', 'nth', 'first', 'last'}
	NUMBER_RE = re.compile('-?(?:0|[1-9]\\d*)(?:\\.\\d+)?(?:[eE][+-]?\\d+)?')
	TERMINALS = {'click': 'click', 'selectOption': 'select', 'fill': 'fill', 'press': 'press', 'goto': 'navigate', 'navigate': 'navigate', 'getSnapshot': 'read', 'getDOMSnapshot': 'read', 'getAXState': 'read', 'domSnapshot': 'read', 'getState': 'inspect', 'screenshot': 'read'}
	TOKEN_RE = re.compile('\\s+|"(?:\\\\.|[^"\\\\\\r\\n])*"|\'(?:\\\\.|[^\'\\\\\\r\\n])*\'|/\\*[\\s\\S]*?\\*/|//[^\\n]*|[A-Za-z_$][\\w$]*|-?(?:0|[1-9]\\d*)(?:\\.\\d+)?(?:[eE][+-]?\\d+)?|[.(),:{}\\[\\];]')
	def __init__(self, tokens=None):
		self.tokens = list(tokens or [])
		self.index = 0
	@classmethod
	def _extract_identity_dict(cls, value):
		result, conflict = ({}, False)
		if isinstance(value, dict):
			for key, fields in cls.IDENTITY_ALIASES.items():
				values = {str(value[field]) for field in fields if isinstance(value.get(field), (str, int)) and str(value[field]).strip()}
				if 1 < len(values):
					conflict = True
					break
				if values:
					result[key] = values.pop()
		r = None if conflict else result
		return r
	@classmethod
	def _iter_identity_objects(cls, value):
		if isinstance(value, list):
			for part in value:
				yield from cls._iter_identity_objects(part)
		elif isinstance(value, str):
			parsed, ok = (None, False)
			try:
				parsed = json.loads(value)
				ok = True
			except ValueError:
				ok = False
			if ok and (not isinstance(parsed, str)):
				yield from cls._iter_identity_objects(parsed)
		elif isinstance(value, dict):
			yield value
			for key in ('metadata', 'browser_context', 'browserContext', 'state', 'result', 'value', 'content'):
				if key in value:
					yield from cls._iter_identity_objects(value[key])
			if value.get('type') in ('input_text', 'text') and isinstance(value.get('text'), str):
				yield from cls._iter_identity_objects(value['text'])
	def _parse_call_chain(self):
		self._take('await')
		receiver = self._take()
		if not re.fullmatch('[A-Za-z_$][\\w$]*', receiver):
			raise ValueError('Browser receiver required')
		self._take('.')
		method = self._take()
		if 'playwright' == method:
			self._take('.')
			method = self._take()
		action = None
		while True:
			self._take('(')
			if self.index < len(self.tokens) and ')' != self.tokens[self.index]:
				while True:
					self._parse_literal()
					if self.index < len(self.tokens) and ')' == self.tokens[self.index]:
						break
					self._take(',')
			self._take(')')
			if method in self.TERMINALS:
				action = self.TERMINALS[method]
				break
			if method not in self.LOCATORS:
				raise ValueError('Unsupported browser method')
			self._take('.')
			method = self._take()
		if self.index < len(self.tokens):
			self._take(';')
		return (receiver, action)
	def _parse_literal(self, depth=0):
		if 20 < depth:
			raise ValueError('Browser argument nesting exceeds supported grammar')
		value = self._take()
		if '[' == value:
			if self.index < len(self.tokens) and ']' == self.tokens[self.index]:
				self._take(']')
			else:
				while True:
					self._parse_literal(depth + 1)
					if self.index < len(self.tokens) and ']' == self.tokens[self.index]:
						self._take(']')
						break
					self._take(',')
		elif '{' == value:
			if self.index < len(self.tokens) and '}' == self.tokens[self.index]:
				self._take('}')
			else:
				while True:
					key = self._take()
					if not (re.fullmatch('[A-Za-z_$][\\w$]*', key) or key.startswith(('"', "'"))):
						raise ValueError('Literal object key required')
					self._take(':')
					self._parse_literal(depth + 1)
					if self.index < len(self.tokens) and '}' == self.tokens[self.index]:
						self._take('}')
						break
					self._take(',')
		elif not (value.startswith(('"', "'")) or value in ('true', 'false', 'null') or self.NUMBER_RE.fullmatch(value)):
			raise ValueError('Literal browser arguments required')
	def _take(self, expected=None):
		if self.index >= len(self.tokens) or (None is not expected and self.tokens[self.index] != expected):
			raise ValueError('Unsupported browser syntax')
		result = self.tokens[self.index]
		self.index += 1
		return result
	@classmethod
	def _tokenize(cls, code):
		tokens, position, ok = ([], 0, True)
		while position < len(code):
			match = cls.TOKEN_RE.match(code, position)
			if not match:
				ok = False
				break
			value = match.group()
			position = match.end()
			if not value.isspace() and (not value.startswith(('//', '/*'))):
				tokens.append(value)
		r = tokens if ok else None
		return r
	@classmethod
	def context_issues(cls, run, events, native_texts_fn):
		method = run['requirement']['method']
		if method not in ('browser_scenario', 'admin', 'serp'):
			r = []
		else:
			relevant = [event for event in events.values() if cls.event_actions(event)]
			if 'browser_scenario' == method:
				for step in run.get('actual_steps', []):
					if isinstance(step, dict):
						event = events.get(step.get('native_event_id'))
						if event and event not in relevant:
							relevant.append(event)
						for phase in ('before', 'after'):
							state = step.get(phase, {})
							if isinstance(state, dict):
								for ev in native_texts_fn(state.get('evidence', [])):
									if ev not in relevant:
										relevant.append(ev)
			conditions = run.get('conditions', {})
			for key in ('session', 'egress'):
				condition = conditions.get(key, {})
				if isinstance(condition, dict) and 'verified' == condition.get('verification'):
					for ev in native_texts_fn(condition.get('evidence', [])):
						if ev not in relevant:
							relevant.append(ev)
			if not relevant:
				r = [] if 'serp' == method else ['Native browser context/tab identity is unknown']
			else:
				identities = [cls.event_browser_identity(event) for event in relevant]
				if any((None is ident for ident in identities)):
					r = ['Actual native browser/context/tab identity is unknown; record unverified, not an interaction proof']
				elif any((ident != identities[0] for ident in identities[1:])):
					r = ['Native before/action/after/egress browser, context, tab or session identities differ; record unverified']
				else:
					r = []
		return r
	@classmethod
	def event_actions(cls, event):
		args = event.get('arguments') or {}
		if True is not event.get('successful') or not isinstance(args, dict):
			r = set()
		else:
			name = cls.native_tool_name(event)
			direct = next(({action} for suffix, action in cls.DIRECT_ACTIONS.items() if name == suffix or name.endswith('__' + suffix)), None)
			if None is not direct:
				r = direct
			else:
				code = args.get('code', '')
				if not (name.endswith('cua_repl__js') or name.endswith('browser__run')) or not isinstance(code, str):
					r = set()
				else:
					r = {action for _, action in cls.unconditional_calls(code)}
		return r
	@classmethod
	def event_browser_identity(cls, event):
		if not cls.event_actions(event):
			r = None
		else:
			name = cls.native_tool_name(event)
			is_script = name.endswith(('cua_repl__js', 'browser__run'))
			candidates = [] if is_script else [cls._extract_identity_dict(event.get('arguments', {}))]
			candidates += [cls._extract_identity_dict(value) for value in cls._iter_identity_objects(event.get('result'))]
			if any((None is value for value in candidates)):
				r = None
			else:
				present = [value for value in candidates if value]
				if not present:
					r = None
				else:
					merged, conflict = ({}, False)
					for candidate in present:
						for key, value in candidate.items():
							if key in merged and merged[key] != value:
								conflict = True
								break
							merged[key] = value
						if conflict:
							break
					r = merged if not conflict and all((key in merged for key in ('browser_id', 'tab_id'))) else None
		return r
	@classmethod
	def extract_verified_country(cls, data):
		if not isinstance(data, dict):
			r = None
		else:
			country = data.get('country_code') or data.get('country')
			r = country if re.fullmatch('[A-Z]{2}', str(country)) and _text(data.get('ip')) else None
		return r
	@classmethod
	def is_geo_url(cls, target):
		return isinstance(target, str) and (urlsplit(target).hostname or '').casefold() in cls.GEO_HOSTS
	@classmethod
	def native_geolocation(cls, event):
		args = event.get('arguments', {})
		if not (cls.event_actions(event) & {'read', 'inspect', 'navigate'}) or not isinstance(args, dict):
			r = None
		else:
			targets = [value for key, value in args.items() if key.casefold() in ('url', 'target_url') and isinstance(value, str)]
			targets += re.findall('https?://[^\\s\\\'"<>]+', str(args.get('code', '')))
			if not any((cls.is_geo_url(target) for target in targets)):
				r = None
			else:
				r = next((country for data in iter_embedded_json_objects(event.get('result')) if (country := cls.extract_verified_country(data))), None)
		return r
	@classmethod
	def native_tool_name(cls, event):
		name = str(event.get('name', '')).casefold().replace('.', '__')
		namespace = str(event.get('namespace') or '').casefold().replace('.', '__')
		return namespace + '__' + name if namespace and (not name.startswith(namespace + '__')) else name
	@classmethod
	def unconditional_calls(cls, code):
		tokens = cls._tokenize(code)
		if not tokens:
			r = []
		else:
			parser, calls, ok = (cls(tokens), [], True)
			try:
				while parser.index < len(parser.tokens):
					calls.append(parser._parse_call_chain())
			except (ValueError, IndexError):
				ok = False
			if not ok or 1 != len({receiver for receiver, _ in calls}) or 1 < sum((action not in ('read', 'inspect') for _, action in calls)):
				r = []
			else:
				r = calls
		return r
class ExperimentPlanStore:
	CLI_NAMES = ('harness.py', 'upwork_project.py')
	def __init__(self, root):
		self.root = Path(root).resolve()
	@staticmethod
	def _after_plan(value, prepared_at):
		try:
			observed = datetime.fromisoformat(value.replace('Z', '+00:00'))
			prepared = datetime.fromisoformat(prepared_at)
			r = None is not observed.tzinfo and observed > prepared
		except (ValueError, TypeError, AttributeError):
			r = False
		return r
	def _is_plan_commit(self, run, event):
		if True is not event.get('successful'):
			r = False
		else:
			args = json.dumps(event.get('arguments'), ensure_ascii=False)
			if not re.search('\\bprepare-experiment\\b', args) or not any((cli in args for cli in self.CLI_NAMES)):
				r = False
			else:
				r = any((1 == receipt.get('upwork_experiment_plan') and receipt.get('project_root') == str(self.root) and (receipt.get('plan') == run.get('plan')) and (receipt.get('plan_sha256') == run.get('plan_sha256')) and (receipt.get('requirement_sha256') == run.get('requirement_sha256')) for receipt in iter_embedded_json_objects(event.get('result'))))
		return r
	def load(self, reference):
		path = inside(self.root / 'ꘖ/KB', reference)
		base = self.root / 'ꘖ/KB/Evidence/Experiments/Plans'
		plan = json.loads(path.read_text(encoding='utf-8'))
		if not path.is_relative_to(base) or 'plan.json' != path.name or path.parent.name != digest(plan) or (1 != plan.get('schema_version')) or ('experiment_plan' != plan.get('kind')) or (plan.get('requirement_sha256') != digest(plan.get('requirement'))) or requirement_issues([plan.get('requirement')]):
			raise ValueError('Missing/changed immutable experimental plan')
		if plan.get('amendment_of'):
			previous = self.load(plan['amendment_of'])
			if plan.get('previous_plan_sha256') != digest(previous) or plan.get('revision') != previous['revision'] + 1:
				raise ValueError('Plan revision chain changed')
		return plan
	def prepare(self, requirement, *, amendment_of=None, amendment_reason=None):
		issues = requirement_issues([requirement])
		if issues:
			raise ValueError('; '.join(issues))
		previous = None
		if None is amendment_of:
			if amendment_reason:
				raise ValueError('Amendment reason needs the exact previous immutable plan')
		else:
			previous = self.load(amendment_of)
			if not _text(amendment_reason):
				raise ValueError('Plan amendment needs an explicit reason')
			if previous['requirement']['id'] != requirement['id']:
				raise ValueError('An amendment must preserve the experimental requirement ID')
		plan = {'schema_version': 1, 'kind': 'experiment_plan', 'prepared_at': datetime.now(timezone.utc).isoformat(timespec='microseconds'), 'requirement': requirement, 'requirement_sha256': digest(requirement), 'revision': previous['revision'] + 1 if previous else 1, 'amendment_of': amendment_of, 'amendment_reason': amendment_reason, 'previous_plan_sha256': digest(previous) if previous else None}
		directory = self.root / 'ꘖ/KB/Evidence/Experiments/Plans' / digest(plan)
		directory.mkdir(parents=True, exist_ok=False)
		path = directory / 'plan.json'
		create_bytes(path, json_data(plan))
		return {'upwork_experiment_plan': 1, 'project_root': str(self.root), 'plan': path.relative_to(self.root / 'ꘖ/KB').as_posix(), 'plan_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), **plan}
	def preregistration_issues(self, run, events=None):
		plan, early = (None, None)
		try:
			plan = self.load(run['plan'])
			path = inside(self.root / 'ꘖ/KB', run['plan'])
			if hashlib.sha256(path.read_bytes()).hexdigest() != run.get('plan_sha256'):
				early = ['Run does not bind the exact immutable plan hash']
			elif plan['requirement_sha256'] != run.get('requirement_sha256'):
				early = ['Run changed the preregistered statement, test, expected or falsifying outcomes']
		except (OSError, KeyError, ValueError, TypeError):
			early = ['Run needs a valid immutable plan committed before observations']
		if None is not early:
			r = early
		elif run.get('status') not in ('verified', 'refuted'):
			r = []
		else:
			issues = []
			observed = [item.get('observed_at') for item in run.get('artifacts', []) if item.get('source_observation')]
			event_list = list(events) if None is not events else run.get('native_trace', {}).get('events', [])
			commits = [event for event in event_list if self._is_plan_commit(run, event)]
			actions = [event for event in event_list if event not in commits]
			observed += [event.get('created_at') for event in actions]
			if not observed or any((not self._after_plan(value, plan['prepared_at']) for value in observed)):
				issues.append('Verified/refuted run requires fresh timestamped observations/actions after this exact plan; saved data cannot masquerade as a newly performed test')
			if run['requirement']['method'] in ('browser_scenario', 'admin', 'serp'):
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
			r = issues
		return r
class ExperimentRunValidator:
	CONTEXT_FIELDS = {'session', 'egress', 'url_country', 'language', 'selected_country', 'currency', 'session_id', 'state_fingerprint'}
	MODE_PATTERNS = {'incognito': '"(?:incognito|isIncognito)"\\s*:\\s*true', 'normal': '"(?:incognito|isIncognito)"\\s*:\\s*false', 'isolated': '"isolated"\\s*:\\s*true'}
	def __init__(self, root, run, contents=None):
		self.root = Path(root).resolve() if None is not root else None
		self.run = run
		self.contents = contents if None is not contents else {}
		self.artifacts = {item.get('id'): item for item in run.get('artifacts', []) if isinstance(item, dict)}
		self.event_list = list(run.get('native_trace', {}).get('events', []))
		self.events = {event.get('id'): event for event in self.event_list if isinstance(event, dict)}
	def _check_admin_run(self):
		issues = []
		conditions = self.run.get('conditions', {})
		if not _text(conditions.get('admin_url')) or not _text(conditions.get('admin_object')):
			issues.append('Admin observation needs exact authenticated setting URL and object scope')
		admin_url = conditions.get('admin_url', '')
		if not any((BrowserTraceInspector.event_actions(ev) & {'read', 'inspect'} and admin_url in json.dumps(ev.get('result'), ensure_ascii=False) for ev in self.events.values())):
			issues.append('Admin observation needs native browser inspection; public documentation is not store configuration')
		return issues
	def _check_browser_scenario_steps(self):
		issues = []
		if not self.run['actual_steps']:
			issues.append('Browser interaction needs actual action steps, not only snapshots')
		for step in self.run['actual_steps']:
			if not isinstance(step, dict):
				issues.append('Actual step object required')
				continue
			action = step.get('action')
			event = self.events.get(step.get('native_event_id'), {})
			if action not in ('click', 'select', 'fill', 'press', 'navigate') or action not in BrowserTraceInspector.event_actions(event):
				issues.append('Actual UI action must match a successful native browser tool event')
			for phase in ('before', 'after'):
				state = step.get(phase)
				if not isinstance(state, dict):
					issues.append('Browser action needs before/after states')
					continue
				if not _text(state.get('url')) or any((key not in state for key in ('currency', 'language', 'selected_country'))):
					issues.append('Before/after states must record URL, currency, language and selected country (unknown may be null)')
				issues += self._evidence_issues(state.get('evidence'), self.artifacts, 'Browser ' + phase)
				state_events = self.native_texts(state.get('evidence', []))
				if not state_events:
					issues.append('Browser state must bind to actual native browser output, not an authored summary')
				elif not any((BrowserTraceInspector.event_actions(ev) & {'read', 'inspect', 'navigate', 'click', 'select', 'press', 'fill'} for ev in state_events)):
					issues.append('Browser state evidence is not a native UI measurement')
				if event:
					positions = [ev.get('output_step', -1) for ev in state_events]
					if 'before' == phase and (not positions or max(positions) >= event.get('step', -1)):
						issues.append('Before state must be captured before the actual native action')
					if 'after' == phase and (not positions or min(positions) < event.get('output_step', -1)):
						issues.append('After state must follow actual native action completion')
				values = [str(state[key]) for key in ('url', 'currency', 'language', 'selected_country') if None is not state.get(key)]
				raw_text = '\n'.join((json.dumps(ev.get('result'), ensure_ascii=False) for ev in state_events))
				if any((value not in raw_text for value in values)):
					issues.append('Declared browser state contains values absent from its raw native output')
			issues += self._evidence_issues(step.get('evidence'), self.artifacts, 'Browser action')
		return issues
	def _check_conditions(self):
		conditions = self.run.get('conditions', {})
		if not isinstance(conditions, dict):
			r = ['Experimental conditions must be an object']
		else:
			issues = []
			try:
				request_context({key: value for key, value in conditions.items() if key in self.CONTEXT_FIELDS})
			except (ValueError, TypeError):
				issues.append('Invalid session/egress conditions')
			session = conditions.get('session', {})
			if isinstance(session, dict) and 'verified' == session.get('verification'):
				ids = session.get('evidence', [])
				issues += self._evidence_issues(ids, self.artifacts, 'Verified browser mode')
				events = [ev for ev in self.native_texts(ids) if 'inspect' in BrowserTraceInspector.event_actions(ev)]
				texts = '\n'.join((json.dumps(ev.get('result'), ensure_ascii=False) for ev in events))
				pattern = self.MODE_PATTERNS.get(session.get('mode'))
				if not pattern or not re.search(pattern, texts.replace('\\"', '"')):
					issues.append('Browser mode needs native browser context inspection; no cookies does not prove Incognito')
			egress = conditions.get('egress', {})
			if isinstance(egress, dict) and 'verified' == egress.get('verification'):
				ids = egress.get('evidence', [])
				issues += self._evidence_issues(ids, self.artifacts, 'Verified IP country')
				candidates = [self.artifacts.get(ident, {}) for ident in ids]
				if not any(('geolocation' == item.get('role') and True is item.get('geolocation_verified') and (item.get('country') == egress.get('country')) for item in candidates)):
					issues.append('IP country needs a saved same-transport geolocation measurement, not a regional URL or language')
				if self.run['requirement']['method'] in ('browser_scenario', 'admin', 'serp') and any(('native-browser' != item.get('transport') for item in candidates)):
					issues.append('Browser IP geography must be measured in that native browser transport; a Python HTTP client can have different proxy/egress')
			r = issues
		return r
	def _check_geolocation_run(self):
		return ['Geolocation run needs a verified IP-country measurement'] if 'verified' != self.run.get('conditions', {}).get('egress', {}).get('verification') else []
	def _check_run_header(self):
		issues = requirement_issues([self.run.get('requirement')])
		if 1 != self.run.get('schema_version') or 'experiment' != self.run.get('kind') or self.run.get('status') not in STATUSES:
			issues.append('Unknown experimental run schema/status')
		if not _text(self.run.get('actual_result')):
			issues.append('Actual result required; executable planned code is not a performed result')
		if self.run.get('status') in ('unverified', 'unavailable') and (not _text(self.run.get('limitation'))):
			issues.append('Unverified/unavailable run needs an explicit limitation')
		if not isinstance(self.run.get('actual_steps'), list):
			issues.append('Actual performed steps must be a list')
		return issues
	def _check_serp_run(self):
		issues = []
		search = self.run.get('conditions', {}).get('search', {})
		if not isinstance(search, dict) or not all((_text(search.get(k)) for k in ('query', 'language', 'country'))):
			issues.append('SERP run needs exact query, search language and country conditions')
		if not any((BrowserTraceInspector.event_actions(ev) & {'read', 'inspect'} or (ev.get('name', '').casefold().split('.')[-1].split('__')[-1] in ('search_web', 'search_query', 'run') and ('search_query' in ev.get('arguments', {}) or 'query' in ev.get('arguments', {}))) for ev in self.events.values() if True is ev.get('successful'))):
			issues.append('SERP run needs a recorded successful native search/browser result')
		return issues
	@classmethod
	def _collector_artifact(cls, root, item):
		meta = load_observation(root, item['observation'])
		source = inside(Path(root) / 'ꘖ/KB', item['observation'])
		raw = (source.parent / 'response.bin').read_bytes()
		artifact = {'id': item['id'], 'role': item.get('role', 'observation'), 'source_observation': item['observation'], 'source_observation_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'observation_kind': meta.get('kind'), 'observation_capabilities': sorted(observation_capabilities(meta)), 'source_url': meta.get('url'), 'observed_at': meta.get('observed_at')}
		if 'geolocation' == artifact['role'] and BrowserTraceInspector.is_geo_url(meta.get('url', '')) and ('content' in artifact['observation_capabilities']):
			try:
				country = BrowserTraceInspector.extract_verified_country(json.loads(raw))
				if country:
					artifact.update(country=country, geolocation_verified=True, transport='http-client')
			except (ValueError, TypeError, AttributeError):
				pass
		return (artifact, raw)
	@staticmethod
	def _evidence_issues(ids, artifacts, label):
		return [label + ': recorded primary artifact IDs required'] if not isinstance(ids, list) or not ids or any((not isinstance(x, str) or x not in artifacts for x in ids)) else []
	@classmethod
	def _ingest_artifacts_and_trace(cls, root, run, raw_artifacts, trace_request):
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
				artifact, raw = cls._collector_artifact(root, item)
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
		if not trace_request:
			if native_aliases:
				raise ValueError('Native artifact aliases require an actual selected native trace')
		else:
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
				if 'geolocation' == item.get('role') and (country := BrowserTraceInspector.native_geolocation(event)):
					saved[-1].update(country=country, geolocation_verified=True, transport='native-browser')
		run['artifacts'] = saved
		return (saved, contents)
	def _verify_saved_artifacts(self, path):
		for artifact in self.run.get('artifacts', []):
			if artifact.get('observation_kind') and (not artifact.get('source_observation')):
				raise ValueError('Observation capability label lacks its actual collector source')
			source = inside(self.root / 'ꘖ/KB', artifact['path'])
			if not source.is_relative_to(path.parent):
				raise ValueError('Experimental artifact escapes immutable run')
			raw = source.read_bytes()
			self.contents[artifact['id']] = raw
			if len(raw) != artifact.get('bytes') or hashlib.sha256(raw).hexdigest() != artifact.get('sha256'):
				raise ValueError('Primary experimental artifact differs from its saved hash/size')
			if artifact.get('source_observation'):
				expected, body = self._collector_artifact(self.root, {'id': artifact['id'], 'role': artifact.get('role'), 'observation': artifact['source_observation']})
				if any((artifact.get(key) != value for key, value in expected.items())) or body != raw:
					raise ValueError('Experimental artifact provenance differs from its actual collector source')
			if artifact.get('geolocation_verified'):
				if not artifact.get('native_event_id'):
					if not artifact.get('source_observation'):
						raise ValueError('Geolocation capability lacks a measured source')
				else:
					event = self.events.get(artifact['native_event_id'], {})
					if BrowserTraceInspector.native_geolocation(event) != artifact.get('country') or 'native-browser' != artifact.get('transport'):
						raise ValueError('Geolocation country differs from native measurement')
		if self.run.get('native_trace'):
			from .metrics import native_tool_trace
			trace = self.run['native_trace']
			request = {key: trace[key] for key in ('surface', 'conversation_id', 'call_ids', 'step_indices', 'native_profile_home') if key in trace}
			current = native_tool_trace(self.root, request)
			if current['events'] != trace.get('events'):
				raise ValueError('Experimental native actions/output differ from the actual selected native events')
			for artifact in self.run['artifacts']:
				if artifact.get('native_event_id'):
					event = self.events.get(artifact['native_event_id'])
					if not event or _result_bytes(event['result']) != self.contents[artifact['id']]:
						raise ValueError('Saved native primary output differs from native authored tool result')
	def capabilities(self):
		if self.run.get('status') not in ('verified', 'refuted'):
			r = []
		else:
			method = self.run['requirement']['method']
			found = set()
			for artifact in self.run['artifacts']:
				found.update(artifact.get('observation_capabilities', []))
			if 'browser_scenario' == method:
				found.update(('content', 'dom', 'interaction'))
				if 'currency_transition' == self.run['requirement']['property'] and all((isinstance(step.get(phase, {}).get('currency'), str) for step in self.run['actual_steps'] for phase in ('before', 'after'))):
					found.add('currency_transition')
			if 'admin' == method:
				found.update(('content', 'admin_configuration'))
			if 'serp' == method:
				found.update(('content', 'serp'))
			if 'verified' == self.run.get('conditions', {}).get('egress', {}).get('verification'):
				found.add('ip_country')
			r = sorted(found)
		return r
	def evaluate_assertions(self):
		assertions = self.run['requirement'].get('assertions', [])
		results = []
		for assertion in assertions:
			matches = [item for item in self.artifacts.values() if item.get('id') == assertion['artifact_id']] if assertion.get('artifact_id') else [item for item in self.artifacts.values() if item.get('role') == assertion.get('artifact_role')]
			result = {'assertion_id': assertion['id'], 'status': 'unverified'}
			try:
				if 1 != len(matches):
					raise ValueError('Assertion must select exactly one primary artifact')
				artifact = matches[0]
				method = self.run['requirement']['method']
				primary = artifact.get('observation_kind') == method and bool(artifact.get('source_observation'))
				if artifact.get('native_event_id'):
					event = self.events.get(artifact['native_event_id'], {})
					primary = bool(BrowserTraceInspector.event_actions(event)) and None is not BrowserTraceInspector.event_browser_identity(event) if method in ('browser_scenario', 'admin', 'geolocation') else 'serp' == method and True is event.get('successful')
				if 'geolocation' == method and True is artifact.get('geolocation_verified'):
					primary = True
				if not primary:
					raise ValueError('Assertion does not select an authentic primary measurement of this method')
				actual = _select_raw(self.contents[artifact['id']], assertion['locator'])
				positive = _compare(actual, assertion['operator'], assertion['expected'])
				disconfirming = assertion['disconfirming']
				negative = _compare(actual, disconfirming['operator'], disconfirming['expected'])
				result.update(artifact_id=artifact['id'], artifact_sha256=artifact['sha256'], positive=positive, disconfirming=negative, selected_value_sha256=digest(actual), status='verified' if positive and (not negative) else 'refuted' if negative and (not positive) else 'unverified')
			except (ValueError, TypeError, KeyError, IndexError, UnicodeError) as exc:
				result['reason'] = type(exc).__name__ + ': missing, ambiguous or unparsable primary measurement'
			results.append(result)
		statuses = {item['status'] for item in results}
		status = 'refuted' if 'refuted' in statuses else 'unverified' if not results or 'unverified' in statuses else 'verified'
		return {'status': status, 'assertions': results, 'interpretation': 'Restricted predicates establish only the preregistered raw property; A.A checks semantic entailment and alternative explanations'}
	@classmethod
	def load(cls, root, reference):
		resolved = Path(root).resolve()
		path = inside(resolved / 'ꘖ/KB', reference)
		run = json.loads(path.read_text(encoding='utf-8'))
		if not path.is_relative_to(resolved / 'ꘖ/KB/Evidence/Experiments'):
			raise ValueError('Experiment must be a recorder-owned immutable run')
		if run.get('requirement_sha256') != digest(run.get('requirement')):
			raise ValueError('Experimental requirement changed after measurement')
		validator = cls(resolved, run)
		validator._verify_saved_artifacts(path)
		unsigned = json.loads(json.dumps(run))
		for artifact in unsigned.get('artifacts', []):
			artifact.pop('path', None)
		if path.parent.name != digest(unsigned):
			raise ValueError('Immutable experimental run metadata changed')
		issues = validator.run_issues() + ExperimentPlanStore(resolved).preregistration_issues(run, validator.event_list)
		if run.get('evaluation') != validator.evaluate_assertions():
			issues.append('Recorded interpretation differs from preregistered raw predicate results')
		if run.get('status') in ('verified', 'refuted') and run['status'] != run.get('evaluation', {}).get('status'):
			issues.append('Verified/refuted status contradicts the raw deterministic results')
		if issues or run.get('capabilities') != validator.capabilities():
			raise ValueError('; '.join(issues or ['Experimental capabilities differ from recorded measurements']))
		return run
	def native_texts(self, ids):
		return [self.events[nid] for ident in ids if isinstance(ident, str) and (nid := self.artifacts.get(ident, {}).get('native_event_id')) in self.events]
	@classmethod
	def record(cls, root, specification, *, tool_trace=None):
		resolved = Path(root).resolve()
		if not isinstance(specification, dict):
			raise ValueError('Experimental run object required')
		run = json.loads(json.dumps(specification, ensure_ascii=False, allow_nan=False))
		if any((key in run for key in ('capabilities', 'recorded_at', 'requirement_sha256', 'evaluation'))):
			raise ValueError('Capabilities, timestamps and requirement hash are recorder-owned')
		if not _text(run.get('plan')) or not _text(run.get('plan_sha256')):
			raise ValueError('Run requires the exact preregistered plan reference and hash')
		store = ExperimentPlanStore(resolved)
		plan = store.load(run['plan'])
		if 'requirement' not in run:
			run['requirement'] = plan['requirement']
		run.update(schema_version=1, kind='experiment', recorded_at=datetime.now(timezone.utc).isoformat(timespec='microseconds'))
		issues = requirement_issues([run.get('requirement')])
		if issues:
			raise ValueError('; '.join(issues))
		run['requirement_sha256'] = digest(run['requirement'])
		raw_artifacts = run.pop('artifacts', [])
		trace_request = tool_trace if None is not tool_trace else run.pop('native_trace', None)
		run.pop('native_trace', None)
		saved, contents = cls._ingest_artifacts_and_trace(resolved, run, raw_artifacts, trace_request)
		validator = cls(resolved, run, contents)
		run['evaluation'] = validator.evaluate_assertions()
		issues = validator.run_issues() + store.preregistration_issues(run, validator.event_list)
		if run.get('status') in ('verified', 'refuted') and run['status'] != run['evaluation']['status']:
			issues.append('Submitted verdict contradicts preregistered raw predicates or lacks a decisive deterministic measurement')
		if issues:
			raise ValueError('; '.join(issues))
		capabilities = validator.capabilities()
		if run.get('status') in ('verified', 'refuted') and run['requirement']['property'] not in capabilities:
			raise ValueError('Recorded method/evidence does not establish the requested property')
		run['capabilities'] = capabilities
		directory = resolved / 'ꘖ/KB/Evidence/Experiments' / digest(run)
		directory.mkdir(parents=True, exist_ok=False)
		for artifact in saved:
			path = directory / (artifact['id'] + '.bin')
			create_bytes(path, contents[artifact['id']])
			artifact['path'] = path.relative_to(resolved / 'ꘖ/KB').as_posix()
		target = directory / 'experiment.json'
		create_bytes(target, json_data(run))
		return {'experiment': target.relative_to(resolved / 'ꘖ/KB').as_posix(), 'experiment_sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'requirement_id': run['requirement']['id'], 'status': run['status'], 'capabilities': capabilities, 'limitation': run.get('limitation')}
	def run_issues(self):
		issues = self._check_run_header()
		if not issues:
			issues += self._check_conditions()
			if len(self.artifacts) != len(self.run.get('artifacts', [])):
				issues.append('Primary artifact IDs must be unique')
			if self.run['status'] not in ('unverified', 'unavailable'):
				issues += BrowserTraceInspector.context_issues(self.run, self.events, self.native_texts)
				if not self.artifacts:
					issues.append('A verified/refuted result needs recorded primary evidence')
				method = self.run['requirement']['method']
				if method in ('http', 'dom'):
					if not any((item.get('observation_kind') == method for item in self.artifacts.values())):
						issues.append('HTTP/DOM run requires a hash-checked collector observation of that actual kind')
				elif 'geolocation' == method:
					issues += self._check_geolocation_run()
				elif 'admin' == method:
					issues += self._check_admin_run()
				elif 'serp' == method:
					issues += self._check_serp_run()
				elif 'browser_scenario' == method:
					issues += self._check_browser_scenario_steps()
		return issues
def _compare(actual, operator, expected):
	if 'contains' == operator:
		if not isinstance(actual, str) or not isinstance(expected, str):
			raise ValueError('contains needs text')
		r = expected in actual
	elif operator not in ('equals', 'not_equals'):
		if type(actual) not in (int, float) or type(expected) not in (int, float):
			raise ValueError('Numeric comparison needs JSON numbers')
		r = {'gt': lambda: actual > expected, 'gte': lambda: actual >= expected, 'lt': lambda: actual < expected, 'lte': lambda: actual <= expected}[operator]()
	else:
		equal = type(actual) is type(expected) and actual == expected
		if type(actual) in (int, float) and type(expected) in (int, float):
			equal = actual == expected
		r = equal if 'equals' == operator else not equal
	return r
def _event_actions(event):
	return BrowserTraceInspector.event_actions(event)
def _event_browser_identity(event):
	return BrowserTraceInspector.event_browser_identity(event)
def _invalid_constant(value):
	raise ValueError('Non-finite JSON number')
def _result_bytes(value):
	return value.encode('utf-8') if isinstance(value, str) else json_data(value)
def _select_raw(raw, locator):
	if 'text' != locator['type']:
		r = resolve_pointer(json.loads(raw, parse_constant=_invalid_constant), locator['value'], decode_uri=False)
	else:
		text = raw.decode('utf-8')
		if locator['value'] and locator['value'] not in text:
			raise ValueError('Text locator absent')
		r = locator['value'] or text
	return r
def _text(value):
	return isinstance(value, str) and bool(value.strip())
def digest(value):
	return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
def evaluate_assertions(run, contents):
	return ExperimentRunValidator(None, run, contents).evaluate_assertions()
def load_experiment(root, reference):
	return ExperimentRunValidator.load(root, reference)
def load_plan(root, reference):
	return ExperimentPlanStore(root).load(reference)
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
def prepare_experiment(root, requirement, *, amendment_of=None, amendment_reason=None):
	return ExperimentPlanStore(root).prepare(requirement, amendment_of=amendment_of, amendment_reason=amendment_reason)
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
def record_experiment(root, specification, *, tool_trace=None):
	return ExperimentRunValidator.record(root, specification, tool_trace=tool_trace)
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
