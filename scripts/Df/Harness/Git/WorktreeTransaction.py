# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.worktree import dfh_prepare_worktrees_base_dir
import shutil
import subprocess
import uuid
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class WorktreeTransaction:
	# @used-by :func:`agent_tools.git_gate.commit_in_worktree()`
	# @used-by :func:`agent_tools.git_gate.create_isolated_worktree()`
	# @used-by :func:`agent_tools.git_gate.remove_isolated_worktree()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.commit()`
	# @used-by :meth:`test_worktree_ignore.WorktreeIgnoreInvariantTests.test_worktree_commit_transaction_create_protects_enclosing_repo()`
	def __init__(self, gate, *, label: str='commit') -> None:
		self.gate = gate
		self.label = label
	# @used-by :meth:`WorktreeTransaction.commit()`
	def __commit_in_wt(self, wt_dir: Path, rel_paths: list[str], message: str, has_head: bool) -> None:
		from Df.Harness.Git.RepoGate import RepoGate
		specs = self.__stage_into_worktree(wt_dir, rel_paths)
		wt_gate = RepoGate(wt_dir, strict=True)
		wt_gate.git('add', '-A', '--', *specs)
		wt_gate.check_commit(rel_paths, message=message)
		old_head = self.gate.git('rev-parse', 'HEAD').decode('utf-8').strip() if has_head else None
		wt_gate.git('commit', '--only', '-m', message, '--', *specs)
		new_head = wt_gate.git('rev-parse', 'HEAD').decode('utf-8').strip()
		self.__update_main_head(new_head, old_head, message, specs)
	# @used-by :meth:`WorktreeTransaction.__commit_in_wt()`
	def __stage_into_worktree(self, wt_dir: Path, rel_paths: list[str]) -> list[str]:
		for rel in rel_paths:
			src, dst = (self.gate.root / rel, wt_dir / rel)
			if not src.exists():
				if dst.exists():
					dst.unlink()
			else:
				dst.parent.mkdir(parents=True, exist_ok=True)
				shutil.copy2(src, dst)
		return [f':(literal){p}' for p in rel_paths]
	# @used-by :meth:`WorktreeTransaction.__commit_in_wt()`
	def __update_main_head(self, new_head: str, old_head: str | None, message: str, specs: list[str]) -> None:
		reflog = f'commit (worktree): {message.strip()}'
		if not old_head:
			self.gate.git('update-ref', '-m', reflog, 'HEAD', new_head)
		else:
			self.gate.git('update-ref', '-m', reflog, 'HEAD', new_head, old_head)
		self.gate.git('reset', '-q', 'HEAD', '--', *specs)
	# @used-by :func:`agent_tools.git_gate.commit_in_worktree()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.commit()`
	def commit(self, paths: list[str], message: str) -> list[str]:
		self.gate.assert_toplevel()
		if not message.strip():
			raise ValueError('Empty commit message')
		self.gate.ensure_hooks()
		r = self.gate.normalize_paths(paths)
		has_head = 0 == self.gate.run_read(['rev-parse', '--verify', 'HEAD'], check=False).returncode
		wt_dir = self.create()
		try:
			self.__commit_in_wt(wt_dir, r, message, has_head)
		finally:
			self.remove(wt_dir)
		return r
	# @used-by :func:`agent_tools.git_gate.create_isolated_worktree()`
	# @used-by :meth:`WorktreeTransaction.commit()`
	# @used-by :meth:`test_worktree_ignore.WorktreeIgnoreInvariantTests.test_worktree_commit_transaction_create_protects_enclosing_repo()`
	def create(self) -> Path:
		base, _ = dfh_prepare_worktrees_base_dir(self.gate.root)
		r = base / f'{self.label}-{uuid.uuid4().hex[:10]}'
		self.gate.git('worktree', 'add', '--detach', str(r), 'HEAD')
		return r
	# @used-by :func:`agent_tools.git_gate.remove_isolated_worktree()`
	# @used-by :meth:`WorktreeTransaction.commit()`
	# @used-by :meth:`test_worktree_ignore.WorktreeIgnoreInvariantTests.test_worktree_commit_transaction_create_protects_enclosing_repo()`
	def remove(self, wt_dir: Path) -> None:
		resolved_wt = Path(wt_dir).resolve()
		try:
			self.gate.git('worktree', 'remove', '--force', str(resolved_wt))
		finally:
			if resolved_wt.exists():
				shutil.rmtree(resolved_wt, ignore_errors=True)
			subprocess.run(['git', '-C', str(self.gate.root), 'worktree', 'prune'], stdin=subprocess.DEVNULL, capture_output=True, check=False, timeout=60, creationflags=_NO_WINDOW)
