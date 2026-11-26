# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Analysis.RedFlagRenderer import RedFlagRenderer
from Df.Harness.Analysis.Validator import SECTIONS, Validator
from Df.Harness.Project.IssueValidator import IssueValidator
TITLES = ('Client Identification', 'Client Concerns', 'Possible Misconceptions', 'Causes of the Problem in This Client System', 'Solution Methods')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class Renderer:
	# @used-by :func:`agent_tools.analysis.render_analysis()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_analysis_merger_and_lifecycle_classes()`
	def __init__(self, value: dict) -> None:
		self.__value = value
	# @used-by :meth:`Renderer.__render_side()`
	def __render_arg(self, arg: dict, markdown_link) -> list[str]:
		if 3 == self.__value.get('schema_version') and (arg.get('claim_id') or arg.get('evidence_id')):
			target = arg.get('claim_id') or arg['evidence_id']
			r = [arg['argument'], f'[Basis: {target}](#{target.lower()})', '']
		else:
			source = Validator.source_uri(arg, self.__value.get('sources', {}))
			r = [arg['argument'], '> ' + arg['quote'].replace('\n', '\n> '), markdown_link('Source', source), '']
			if arg.get('anchor_exception'):
				loc = arg['anchor_exception']
				r.extend([f"Section: {loc['section']}.", markdown_link('Address verification', loc['observation']), ''])
		return r
	# @used-by :meth:`Renderer.__render_claim_contract()`
	def __render_claim_extras(self, claim: dict) -> list[str]:
		lines: list[str] = []
		for missing in claim['missing_checks']:
			lines.extend(['Missing check: ' + missing, ''])
		if claim.get('alternative_explanations'):
			lines.extend(['Alternatives: ' + '; '.join(claim['alternative_explanations']) + '.', claim['discriminating_check'], ''])
		if claim.get('applicability'):
			lines.extend(['Applicability conditions: ' + '; '.join(claim['applicability']) + '.', 'Result validation: ' + claim['validation'], ''])
		lines.extend(['Impact: ' + claim['impact']['severity'] + '. ' + claim['impact']['basis'], ''])
		if claim.get('calculation'):
			calc = claim['calculation']
			lines.extend([f"Calculation: `{calc['formula']}`; old={calc['operands']['old']['value']} {calc['operands']['old']['unit']}; new={calc['operands']['new']['value']} {calc['operands']['new']['unit']}; result {calc['result']}%; rounding {calc['rounding']} to {calc['rounding_places']} places.", ''])
		return lines
	# @used-by :meth:`Renderer.__render_item()`
	# @used-by :meth:`Renderer.render()`
	def __render_claim_contract(self, claim: dict, markdown_link) -> list[str]:
		lines = [f"Kind: {claim['knowledge_type']}. Verification status: {claim['verification_status']}.", 'Scope: ' + claim['scope']['description'], '']
		if claim['scope']['sample']:
			lines.extend(['Verified objects: ' + '; '.join(claim['scope']['sample']) + '.', ''])
		for limitation in claim['scope']['limitations']:
			lines.extend(['Limitation: ' + limitation, ''])
		for dep in claim['derived_from']:
			lines.extend([f"Dependency: [{dep['claim_id']}](#{dep['claim_id'].lower()}), version `{dep['sha256']}`.", ''])
		for ref in claim['evidence']:
			lines.extend([f"### {ref['id']}", '> ' + ref['quote'].replace('\n', '\n> '), markdown_link('Primary source', ref['source']), f"Locator: {ref['locator']['type']}: {ref['locator']['value']}. SHA-256: `{ref['source_sha256']}`.", ''])
			if ref.get('anchor_exception'):
				exc = ref['anchor_exception']
				lines.extend(['Documentation section: ' + exc['section'] + '.', markdown_link('Saved anchor-absence verification', exc['observation']), ''])
		lines.extend(self.__render_claim_extras(claim))
		return lines
	# @used-by :meth:`Renderer.__render_section()`
	def __render_item(self, key: str, item: dict, markdown_link) -> list[str]:
		lines = [f"## {item['id']}", item['essence'], '']
		if 3 == self.__value.get('schema_version'):
			lines.extend(self.__render_claim_contract(item, markdown_link))
		if item.get('addresses'):
			lines.extend(['Addresses: ' + ', '.join((f'[{i}](#{i.lower()})' for i in item['addresses'])) + '.', ''])
		for side, label in (('for', 'For'), ('against', 'Against')):
			lines.extend(self.__render_side(item, side, label, markdown_link))
		if 'methods' == key:
			lines.append(f"Score: {item['score_percent']}% ({item['criterion']}).")
		else:
			lines.append(f"Expert plausibility: {item['probability_percent']}%.")
		lines.extend([item['assessment_basis'], ''])
		return lines
	# @used-by :meth:`Renderer.render()`
	def __render_section(self, number: int, key: str, title: str, markdown_link) -> list[str]:
		lines = [f'# {number}. {title}', '']
		if not self.__value[key]:
			lines.extend([self.__value['notes'][key], ''])
		for item in self.__value[key]:
			lines.extend(self.__render_item(key, item, markdown_link))
		return lines
	# @used-by :meth:`Renderer.__render_item()`
	def __render_side(self, item: dict, side: str, label: str, markdown_link) -> list[str]:
		lines = [f'### {label}']
		for arg in item[side]:
			lines.extend(self.__render_arg(arg, markdown_link))
		if 'against' == side and (not item[side]):
			gap = item['counterevidence']
			lines.extend([f"Counterevidence status: {gap['status']}.", gap['limitations'], ''])
			lines.extend((markdown_link('Reviewed source', x) for x in gap['reviewed_sources']))
			lines.append('')
		return lines
	# @used-by :func:`agent_tools.analysis.render_analysis()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_analysis_merger_and_lifecycle_classes()`
	def render(self) -> str:
		from agent_tools.links import markdown_link
		IssueValidator(Validator(self.__value).issues()).require_valid()
		lines = [RedFlagRenderer(self.__value).render()] if self.__value.get('red_flags') else []
		if 3 == self.__value.get('schema_version'):
			lines.extend(['# Primary Observations and Calculations', ''])
			for fact in self.__value['facts']:
				lines.extend([f"## {fact['id']}", fact['essence'], '', *self.__render_claim_contract(fact, markdown_link)])
		for number, (key, title) in enumerate(zip(SECTIONS, TITLES), 1):
			lines.extend(self.__render_section(number, key, title, markdown_link))
		return '\n'.join(lines)