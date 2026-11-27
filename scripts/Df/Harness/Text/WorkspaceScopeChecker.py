# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Text.MechanicalProjector import MechanicalProjector
from Df.Harness.lib.text_sections import dfh_scope_blocks
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class WorkspaceScopeChecker:
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.scope_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_workspace_integrity_and_review_classes()`
	def __init__(self, op: dict, base, candidate: str) -> None:
		self.__op = op
		self.__base = base.decode('utf-8') if isinstance(base, (bytes, bytearray)) else base
		self.__candidate = candidate
	# @used-by :meth:`WorkspaceScopeChecker.check()`
	@staticmethod
	def __permitted_sections(allowed: list[str], names: list[str], issues: list[dict]) -> set[str]:
		permit: set[str] = set()
		for name in allowed:
			if name in names:
				permit.update((key for key in names if key == name or key.startswith(name + '.')))
			elif 1 != name.count('-'):
				issues.append({'code': 'text.allow', 'message': 'Unknown allowed section: ' + name})
			else:
				first, last = name.split('-')
				if first not in names or last not in names or names.index(first) > names.index(last):
					issues.append({'code': 'text.allow', 'message': 'Invalid allowed section range: ' + name})
				else:
					chosen = names[names.index(first):names.index(last) + 1]
					permit.update((key for key in names if any((key == node or key.startswith(node + '.') for node in chosen))))
		return permit
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.scope_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_workspace_integrity_and_review_classes()`
	def check(self) -> list[dict]:
		r: list[dict] = []
		if 'inspect' == self.__op['mode'] and self.__candidate != self.__base:
			r.append({'code': 'text.inspect_write', 'message': 'Inspect cannot change the document'})
		if self.__op['changes'] in ('links', 'renumber') and MechanicalProjector(self.__base, self.__op['kind'], self.__op['changes']).project() != MechanicalProjector(self.__candidate, self.__op['kind'], self.__op['changes']).project():
			r.append({'code': 'text.scope', 'message': 'Candidate changes content outside the declared mechanical operation'})
		allowed = self.__op.get('allow_sections', [])
		if allowed:
			before = dfh_scope_blocks(self.__base, self.__op['kind'])
			after = {b['section']: b['text'] for b in dfh_scope_blocks(self.__candidate, self.__op['kind'])}
			names = [b['section'] for b in before]
			permit = self.__permitted_sections(allowed, names, r)
			for block in before:
				if block['section'] not in permit and after.get(block['section']) != block['text']:
					r.append({'code': 'text.outside_scope', 'message': 'Changed or removed section outside scope: ' + block['section']})
			for name in set(after) - set(names):
				if name not in permit and (not any((name.startswith(parent + '.') for parent in permit))):
					r.append({'code': 'text.outside_scope', 'message': 'Added section outside scope: ' + name})
		return r
