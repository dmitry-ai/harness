# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Mapping
from Df.Harness.Text.Finding import Finding
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class FieldLinter:
	# @used-by :func:`agent_tools.proposal.lint_fields()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_proposal_subsystem_roundtrip_and_fields()`
	def __init__(self, fields: Mapping[str, str], limits: Mapping[str, int], *, count_mode: str='utf16') -> None:
		self.__fields = fields
		self.__limits = limits
		self.__count_mode = count_mode
	# @used-by :func:`agent_tools.proposal.lint_fields()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_proposal_subsystem_roundtrip_and_fields()`
	def lint(self) -> list[Finding]:
		if self.__count_mode not in ('utf16', 'unicode'):
			raise ValueError('character count mode must be utf16 or unicode')
		r: list[Finding] = []
		for name, limit in self.__limits.items():
			if name not in self.__fields:
				r.append(Finding('error', 'PROPOSAL-FIELD-MISSING', 1, f'missing Upwork field {name}'))
				continue
			if not isinstance(limit, int) or isinstance(limit, bool) or 1 > limit:
				raise ValueError(f'positive integer character limit required for {name}')
			count = len(self.__fields[name].encode('utf-16-le')) // 2 if 'utf16' == self.__count_mode else len(self.__fields[name])
			if count > limit:
				r.append(Finding('error', 'PROPOSAL-FIELD-LIMIT', 1, f'{name}: {count} characters exceeds its {limit} character limit'))
		for name in self.__fields.keys() - self.__limits.keys():
			r.append(Finding('error', 'PROPOSAL-FIELD-LIMIT-MISSING', 1, f'no confirmed character limit for Upwork field {name}'))
		return r
