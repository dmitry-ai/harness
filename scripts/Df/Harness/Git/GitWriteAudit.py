# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Git.CommitArgsParser import CommitArgsParser
from Df.Harness.Git.GitGlobalOptsScanner import GitGlobalOptsScanner
from Df.Harness.Git.GitSegmentExtractor import GitSegmentExtractor
import re
_COMMIT_MSG_URL_RE = re.compile(r'^https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\d+)$')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class GitWriteAudit:
	# @used-by :meth:`Df.Harness.Git.ShellInspector.ShellInspector.prohibited_git_write_commands()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def __init__(self, text: str) -> None:
		self.__text = text
	# @used-by :meth:`GitWriteAudit.detect()`
	@staticmethod
	def __check_commit_segment(segment: str, tokens: list[str]) -> list[str]:
		_, msg, _, no_verify, all_flag, _ = CommitArgsParser(tokens).parse()
		out: list[str] = []
		clean_seg = segment.strip()
		if no_verify:
			out.append(f'git commit --no-verify/-n is prohibited ({clean_seg})')
		if all_flag:
			out.append(f'git commit -a/--all is prohibited ({clean_seg})')
		if None is not msg and ('$' not in msg):
			norm = '\n'.join((ln for ln in msg.splitlines() if not ln.startswith('#'))).strip()
			if None is _COMMIT_MSG_URL_RE.fullmatch(norm):
				out.append(f'git commit message must contain only the GitHub Issue URL ({clean_seg})')
		return out
	# @used-by :meth:`Df.Harness.Git.ShellInspector.ShellInspector.prohibited_git_write_commands()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def detect(self) -> list[str]:
		r: list[str] = []
		if isinstance(self.__text, str) and 'git' in self.__text:
			for segment, tokens in GitSegmentExtractor(self.__text).extract():
				sub_idx, _, _ = GitGlobalOptsScanner(tokens).scan()
				subcommand = tokens[sub_idx] if None is not sub_idx else None
				if 'filter-branch' == subcommand:
					r.append(f'git filter-branch is prohibited ({segment.strip()})')
				elif 'commit' == subcommand:
					r.extend(self.__check_commit_segment(segment, tokens))
		return r
