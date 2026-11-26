# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
DIRECT_ACTIONS = {'click_browser_element': 'click', 'browser_click': 'click', 'select_browser_option': 'select', 'browser_select_option': 'select', 'browser_navigate': 'navigate', 'read_browser_dom': 'read', 'browser_screenshot': 'read', 'browser_get_state': 'inspect'}
LOCATORS = {'getByRole', 'getByText', 'getByLabel', 'getByPlaceholder', 'getByTestId', 'locator', 'nth', 'first', 'last'}
NUMBER_RE = re.compile('-?(?:0|[1-9]\\d*)(?:\\.\\d+)?(?:[eE][+-]?\\d+)?')
TERMINALS = {'click': 'click', 'selectOption': 'select', 'fill': 'fill', 'press': 'press', 'goto': 'navigate', 'navigate': 'navigate', 'getSnapshot': 'read', 'getDOMSnapshot': 'read', 'getAXState': 'read', 'domSnapshot': 'read', 'getState': 'inspect', 'screenshot': 'read'}
TOKEN_RE = re.compile('\\s+|"(?:\\\\.|[^"\\\\\\r\\n])*"|\'(?:\\\\.|[^\'\\\\\\r\\n])*\'|/\\*[\\s\\S]*?\\*/|//[^\\n]*|[A-Za-z_$][\\w$]*|-?(?:0|[1-9]\\d*)(?:\\.\\d+)?(?:[eE][+-]?\\d+)?|[.(),:{}\\[\\];]')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class CallChainParser:
	# @used-by :meth:`CallChainParser.event_actions()`
	# @used-by :meth:`Df.Harness.Experiment.TraceInspector.TraceInspector.unconditional_calls()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	def __init__(self, code: str) -> None:
		self.__code = code
		self.__tokens: list[str] = []
		self.__index = 0
	# @used-by :meth:`CallChainParser.__walk_chain()`
	def __parse_args(self) -> None:
		self.__take('(')
		if self.__index < len(self.__tokens) and ')' != self.__tokens[self.__index]:
			while True:
				self.__parse_literal()
				if self.__index < len(self.__tokens) and ')' == self.__tokens[self.__index]:
					break
				self.__take(',')
		self.__take(')')
	# @used-by :meth:`CallChainParser.__parse_literal()`
	def __parse_array(self, depth: int) -> None:
		if self.__index < len(self.__tokens) and ']' == self.__tokens[self.__index]:
			self.__take(']')
		else:
			while True:
				self.__parse_literal(depth + 1)
				if self.__index < len(self.__tokens) and ']' == self.__tokens[self.__index]:
					self.__take(']')
					break
				self.__take(',')
	# @used-by :meth:`CallChainParser.parse_calls()`
	def __parse_call_chain(self) -> tuple[str, str]:
		self.__take('await')
		receiver = self.__take()
		if not re.fullmatch('[A-Za-z_$][\\w$]*', receiver):
			raise ValueError('Browser receiver required')
		self.__take('.')
		method = self.__take()
		if 'playwright' == method:
			self.__take('.')
			method = self.__take()
		action = self.__walk_chain(method)
		if self.__index < len(self.__tokens):
			self.__take(';')
		return (receiver, action)
	# @used-by :meth:`CallChainParser.__parse_args()`
	# @used-by :meth:`CallChainParser.__parse_array()`
	# @used-by :meth:`CallChainParser.__parse_object()`
	def __parse_literal(self, depth: int=0) -> None:
		if 20 < depth:
			raise ValueError('Browser argument nesting exceeds supported grammar')
		value = self.__take()
		if '[' == value:
			self.__parse_array(depth)
		elif '{' == value:
			self.__parse_object(depth)
		elif not (value.startswith(('"', "'")) or value in ('true', 'false', 'null') or NUMBER_RE.fullmatch(value)):
			raise ValueError('Literal browser arguments required')
	# @used-by :meth:`CallChainParser.__parse_literal()`
	def __parse_object(self, depth: int) -> None:
		if self.__index < len(self.__tokens) and '}' == self.__tokens[self.__index]:
			self.__take('}')
		else:
			while True:
				key = self.__take()
				if not (re.fullmatch('[A-Za-z_$][\\w$]*', key) or key.startswith(('"', "'"))):
					raise ValueError('Literal object key required')
				self.__take(':')
				self.__parse_literal(depth + 1)
				if self.__index < len(self.__tokens) and '}' == self.__tokens[self.__index]:
					self.__take('}')
					break
				self.__take(',')
	# @used-by :meth:`CallChainParser.__parse_args()`
	# @used-by :meth:`CallChainParser.__parse_array()`
	# @used-by :meth:`CallChainParser.__parse_call_chain()`
	# @used-by :meth:`CallChainParser.__parse_literal()`
	# @used-by :meth:`CallChainParser.__parse_object()`
	# @used-by :meth:`CallChainParser.__walk_chain()`
	def __take(self, expected: str | None=None) -> str:
		if self.__index >= len(self.__tokens) or (None is not expected and self.__tokens[self.__index] != expected):
			raise ValueError('Unsupported browser syntax')
		r = self.__tokens[self.__index]
		self.__index += 1
		return r
	# @used-by :meth:`CallChainParser.parse_calls()`
	@staticmethod
	def __tokenize(code: str) -> list[str] | None:
		tokens, position, ok = ([], 0, True)
		while position < len(code):
			match = TOKEN_RE.match(code, position)
			if not match:
				ok = False
				break
			value = match.group()
			position = match.end()
			if not value.isspace() and (not value.startswith(('//', '/*'))):
				tokens.append(value)
		return tokens if ok else None
	# @used-by :meth:`CallChainParser.__parse_call_chain()`
	def __walk_chain(self, method: str) -> str:
		action = ''
		while True:
			self.__parse_args()
			if method in TERMINALS:
				action = TERMINALS[method]
				break
			if method not in LOCATORS:
				raise ValueError('Unsupported browser method')
			self.__take('.')
			method = self.__take()
		return action
	# @used-by :meth:`Df.Harness.Experiment.AssertionEvaluator.AssertionEvaluator.__is_primary()`
	# @used-by :meth:`Df.Harness.Experiment.BrowserIdentityExtractor.BrowserIdentityExtractor.extract_identity()`
	# @used-by :meth:`Df.Harness.Experiment.BrowserStepAuditor.BrowserStepAuditor.__check_phase()`
	# @used-by :meth:`Df.Harness.Experiment.BrowserStepAuditor.BrowserStepAuditor.__check_step()`
	# @used-by :meth:`Df.Harness.Experiment.ConditionAuditor.ConditionAuditor.__check_session()`
	# @used-by :meth:`Df.Harness.Experiment.NativeGeoExtractor.NativeGeoExtractor.extract_country()`
	# @used-by :meth:`Df.Harness.Experiment.RunAuditor.RunAuditor.__check_admin()`
	# @used-by :meth:`Df.Harness.Experiment.RunAuditor.RunAuditor.__check_serp()`
	# @used-by :meth:`Df.Harness.Experiment.TraceContextAuditor.TraceContextAuditor.__collect_relevant()`
	# @used-by :meth:`Df.Harness.Experiment.TraceInspector.TraceInspector.event_actions()`
	@classmethod
	def event_actions(cls, event: dict) -> set[str]:
		args = event.get('arguments') or {}
		if True is not event.get('successful') or not isinstance(args, dict):
			r: set[str] = set()
		else:
			name = cls.native_tool_name(event)
			direct = next(({action} for suffix, action in DIRECT_ACTIONS.items() if name == suffix or name.endswith('__' + suffix)), None)
			if None is not direct:
				r = direct
			else:
				code = args.get('code', '')
				if not (name.endswith('cua_repl__js') or name.endswith('browser__run')) or not isinstance(code, str):
					r = set()
				else:
					r = {action for _, action in cls(code).parse_calls()}
		return r
	# @used-by :meth:`CallChainParser.event_actions()`
	# @used-by :meth:`Df.Harness.Experiment.BrowserIdentityExtractor.BrowserIdentityExtractor.extract_identity()`
	# @used-by :meth:`Df.Harness.Experiment.TraceInspector.TraceInspector.native_tool_name()`
	@staticmethod
	def native_tool_name(event: dict) -> str:
		name = str(event.get('name', '')).casefold().replace('.', '__')
		namespace = str(event.get('namespace') or '').casefold().replace('.', '__')
		return namespace + '__' + name if namespace and (not name.startswith(namespace + '__')) else name
	# @used-by :meth:`Df.Harness.Experiment.TraceInspector.TraceInspector.unconditional_calls()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	def parse_calls(self) -> list[tuple[str, str]]:
		tokens = self.__tokenize(self.__code)
		if not tokens:
			r: list[tuple[str, str]] = []
		else:
			self.__tokens, self.__index = (tokens, 0)
			calls, ok = ([], True)
			try:
				while self.__index < len(self.__tokens):
					calls.append(self.__parse_call_chain())
			except (ValueError, IndexError):
				ok = False
			if not ok or 1 != len({receiver for receiver, _ in calls}) or 1 < sum((action not in ('read', 'inspect') for _, action in calls)):
				r = []
			else:
				r = calls
		return r
