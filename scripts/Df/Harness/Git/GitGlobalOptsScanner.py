# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.HostPathNormalizer import HostPathNormalizer
_DIR_OPTS = frozenset({'-C', '--work-tree'})
_VALUE_GLOBAL_OPTS = ('-C', '--git-dir', '--work-tree', '-c', '--exec-path', '--namespace', '--super-prefix', '--config-env')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class GitGlobalOptsScanner:
	# @used-by :meth:`Df.Harness.Git.CommitArgsParser.CommitArgsParser.parse()`
	# @used-by :meth:`Df.Harness.Git.GitReadAudit.GitReadAudit.__is_unflagged_read()`
	# @used-by :meth:`Df.Harness.Git.GitWriteAudit.GitWriteAudit.detect()`
	# @used-by :meth:`Df.Harness.Git.RepoResolver.RepoResolver.resolve()`
	# @used-by :meth:`Df.Harness.Git.ShellInspector.ShellInspector.scan_git_global_opts()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def __init__(self, argv: list[str] | tuple[str, ...], *, base_dir: Path | None=None) -> None:
		self.__tokens = list(argv)
		self.__base_dir = base_dir
	# @used-by :meth:`GitGlobalOptsScanner.__step()`
	@staticmethod
	def __advance_dir(target_dir: Path | None, raw_val: str) -> Path | None:
		r = target_dir
		if None is not target_dir:
			cand = HostPathNormalizer(raw_val).normalize()
			r = cand.resolve() if cand.is_absolute() else (target_dir / cand).resolve()
		return r
	# @used-by :meth:`GitGlobalOptsScanner.scan()`
	def __step(self, idx: int, has_flag: bool, target_dir: Path | None) -> tuple[int, bool, Path | None, int | None, bool]:
		tok = self.__tokens[idx]
		sub_idx, stop = (None, False)
		if '--' == tok:
			stop = True
		elif '--no-optional-locks' == tok:
			has_flag, idx = (True, idx + 1)
		elif tok in _DIR_OPTS and idx + 1 < len(self.__tokens):
			target_dir, idx = (self.__advance_dir(target_dir, self.__tokens[idx + 1]), idx + 2)
		elif tok in _VALUE_GLOBAL_OPTS:
			idx += 2
		elif tok.startswith('-'):
			idx += 1
		else:
			sub_idx, stop = (idx, True)
		return (idx, has_flag, target_dir, sub_idx, stop)
	# @used-by :meth:`Df.Harness.Git.CommitArgsParser.CommitArgsParser.parse()`
	# @used-by :meth:`Df.Harness.Git.GitReadAudit.GitReadAudit.__is_unflagged_read()`
	# @used-by :meth:`Df.Harness.Git.GitWriteAudit.GitWriteAudit.detect()`
	# @used-by :meth:`Df.Harness.Git.RepoResolver.RepoResolver.resolve()`
	# @used-by :meth:`Df.Harness.Git.ShellInspector.ShellInspector.scan_git_global_opts()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def scan(self) -> tuple[int | None, bool, Path | None]:
		has_flag, sub_idx, target_dir, idx = (False, None, self.__base_dir, 0)
		while idx < len(self.__tokens):
			idx, has_flag, target_dir, sub_idx, stop = self.__step(idx, has_flag, target_dir)
			if stop:
				break
		return (sub_idx, has_flag, target_dir)
