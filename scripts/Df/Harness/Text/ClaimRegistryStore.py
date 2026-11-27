# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from Df.Harness.lib.research import dfh_json_data
from Df.Harness.lib.text_claims import dfh_registry_path, dfh_text_digest
from agent_tools.claims import claim_digest, claim_index, contract_issues, evidence_contract_issues
from agent_tools.storage import create_bytes, locked, replace_bytes
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ClaimRegistryStore:
	# @used-by :func:`agent_tools.text_claims.save_registry()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__review_source_handlers()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_claims_sources_and_cli_runner_classes()`
	def __init__(self, root, candidate, *, expected_sha256=None, reference=None, reassessments=None) -> None:
		self.__root = root
		self.__candidate = candidate
		self.__expected_sha256 = expected_sha256
		self.__reference = reference
		self.__reassessments = reassessments or {}
	# @used-by :meth:`ClaimRegistryStore.save()`
	def __invalidate_dependents(self, old: dict, index: dict, changed: set[str]) -> list[str]:
		invalidated, pending = ([], set(changed) & set(old))
		while pending:
			current = pending.pop()
			for ident, claim in index.items():
				if ident == current or ident in invalidated or ident not in old:
					continue
				if any((d.get('claim_id') == current for d in claim.get('derived_from', []))):
					claim['superseded_dependencies'] = deepcopy(claim.get('derived_from', []))
					claim['verification_status'] = 'stale'
					claim['missing_checks'] = list(dict.fromkeys([*claim.get('missing_checks', []), 'Reassess the changed primary premise: ' + current]))
					invalidated.append(ident)
					pending.add(ident)
		self.__refresh_dep_digests(index, invalidated)
		return invalidated
	# @used-by :meth:`ClaimRegistryStore.save()`
	@staticmethod
	def __persist(path: Path, data_dir: Path, previous: bytes | None, payload: bytes) -> None:
		history = data_dir / 'text-claim-history'
		history.mkdir(parents=True, exist_ok=True)
		if None is not previous:
			archive = history / (dfh_text_digest(previous) + '.json')
			if not archive.exists():
				create_bytes(archive, previous)
		if (path.read_bytes() if path.exists() else None) != previous:
			raise ValueError('Claim registry changed during validation; external edit preserved')
		if None is not previous:
			replace_bytes(path, payload)
		else:
			path.parent.mkdir(parents=True, exist_ok=True)
			create_bytes(path, payload)
	# @used-by :meth:`ClaimRegistryStore.__invalidate_dependents()`
	@staticmethod
	def __refresh_dep_digests(index: dict, invalidated: list[str]) -> None:
		for _ in range(len(index) + 1):
			for ident in invalidated:
				for dep in index[ident].get('derived_from', []):
					if dep.get('claim_id') in index:
						dep['sha256'] = claim_digest(index[dep['claim_id']])
	# @used-by :func:`agent_tools.text_claims.save_registry()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__review_source_handlers()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_claims_sources_and_cli_runner_classes()`
	def save(self) -> dict:
		from agent_tools.path_registry import project_paths
		pp = project_paths(self.__root, exact_root=True)
		root, value = (pp.root, deepcopy(self.__candidate))
		if not isinstance(value, dict) or 3 != value.get('schema_version'):
			raise ValueError('Text claim registry requires schema_version 3')
		path = dfh_registry_path(root, self.__reference)
		with locked(pp.data_dir / 'text-claims.lock'):
			previous = path.read_bytes() if path.exists() else None
			if (dfh_text_digest(previous) if None is not previous else None) != self.__expected_sha256:
				raise ValueError('Claim registry changed; read current bytes and reconcile')
			old, index = (claim_index(json.loads(previous)) if previous else {}, claim_index(value))
			changed = {i for i, c in index.items() if i not in old or claim_digest(c) != claim_digest(old[i])} | set(old) - set(index)
			invalidated = self.__invalidate_dependents(old, index, changed)
			issues = contract_issues(value) or evidence_contract_issues(root, value, skip_structural=True)
			if issues:
				raise ValueError(json.dumps(issues, ensure_ascii=False))
			payload = dfh_json_data(value)
			self.__persist(path, pp.data_dir, previous, payload)
		return {'registry': path.relative_to(root).as_posix(), 'sha256': dfh_text_digest(payload), 'changed_claims': sorted(changed), 'invalidated_claims': sorted(invalidated), 'detail': 'Dependent text approvals are checked against exact claim revisions before use'}
