# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.git import df_git_root
from Df.Harness.Git.CommitTagger import CommitTagger
from Df.Harness.Git.RepoGate import RepoGate
from agent_tools.issues.repo_locator import origin_repo_slug
import re
_LINE_FRAG_RE = re.compile(r'^L(\d+)(?:-L?(\d+))?$')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class BlobUrlBuilder:
	# @used-by :func:`agent_tools.repo_tags.build_github_blob_url()`
	# @used-by :func:`agent_tools.repo_tags.validate_tree_path_and_fragment()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	def __init__(self, file_path: Path | str, *, commit: str='HEAD', lines: str | None=None, anchor: str | None=None, push: bool=False, date_override: str | None=None) -> None:
		self.__target = Path(file_path).resolve()
		self.__commit = commit
		self.__frag = (lines or anchor or '').strip().lstrip('#')
		self.__push = push
		self.__date_override = date_override
	# @used-by :meth:`BlobUrlBuilder.__validate_tree_path()`
	@staticmethod
	def __validate_blob_fragment(repo: Path, ref: str, rel_path: str, fragment: str) -> int:
		proc = RepoGate(repo).run_read(['-c', 'core.quotepath=false', 'show', f'{ref}:{rel_path}'], check=False)
		if 0 != proc.returncode:
			raise ValueError(f'Path "{rel_path}" is missing at tag "{ref}" in {repo}')
		total = max(1, len(proc.stdout.decode('utf-8', errors='replace').splitlines()))
		m_ln = _LINE_FRAG_RE.fullmatch(fragment) if fragment else None
		if None is not m_ln:
			start, end = (int(m_ln.group(1)), int(m_ln.group(2) or m_ln.group(1)))
			if 1 > start or start > end or end > total:
				raise ValueError(f'Line anchor #{fragment} out of bounds (1..{total}) for {rel_path} at {ref}')
		return total
	# @used-by :meth:`BlobUrlBuilder.build()`
	def __validate_tree_path(self, repo: Path, ref: str, rel_path: str) -> tuple[str, int]:
		proc = RepoGate(repo).run_read(['-c', 'core.quotepath=false', 'cat-file', '-t', f'{ref}:{rel_path}'], check=False)
		if 0 != proc.returncode:
			raise ValueError(f'Path "{rel_path}" does not exist at tag "{ref}" in {repo}')
		obj_type = proc.stdout.decode('utf-8', errors='replace').strip()
		if 'tree' == obj_type and self.__frag:
			raise ValueError(f'Directory link cannot carry fragment #{self.__frag}: {rel_path}')
		total = self.__validate_blob_fragment(repo, ref, rel_path, self.__frag) if 'blob' == obj_type else 0
		return (obj_type, total)
	# @used-by :func:`agent_tools.repo_tags.build_github_blob_url()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	def build(self) -> str:
		raw_root = df_git_root(self.__target)
		repo_root = raw_root.resolve() if None is not raw_root else None
		if None is repo_root:
			raise ValueError(f'Path is not inside a Git repository: {self.__target}')
		slug = origin_repo_slug(repo_root)
		if not slug:
			raise ValueError(f'Repository has no GitHub remote slug: {repo_root}')
		rel_path = self.__target.relative_to(repo_root).as_posix()
		if (not rel_path) or '.' == rel_path:
			raise ValueError(f'Target must be a file or subdirectory inside {repo_root}')
		tag = CommitTagger(repo_root, commit=self.__commit, date_override=self.__date_override, push=self.__push).ensure()['tag']
		obj_type, _ = self.__validate_tree_path(repo_root, tag, rel_path)
		kind = 'tree' if 'tree' == obj_type else 'blob'
		return f'https://github.com/{slug}/{kind}/{tag}/{rel_path}' + (f'#{self.__frag}' if self.__frag else '')
