# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Git.GitGlobalOptsScanner import GitGlobalOptsScanner
_SKIP_TWO_OPTS = frozenset({'-c', '-C', '--reuse-message', '--reedit-message', '--fixup', '--squash', '--author', '--date', '--cleanup', '-u', '--untracked-files', '-S', '--gpg-sign'})
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class CommitArgsParser:
	# @used-by :meth:`Df.Harness.Git.GitWriteAudit.GitWriteAudit.__check_commit_segment()`
	# @used-by :meth:`Df.Harness.Git.PushValidator.PushValidator.__verify_commit()`
	# @used-by :meth:`Df.Harness.Git.ShellInspector.ShellInspector.parse_commit_subcommand_args()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def __init__(self, argv: list[str] | tuple[str, ...]) -> None:
		self.__tokens = list(argv)
	# @used-by :meth:`CommitArgsParser.__consume_token()`
	@staticmethod
	def __consume_msg_or_file(tok: str, rest: list[str], idx: int, st: dict) -> int:
		step = 0
		if tok in ('-m', '--message') and idx + 1 < len(rest):
			st['msg_parts'].append(rest[idx + 1])
			step = 2
		elif tok.startswith('--message='):
			st['msg_parts'].append(tok.split('=', 1)[1])
			step = 1
		elif tok.startswith('-m') and 2 < len(tok):
			st['msg_parts'].append(tok[2:])
			step = 1
		elif tok in ('-F', '--file') and idx + 1 < len(rest):
			st['msg_file'] = rest[idx + 1]
			step = 2
		elif tok.startswith('--file='):
			st['msg_file'] = tok.split('=', 1)[1]
			step = 1
		return step
	# @used-by :meth:`CommitArgsParser.parse()`
	def __consume_token(self, rest: list[str], idx: int, st: dict) -> int:
		tok = rest[idx]
		mf_step = self.__consume_msg_or_file(tok, rest, idx, st)
		if 0 < mf_step:
			r = idx + mf_step
		elif tok in ('--no-verify', '--all'):
			st['no_verify'] = st['no_verify'] or '--no-verify' == tok
			st['all_flag'] = st['all_flag'] or '--all' == tok
			r = idx + 1
		elif tok in _SKIP_TWO_OPTS:
			r = idx + 2
		elif tok.startswith('--') or (not tok.startswith('-')):
			if not tok.startswith('-'):
				st['pathspecs'].append(tok)
			r = idx + 1
		else:
			r, b_nv, b_all = self.__parse_flag_bundle(tok[1:], rest, idx, st['msg_parts'])
			st['no_verify'], st['all_flag'] = (st['no_verify'] or b_nv, st['all_flag'] or b_all)
		return r
	# @used-by :meth:`CommitArgsParser.__consume_token()`
	@staticmethod
	def __parse_flag_bundle(flags: str, rest: list[str], idx: int, msg_parts: list[str]) -> tuple[int, bool, bool]:
		no_verify, all_flag = ('n' in flags, 'a' in flags)
		if 'm' not in flags:
			next_idx = idx + 1
		else:
			rem = flags[flags.index('m') + 1:]
			if not rem and idx + 1 >= len(rest):
				next_idx = idx + 1
			elif rem:
				msg_parts.append(rem)
				next_idx = idx + 1
			else:
				msg_parts.append(rest[idx + 1])
				next_idx = idx + 2
		return (next_idx, no_verify, all_flag)
	# @used-by :meth:`Df.Harness.Git.GitWriteAudit.GitWriteAudit.__check_commit_segment()`
	# @used-by :meth:`Df.Harness.Git.PushValidator.PushValidator.__verify_commit()`
	# @used-by :meth:`Df.Harness.Git.ShellInspector.ShellInspector.parse_commit_subcommand_args()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def parse(self) -> tuple[list[str], str | None, str | None, bool, bool, list[str]]:
		sub_idx, _, _ = GitGlobalOptsScanner(self.__tokens).scan()
		if None is sub_idx or 'commit' != self.__tokens[sub_idx]:
			r: tuple[list[str], str | None, str | None, bool, bool, list[str]] = ([], None, None, False, False, [])
		else:
			rest = self.__tokens[sub_idx + 1:]
			st: dict = {'msg_parts': [], 'msg_file': None, 'no_verify': False, 'all_flag': False, 'pathspecs': []}
			idx, after_dd = (0, False)
			while idx < len(rest):
				if after_dd:
					st['pathspecs'].append(rest[idx])
					idx += 1
				elif '--' == rest[idx]:
					after_dd, idx = (True, idx + 1)
				else:
					idx = self.__consume_token(rest, idx, st)
			r = (rest, '\n\n'.join(st['msg_parts']) if st['msg_parts'] else None, st['msg_file'], st['no_verify'], st['all_flag'], st['pathspecs'])
		return r
