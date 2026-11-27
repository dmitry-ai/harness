# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from pathlib import Path
import re
from Df.Harness.lib.text_claims import dfh_claim_subset, dfh_evidence_inputs, dfh_primary_numbers, dfh_registry_path, dfh_text_digest, dfh_text_issue, dfh_text_nonempty
from Df.Harness.lib.text_sections import dfh_content_blocks
from agent_tools.claims import claim_digest, claim_index, contract_issues, evidence_contract_issues, standalone_numbers
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_SIGNIFICANT_PROPS = frozenset({'causality', 'business_impact', 'architecture_change', 'pricing_change', 'admin_configuration'})
class ClaimMapValidator:
	# @used-by :func:`agent_tools.text_claims.validate_map()`
	# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.run()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_claims_sources_and_cli_runner_classes()`
	def __init__(self, root, text: str, kind: str, manifest) -> None:
		self.__root = root
		self.__text = text
		self.__kind = kind
		self.__manifest = manifest
	# @used-by :meth:`ClaimMapValidator.__run_validation()`
	def __audit_block(self, section: str, item: dict, block: dict, index: dict, used: dict, issues: list) -> dict:
		ids, nums = (item.get('claim_ids', []), set())
		for ident in ids:
			if ident in index:
				nums.update(self.__check_claim(ident, index[ident], item, block, index, used, issues))
		missing = standalone_numbers(block['prose']) - nums
		if missing and ids:
			issues.append(dfh_text_issue('text.number', 'Numeric figures need primary operands or a verified calculation', key=item['key'], numbers=sorted(missing)))
		is_sig = any((index[i].get('materiality') in ('significant', 'critical') or 'causal' == index[i].get('category') or bool(set(index[i].get('properties', [])) & _SIGNIFICANT_PROPS) for i in ids if i in index))
		body = block['prose'] or block['text']
		return {'claim_id': item['key'], 'essence': body, 'response_excerpt': body, 'section': section, 'role': item.get('role'), 'kb_claim_ids': ids, 'kb_claim_versions': {i: claim_digest(index[i]) for i in ids if i in index}, 'qualification': item.get('qualification'), 'goal_basis': item.get('goal_basis'), 'new_content': item.get('new_content'), 'reuse_basis': item.get('reuse_basis'), 'nonfactual_basis': item.get('nonfactual_basis'), 'materiality': 'significant' if is_sig else 'routine'}
	# @used-by :meth:`ClaimMapValidator.__audit_block()`
	@staticmethod
	def __check_claim(ident: str, claim: dict, item: dict, block: dict, index: dict, used: dict, issues: list) -> set[str]:
		status = claim.get('verification_status')
		if status in ('unverified', 'unavailable', 'stale'):
			issues.append(dfh_text_issue('text.unverified', 'An unresolved/stale claim cannot support client prose', key=item['key'], claim_id=ident))
		if 'limited' == status:
			qualification = item.get('qualification')
			if not dfh_text_nonempty(qualification) or qualification not in block['prose']:
				issues.append(dfh_text_issue('text.qualification', 'A limited claim needs its exact visible qualification', key=item['key'], claim_id=ident))
			elif re.search('^(?:if|whether|when|unless|\\u0435\\u0441\\u043b\\u0438|\\u043f\\u0440\\u0438 \\u0443\\u0441\\u043b\\u043e\\u0432\\u0438\\u0438|\\u0432 \\u0441\\u043b\\u0443\\u0447\\u0430\\u0435)\\b', qualification.strip(), re.I):
				issues.append(dfh_text_issue('text.qualification_lazy', 'A conditional conjunction is not a valid claim qualification; name the technical boundary or operational access restriction', key=item['key'], claim_id=ident))
		if not (ident in used and 'inference' != item.get('role')):
			used[ident] = item['key']
		elif not dfh_text_nonempty(item.get('reuse_basis')):
			issues.append(dfh_text_issue('text.repeat', 'A fact is introduced twice; remove the repetition or justify distinct scope/comparison', key=item['key'], previous=used[ident]))
		return dfh_primary_numbers(claim, index)
	# @used-by :meth:`ClaimMapValidator.__run_validation()`
	def __load_registry(self, all_ids: set[str], issues: list, inputs: dict) -> dict:
		index: dict = {}
		if all_ids:
			registry = dfh_registry_path(self.__root, self.__manifest.get('registry'))
			value = dfh_claim_subset(json.loads(registry.read_text(encoding='utf-8-sig')), all_ids)
			issues.extend(contract_issues(value))
			if not issues:
				issues.extend(evidence_contract_issues(self.__root, value, skip_structural=True))
			inputs[registry.relative_to(Path(self.__root).resolve()).as_posix()] = dfh_text_digest(registry.read_bytes())
			index = claim_index(value)
			if not issues:
				inputs.update(dfh_evidence_inputs(self.__root, value))
		return index
	# @used-by :meth:`ClaimMapValidator.validate()`
	def __run_validation(self, issues: list, inputs: dict, assessment: list) -> dict:
		mapped: dict = {}
		actual = {block['section']: block for block in dfh_content_blocks(self.__text, self.__kind)}
		for item in self.__manifest['blocks']:
			self.__validate_block_entry(item, actual, mapped, issues)
		if set(actual) != set(mapped):
			issues.append(dfh_text_issue('text.coverage', 'Map must cover every content block exactly once', missing=sorted(set(actual) - set(mapped)), extra=sorted(set(mapped) - set(actual))))
		all_ids = {ident for item in mapped.values() for ident in item.get('claim_ids', []) if isinstance(ident, str)}
		index = self.__load_registry(all_ids, issues, inputs)
		used: dict = {}
		for section, item in mapped.items():
			if section in actual:
				assessment.append(self.__audit_block(section, item, actual[section], index, used, issues))
		return index
	# @used-by :meth:`ClaimMapValidator.__run_validation()`
	@staticmethod
	def __validate_block_entry(item, actual: dict, mapped: dict, issues: list) -> None:
		if not isinstance(item, dict) or not dfh_text_nonempty(item.get('key')) or (not dfh_text_nonempty(item.get('section'))):
			issues.append(dfh_text_issue('text.block', 'Each block needs a stable key and current section'))
		else:
			section, key = (item['section'], item['key'])
			if section in mapped or key in {b['key'] for b in mapped.values()}:
				issues.append(dfh_text_issue('text.duplicate_key', 'A section and stable key must each occur once', key=key))
			else:
				mapped[section] = item
				block = actual.get(section)
				if not block or dfh_text_digest(block['text'].encode()) != item.get('text_sha256'):
					issues.append(dfh_text_issue('text.block_version', 'Map does not match exact current block bytes', key=key))
				else:
					ClaimMapValidator.__validate_block_fields(item, key, issues)
	# @used-by :meth:`ClaimMapValidator.__validate_block_entry()`
	@staticmethod
	def __validate_block_fields(item: dict, key: str, issues: list) -> None:
		if item.get('role') not in ('observation', 'documented', 'inference', 'recommendation', 'context', 'nonfactual'):
			issues.append(dfh_text_issue('text.role', 'Choose the block role explicitly', key=key))
		if not dfh_text_nonempty(item.get('goal_basis')) or not dfh_text_nonempty(item.get('new_content')):
			issues.append(dfh_text_issue('text.relevance', 'Explain the goal contribution and new information', key=key))
		if not isinstance(item.get('claim_ids'), list) or len(item['claim_ids']) != len(set(item['claim_ids'])):
			issues.append(dfh_text_issue('text.claims', 'Record unique supporting claim IDs', key=key))
		elif not item['claim_ids'] and 'nonfactual' != item.get('role'):
			issues.append(dfh_text_issue('text.unsourced', 'A substantive block must identify its KB claims', key=key))
		if 'nonfactual' == item.get('role') and (not dfh_text_nonempty(item.get('nonfactual_basis'))):
			issues.append(dfh_text_issue('text.nonfactual', 'A salutation/offer/question needs its exact nonfactual purpose; review confirms this classification', key=key))
	# @used-by :func:`agent_tools.text_claims.validate_map()`
	# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.run()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_claims_sources_and_cli_runner_classes()`
	def validate(self) -> dict:
		issues, inputs, assessment, index = ([], {}, [], {})
		if not isinstance(self.__manifest, dict) or 1 != self.__manifest.get('schema_version') or (not isinstance(self.__manifest.get('blocks'), list)):
			r = {'valid': False, 'issues': [dfh_text_issue('text.map', 'A schema 1 paragraph map is required')], 'inputs': {}, 'claims': [], 'claim_versions': {}}
		else:
			try:
				index = self.__run_validation(issues, inputs, assessment)
			except (ValueError, OSError, KeyError, TypeError) as exc:
				issues.append(dfh_text_issue('text.map_input', str(exc)))
			r = {'valid': not issues, 'issues': issues, 'inputs': inputs, 'claims': assessment, 'claim_versions': {i: claim_digest(c) for i, c in index.items()}}
		return r
