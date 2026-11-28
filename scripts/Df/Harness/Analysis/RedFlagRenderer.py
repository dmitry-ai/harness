# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
from Df.Harness.Analysis.RedFlagValidator import CARD_HEADINGS, FLAGS
RU_STATUSES = {'confirmed': '\u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u043e', 'suspected': '\u0433\u0438\u043f\u043e\u0442\u0435\u0437\u0430', 'unresolved': '\u043d\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u043e \u043f\u043e \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u043c \u0434\u0430\u043d\u043d\u044b\u043c'}
STATUSES = {'confirmed': 'confirmed', 'suspected': 'hypothesis', 'unresolved': 'unresolved from available data'}
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RedFlagRenderer:
	# @used-by :func:`agent_tools.red_flags.render_red_flags()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__build_section()`
	# @used-by :meth:`Df.Harness.Analysis.Renderer.Renderer.render()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	def __init__(self, value: dict, *, project_card: bool=False, analysis_rel: str='\ua616/KB/Analysis.json') -> None:
		self.__value = value
		self.__project_card = project_card
		self.__analysis_rel = analysis_rel
	# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
	# @used-by :meth:`RedFlagRenderer.render()`
	def __combo_warning(self, by_id: dict) -> list[str]:
		suspected = 'suspected' == by_id['RF-CLIENT-INTERMEDIARY']['status']
		if self.__project_card:
			qual = ' (\u043f\u043e\u0441\u0440\u0435\u0434\u043d\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u043f\u043e\u043a\u0430 \u044f\u0432\u043b\u044f\u0435\u0442\u0441\u044f \u0433\u0438\u043f\u043e\u0442\u0435\u0437\u043e\u0439)' if suspected else ''
			r = [f'**\u041e\u0431\u0430 Red Flags \u043e\u0434\u043d\u043e\u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e{qual}: \u0432\u044b\u0441\u043e\u043a\u0430\u044f \u0432\u0435\u0440\u043e\u044f\u0442\u043d\u043e\u0441\u0442\u044c \u043e\u0442\u043a\u0430\u0437\u0430 \u043e\u0442 \u043f\u0440\u043e\u0435\u043a\u0442\u0430.**  ']
		else:
			qual = ' (intermediation is currently a hypothesis)' if suspected else ''
			r = [f'**Both Red Flags simultaneously{qual}: high likelihood of declining the project.**  ']
		return r
	# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
	# @used-by :meth:`RedFlagRenderer.render()`
	def __render_flag(self, ident: str, flag: dict, pointers: dict[str, str]) -> list[str]:
		heading = CARD_HEADINGS[ident] if self.__project_card else FLAGS[ident][0]
		status_lbl = '\u0421\u0442\u0430\u0442\u0443\u0441' if self.__project_card else 'Status'
		status_val = RU_STATUSES[flag['status']] if self.__project_card else STATUSES[flag['status']]
		basis_lbl = '\u041e\u0441\u043d\u043e\u0432\u0430\u043d\u0438\u0435' if self.__project_card else 'Basis'
		refs = ', '.join((f"[{(ref)}](<{(pointers[ref] if self.__project_card else '#' + ref.lower())}>)" for ref in flag['basis_ids']))
		summary = '  \n'.join((ln.rstrip() for ln in flag['summary'].strip().splitlines()))
		return [f'## {heading}', f'{status_lbl}: {status_val}.  ', f'{summary}  ', f'{basis_lbl}: {refs}.  ']
	# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
	# @used-by :func:`agent_tools.red_flags.render_red_flags()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__build_section()`
	# @used-by :meth:`Df.Harness.Analysis.Renderer.Renderer.render()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	def render(self) -> str:
		flags = self.__value.get('red_flags', [])
		if not flags:
			r = ''
		else:
			by_id = {flag['id']: flag for flag in flags}
			lines = ['# Red Flags']
			if 2 == len(by_id):
				lines.extend(self.__combo_warning(by_id))
			pointers = {claim['id']: f'{self.__analysis_rel}#/identity/{index}' for index, claim in enumerate(self.__value['identity'])}
			for ident in FLAGS:
				if ident in by_id:
					lines.extend(self.__render_flag(ident, by_id[ident], pointers))
			r = '\n'.join(lines) + '\n'
		return r