# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import date
from typing import Iterable
from Df.Core.lib.array.first import df_first
from Df.Harness.Git.DateTagAllocator import DATE_TAG_RE, SEMVER_TAG_RE
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class TagSelector:
	# @used-by :func:`agent_tools.repo_tags.pick_preferred_tag()`
	# @used-by :meth:`Df.Harness.Git.CommitTagger.CommitTagger.ensure()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__build_entry()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_git.DfHarnessS11Wave2CCovGitTests.test_git_read_audit_unquote_and_tag_selector()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def __init__(self, tags: Iterable[str]) -> None:
		self.__tags = [t.strip() for t in tags if t and t.strip()]
	# @used-by :meth:`TagSelector.__is_valid_repo()`
	# @used-by :meth:`TagSelector.pick()`
	@staticmethod
	def __is_valid_date(tag: str) -> bool:
		m = DATE_TAG_RE.fullmatch(tag)
		if None is m:
			r = False
		else:
			try:
				date.fromisoformat(m.group('date'))
				r = True
			except ValueError:
				r = False
		return r
	# @used-by :meth:`TagSelector.pick()`
	def __is_valid_repo(self, tag: str) -> bool:
		return self.__is_valid_date(tag) or bool(SEMVER_TAG_RE.fullmatch(tag))
	# @used-by :func:`agent_tools.repo_tags.pick_preferred_tag()`
	# @used-by :meth:`Df.Harness.Git.CommitTagger.CommitTagger.ensure()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__build_entry()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_git.DfHarnessS11Wave2CCovGitTests.test_git_read_audit_unquote_and_tag_selector()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def pick(self) -> str | None:
		date_tags = sorted((t for t in self.__tags if self.__is_valid_date(t)))
		if date_tags:
			r: str | None = date_tags[0]
		else:
			r = df_first(sorted((t for t in self.__tags if self.__is_valid_repo(t))))
		return r
