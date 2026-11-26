# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import date
from typing import Iterable
import re
DATE_TAG_RE = re.compile(r'^(?P<date>\d{4}-\d{2}-\d{2})(?:--(?P<num>[2-9]\d*|1\d+))?$')
SEMVER_TAG_RE = re.compile(r'^v?\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DateTagAllocator:
	# @used-by :func:`agent_tools.repo_tags.next_date_tag()`
	# @used-by :meth:`Df.Harness.Git.CommitTagger.CommitTagger.ensure()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__build_entry()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	def __init__(self, existing_tags: Iterable[str], day: str) -> None:
		self.__existing = list(existing_tags)
		self.__day = day
	# @used-by :func:`agent_tools.repo_tags.next_date_tag()`
	# @used-by :meth:`Df.Harness.Git.CommitTagger.CommitTagger.ensure()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__build_entry()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	def allocate(self) -> str:
		clean_day = date.fromisoformat((self.__day or '').strip()).isoformat()
		max_num = 0
		for raw in self.__existing:
			m = DATE_TAG_RE.fullmatch((raw or '').strip())
			if None is not m and clean_day == m.group('date'):
				num = 1 if None is m.group('num') else int(m.group('num'))
				if num > max_num:
					max_num = num
		return clean_day if 0 == max_num else f'{clean_day}--{max_num + 1}'
