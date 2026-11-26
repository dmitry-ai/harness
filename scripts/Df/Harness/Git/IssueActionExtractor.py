# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
import re
_BRACE_RE = re.compile(r'(?m)^[ \t]*\{')
_RAN_TESTS_RE = re.compile(r'(?m)^Ran \d+ tests? in \d')
_SHOWING_RE = re.compile(r'(?m)^Showing lines \d+-\d+ of \d+\b')
_TEMP_CONSUMED_RE = re.compile(r'(?i)"consumed_files"\s*:\s*\[\s*"[^"]*(?:[/\\]temp[/\\]|[/\\]tmp[/\\])')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class IssueActionExtractor:
	# @used-by :meth:`Df.Harness.Git.ShellInspector.ShellInspector.extract_issue_actions()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def __init__(self, outputs: list[str] | tuple[str, ...]) -> None:
		self.__outputs = outputs or ()
	# @used-by :meth:`IssueActionExtractor.extract()`
	@staticmethod
	def __decode_text(text: str, decoder: json.JSONDecoder) -> list[dict]:
		from agent_tools.issues.batch_commands import extract_actions_from_decoded_obj
		out: list[dict] = []
		pos = 0
		while True:
			m_brace = _BRACE_RE.search(text[pos:])
			if None is m_brace:
				break
			raw_start = text.find('{', pos + m_brace.start())
			try:
				obj, end_idx = decoder.raw_decode(text, raw_start)
			except ValueError:
				pos = raw_start + 1
				continue
			nl_idx = text.find('\n', end_idx)
			tail = text[end_idx:] if -1 == nl_idx else text[end_idx:nl_idx]
			pos = end_idx
			if (not tail.strip()) and isinstance(obj, dict):
				out.extend(extract_actions_from_decoded_obj(obj))
		return out
	# @used-by :meth:`IssueActionExtractor.extract()`
	@staticmethod
	def __is_eligible_text(text: object) -> bool:
		return isinstance(text, str) and '"action"' in text and '"repo"' in text and (not _RAN_TESTS_RE.search(text)) and (not _SHOWING_RE.search(text)) and (not _TEMP_CONSUMED_RE.search(text))
	# @used-by :meth:`Df.Harness.Git.ShellInspector.ShellInspector.extract_issue_actions()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def extract(self) -> list[dict]:
		decoder = json.JSONDecoder()
		r: list[dict] = []
		for text in self.__outputs:
			if self.__is_eligible_text(text):
				r.extend(self.__decode_text(text, decoder))
		return r
