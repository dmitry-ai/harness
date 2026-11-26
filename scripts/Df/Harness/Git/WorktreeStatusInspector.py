# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.text.trim import df_trim_text_left
from Df.Harness.Git.RepoGate import RepoGate
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class WorktreeStatusInspector:
	# @used-by :func:`agent_tools.worktree_flow.worktree_status()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	def __init__(self, repo: Path | str) -> None:
		self.__repo = Path(repo).resolve()
	# @used-by :meth:`WorktreeStatusInspector.__parse_porcelain()`
	@staticmethod
	def __apply_line(cur: dict, line: str) -> None:
		if line.startswith('worktree '):
			cur['path'] = Path(line[9:].strip()).resolve().as_posix()
		elif line.startswith('HEAD '):
			cur['head'] = line[5:].strip()
		elif line.startswith('branch '):
			cur['branch'] = str(df_trim_text_left(line[7:].strip(), 'refs/heads/'))
		elif 'detached' == line:
			cur['detached'] = True
	# @used-by :meth:`WorktreeStatusInspector.inspect()`
	@staticmethod
	def __current_branch(repo: Path) -> str:
		proc = RepoGate(repo).run_read(['rev-parse', '--abbrev-ref', 'HEAD'], check=False)
		return proc.stdout.decode('utf-8', errors='replace').strip() if 0 == proc.returncode else ''
	# @used-by :meth:`WorktreeStatusInspector.inspect()`
	def __enrich_entry(self, main_repo: Path, main_posix: str, base_ref: str, entry: dict) -> None:
		wp = Path(entry['path'])
		is_main = wp.resolve().as_posix() == main_posix
		entry['is_main'] = is_main
		if not wp.is_dir():
			entry.update(missing=True, dirty=False, ahead=0, behind=0, stale=not is_main)
		else:
			entry['dirty'] = bool(RepoGate(wp).run_read(['status', '--porcelain'], check=False).stdout.strip())
			if is_main:
				entry.update(ahead=0, behind=0, stale=False)
			else:
				ahead, behind = self.__rev_distance(main_repo, base_ref, str(entry.get('head') or ''))
				entry.update(ahead=ahead, behind=behind, stale=(not entry['dirty']) and 0 == ahead and 0 < behind)
	# @used-by :meth:`WorktreeStatusInspector.inspect()`
	def __parse_porcelain(self, text: str) -> list[dict]:
		entries: list[dict] = []
		cur: dict = {}
		for raw in (text or '').splitlines():
			line = raw.strip()
			if line:
				self.__apply_line(cur, line)
			elif cur:
				entries.append(cur)
				cur = {}
		if cur:
			entries.append(cur)
		return entries
	# @used-by :meth:`WorktreeStatusInspector.__enrich_entry()`
	@staticmethod
	def __rev_distance(main_repo: Path, base_ref: str, head_sha: str) -> tuple[int, int]:
		r = (0, 0)
		if head_sha:
			proc = RepoGate(main_repo).run_read(['rev-list', '--left-right', '--count', f'{base_ref}...{head_sha}'], check=False)
			parts = proc.stdout.decode('utf-8', errors='replace').strip().split() if 0 == proc.returncode else []
			if 2 == len(parts) and parts[0].isdigit() and parts[1].isdigit():
				r = (int(parts[1]), int(parts[0]))
		return r
	# @used-by :func:`agent_tools.worktree_flow.worktree_status()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	def inspect(self) -> dict:
		main_repo = RepoGate(self.__repo).main_repo()
		base_ref = self.__current_branch(main_repo) or 'HEAD'
		raw = RepoGate(main_repo).run_read(['worktree', 'list', '--porcelain']).stdout.decode('utf-8', errors='replace')
		entries = self.__parse_porcelain(raw)
		main_posix = main_repo.resolve().as_posix()
		for entry in entries:
			self.__enrich_entry(main_repo, main_posix, base_ref, entry)
		stale = [e['path'] for e in entries if e.get('stale')]
		behind = [e['path'] for e in entries if 0 < int(e.get('behind') or 0)]
		return {'valid': True, 'main_repo': main_repo.as_posix(), 'base_ref': base_ref, 'worktrees': entries, 'stale_worktrees': stale, 'behind_worktrees': behind}
