# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Analysis.RedFlagValidator import FLAGS
STATUSES = {'confirmed': 'confirmed', 'suspected': 'hypothesis', 'unresolved': 'unresolved from available data'}
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RedFlagRenderer:
	# @used-by :func:`agent_tools.red_flags.render_red_flags()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__build_block()`
	# @used-by :meth:`Df.Harness.Analysis.Renderer.Renderer.render()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	def __init__(self, value: dict, *, project_card: bool=False, analysis_rel: str='\ua616/KB/Analysis.json') -> None:
		self.__value = value
		self.__project_card = project_card
		self.__analysis_rel = analysis_rel
	# @used-by :func:`agent_tools.red_flags.render_red_flags()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__build_block()`
	# @used-by :meth:`Df.Harness.Analysis.Renderer.Renderer.render()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	def render(self) -> str:
		flags = self.__value.get('red_flags', [])
		if not flags:
			r = ''
		else:
			by_id = {flag['id']: flag for flag in flags}
			lines = [f'# Red Flags \u2014 {len(flags)}', '']
			if 2 == len(by_id):
				qualifier = ' (intermediation is currently a hypothesis)' if 'suspected' == by_id['RF-CLIENT-INTERMEDIARY']['status'] else ''
				lines += [f'**Both Red Flags simultaneously{qualifier}: high likelihood of declining the project.**', '']
			pointers = {claim['id']: f'{self.__analysis_rel}#/identity/{index}' for index, claim in enumerate(self.__value['identity'])}
			for ident in FLAGS:
				if ident in by_id:
					flag = by_id[ident]
					lines += [f"- **{FLAGS[ident][0]}.** Status: {STATUSES[flag['status']]}.", '  ' + flag['summary'].strip().replace('\n', '\n  '), '  Basis: ' + ', '.join((f"[{ref}](<{(pointers[ref] if self.__project_card else '#' + ref.lower())}>)" for ref in flag['basis_ids'])) + '.', '']
			r = '\n'.join(lines) + '\n'
		return r