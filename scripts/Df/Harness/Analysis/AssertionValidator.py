# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class AssertionValidator:
	# @used-by :func:`agent_tools.schema_help.requirement_assertion_issues()`
	# @used-by :meth:`Df.Harness.Experiment.RequirementValidator.RequirementValidator.__check_one()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_schema_help_classes()`
	def __init__(self, label: str, requirement: dict, operators: tuple[str, ...]) -> None:
		self.__label = label
		self.__requirement = requirement
		self.__operators = operators
	# @used-by :meth:`AssertionValidator.issues()`
	def __check_one(self, item, seen_ids: set[str], out: list[str]) -> None:
		if not isinstance(item, dict):
			out.append(self.__label + ': deterministic assertion object required')
		else:
			aid = item.get('id')
			if not isinstance(aid, str) or not aid.strip() or aid in seen_ids:
				out.append(self.__label + ': assertion needs a unique id')
			if isinstance(aid, str):
				seen_ids.add(aid)
			has_id = isinstance(item.get('artifact_id'), str) and bool(item['artifact_id'].strip())
			has_role = isinstance(item.get('artifact_role'), str) and bool(item['artifact_role'].strip())
			if has_id == has_role:
				out.append(self.__label + ': assertion prebinds exactly one logical artifact ID or role')
			if not self.__valid_locator(item.get('locator')):
				out.append(self.__label + ': assertion needs an exact JSON pointer or text locator')
			if not (self.__valid_comparison(item) and self.__valid_comparison(item.get('disconfirming'))):
				out.append(self.__label + ': explicit positive and disconfirming deterministic comparisons required')
	# @used-by :meth:`AssertionValidator.__check_one()`
	def __valid_comparison(self, cmp_obj) -> bool:
		return isinstance(cmp_obj, dict) and cmp_obj.get('operator') in self.__operators and ('expected' in cmp_obj) and (not isinstance(cmp_obj.get('expected'), (dict, list)))
	# @used-by :meth:`AssertionValidator.__check_one()`
	def __valid_locator(self, loc) -> bool:
		r = False
		if isinstance(loc, dict) and loc.get('type') in ('json_pointer', 'text') and isinstance(loc.get('value'), str):
			r = ('json_pointer' != loc.get('type')) or (not loc['value']) or loc['value'].startswith('/')
		return r
	# @used-by :func:`agent_tools.schema_help.requirement_assertion_issues()`
	# @used-by :meth:`Df.Harness.Experiment.RequirementValidator.RequirementValidator.__check_one()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_schema_help_classes()`
	def issues(self) -> list[str]:
		out: list[str] = []
		assertions = self.__requirement.get('assertions', [])
		if not isinstance(assertions, list):
			out.append(self.__label + ': assertions must be a list')
		else:
			seen_ids: set[str] = set()
			for item in assertions:
				self.__check_one(item, seen_ids, out)
		return out