# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Git.GitGlobalOptsScanner import GitGlobalOptsScanner
from Df.Harness.Git.GitSegmentExtractor import GitSegmentExtractor
import re
_ARGV_LIST_RE = re.compile(r'[\[\(]\s*([\'"](?:[^\'"]*?[\\/])?git(?:\.exe)?[\'"](?:\s*,\s*[^\]\)]+)+)[\]\)]')
_BRAIN_SCRATCH_RE = re.compile(r'[\\/]\.gemini[\\/]antigravity[\\/]brain[\\/][^\\/]+[\\/]scratch[\\/]', re.I)
_EXEC_CMD_RE = re.compile(r'\bcmd\s*:\s*("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`)')
_LIT_RE = re.compile(r'[\'"]([^\'"]*)[\'"]')
_OPT_LOCKS_RE = re.compile(r'(?:\$env:)?GIT_OPTIONAL_LOCKS\s*=\s*["\']?0["\']?')
READ_SUBCOMMANDS = ('status', 'diff', 'log', 'rev-parse', 'show', 'ls-files')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class GitReadAudit:
	# @used-by :meth:`Df.Harness.Git.ShellInspector.ShellInspector.unflagged_git_read_commands()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_git.DfHarnessS11Wave2CCovGitTests.test_git_read_audit_unquote_and_tag_selector()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def __init__(self, text: str) -> None:
		self.__text = text
	# @used-by :meth:`GitReadAudit.__scan_argv_lists()`
	# @used-by :meth:`GitReadAudit.__scan_shell_candidates()`
	@staticmethod
	def __is_unflagged_read(tokens: list[str]) -> bool:
		sub_idx, has_flag, _ = GitGlobalOptsScanner(tokens).scan()
		subcommand = tokens[sub_idx] if None is not sub_idx else None
		return subcommand in READ_SUBCOMMANDS and (not has_flag)
	# @used-by :meth:`GitReadAudit.detect()`
	def __scan_argv_lists(self, out: list[str]) -> None:
		for match in _ARGV_LIST_RE.finditer(self.__text):
			raw_items = [part.strip() for part in match.group(1).split(',')]
			parsed = [lit.group(1) if (lit := _LIT_RE.fullmatch(item)) else '<expr>' for item in raw_items[1:]]
			if self.__is_unflagged_read(parsed):
				snippet = ' '.join(match.group(0).split())
				if snippet not in out:
					out.append(snippet)
	# @used-by :meth:`GitReadAudit.detect()`
	def __scan_shell_candidates(self, out: list[str]) -> None:
		exec_cmds = [raw[1:-1] if raw.startswith('`') else self.__unquote(raw) for cm in _EXEC_CMD_RE.finditer(self.__text) for raw in (cm.group(1),)] if 'exec_command' in self.__text else []
		for candidate in exec_cmds or [self.__text]:
			if not _OPT_LOCKS_RE.search(candidate):
				for segment, tokens in GitSegmentExtractor(candidate).extract():
					if self.__is_unflagged_read(tokens):
						normalized = ' '.join(segment.strip().split())
						if normalized not in out:
							out.append(normalized)
	# @used-by :meth:`GitReadAudit.__scan_shell_candidates()`
	@staticmethod
	def __unquote(token: str) -> str:
		if not (2 <= len(token) and token[0] == token[-1] and token[0] in ('"', "'")):
			r = token
		else:
			r = token[1:-1].replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
		return r
	# @used-by :meth:`Df.Harness.Git.ShellInspector.ShellInspector.unflagged_git_read_commands()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_git.DfHarnessS11Wave2CCovGitTests.test_git_read_audit_unquote_and_tag_selector()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def detect(self) -> list[str]:
		r: list[str] = []
		if isinstance(self.__text, str) and 'git' in self.__text and (not _BRAIN_SCRATCH_RE.search(self.__text)):
			self.__scan_argv_lists(r)
			self.__scan_shell_candidates(r)
		return r
