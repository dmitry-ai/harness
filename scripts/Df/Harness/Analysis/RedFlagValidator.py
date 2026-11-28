# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Project.Diagnostics import Diagnostics
# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
CARD_HEADINGS = {'RF-CLIENT-INTERMEDIARY': '\u041f\u043e\u0441\u0440\u0435\u0434\u043d\u0438\u043a', 'RF-WEBSITE-UNIDENTIFIED': '\u0421\u0430\u0439\u0442 \u043d\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d'}
FLAGS = {'RF-CLIENT-INTERMEDIARY': ('Client is an intermediary', ('confirmed', 'suspected')), 'RF-WEBSITE-UNIDENTIFIED': ('Target website is unidentified', ('unresolved',))}
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RedFlagValidator:
	# @used-by :func:`agent_tools.red_flags.red_flag_issues()`
	# @used-by :meth:`Df.Harness.Analysis.Validator.Validator.issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	def __init__(self, value: dict, claims: dict) -> None:
		self.__value = value
		self.__claims = claims
	# @used-by :meth:`RedFlagValidator.issues()`
	def __check_flag(self, index: int, flag, seen: set[str], out: list[dict]) -> None:
		field = f'/red_flags/{index}'
		if not isinstance(flag, dict):
			out.append(Diagnostics().problem('red_flags.object', field, 'A red flag must be an object'))
		else:
			ident = flag.get('id')
			if not isinstance(ident, str) or ident not in FLAGS or ident in seen:
				out.append(Diagnostics().problem('red_flags.id', field + '/id', 'Unknown or duplicate red flag ID'))
			else:
				seen.add(ident)
				if flag.get('status') not in FLAGS[ident][1]:
					out.append(Diagnostics().problem('red_flags.status', field + '/status', 'Use the status allowed for this flag'))
			if not isinstance(flag.get('summary'), str) or not flag['summary'].strip():
				out.append(Diagnostics().problem('red_flags.summary', field + '/summary', 'Explain this project-specific risk'))
			refs = flag.get('basis_ids')
			if not isinstance(refs, list) or not refs or any((not isinstance(ref, str) or 'identity' != self.__claims.get(ref) for ref in refs)):
				out.append(Diagnostics().problem('red_flags.basis', field + '/basis_ids', 'Reference existing identity claims with evidence'))
	# @used-by :func:`agent_tools.red_flags.red_flag_issues()`
	# @used-by :meth:`Df.Harness.Analysis.Validator.Validator.issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	def issues(self) -> list[dict]:
		if 'red_flags' not in self.__value:
			r: list[dict] = []
		else:
			flags = self.__value['red_flags']
			if not isinstance(flags, list):
				r = [Diagnostics().problem('red_flags.list', '/red_flags', 'red_flags must be a list')]
			else:
				out: list[dict] = []
				seen: set[str] = set()
				for idx, flag in enumerate(flags):
					self.__check_flag(idx, flag, seen, out)
				r = out
		return r