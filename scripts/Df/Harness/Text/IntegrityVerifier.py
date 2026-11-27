# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from Df.Harness.Text.ApprovalIntegrityChecker import ApprovalIntegrityChecker
from Df.Harness.Text.SourceIntegrityChecker import SourceIntegrityChecker
from Df.Harness.Text.Workspace import Workspace
from Df.Harness.lib.research import dfh_inside
from Df.Harness.lib.text_claims import dfh_claim_subset, dfh_registry_path, dfh_text_digest
from Df.Harness.lib.text_review import dfh_text_review_state
from Df.Harness.lib.text_workflow import APPLIED_CHECK_KEYS, dfh_hash_or_none, dfh_read_json_sig, dfh_target_bytes
from agent_tools.storage import locked, read_addressed_json
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class IntegrityVerifier:
	# @used-by :func:`agent_tools.text_workflow._applied_integrity()`
	# @used-by :func:`agent_tools.text_workflow._claim_snapshot()`
	# @used-by :func:`agent_tools.text_workflow._reconciled_integrity()`
	# @used-by :func:`agent_tools.text_workflow._verify_applied_successor()`
	# @used-by :func:`agent_tools.text_workflow.integrity_snapshot()`
	# @used-by :func:`agent_tools.text_workflow.verify_integrity()`
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.gate()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_workspace_integrity_and_review_classes()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	def __init__(self, workspace: Workspace, *, index_state=None) -> None:
		self.ws = workspace
		self.index_state = index_state
	# @used-by :meth:`IntegrityVerifier.__collect_applied_files()`
	# @used-by :meth:`IntegrityVerifier.__collect_applied_reviews()`
	# @used-by :meth:`IntegrityVerifier.applied_integrity()`
	def __add_artifact(self, files: dict, reference: str, expected=None) -> None:
		actual = dfh_text_digest(dfh_inside(self.ws.root, reference).read_bytes())
		if None is not expected and actual != expected:
			raise ValueError('Admitted text artifact changed: ' + reference)
		if reference in files and files[reference] != actual:
			raise ValueError('Conflicting admitted text artifact versions')
		files[reference] = actual
	# @used-by :meth:`IntegrityVerifier.applied_integrity()`
	def __collect_applied(self, name: str, entry: dict, files: dict, claims: list, *, require_live_proof: bool) -> list:
		_, saved = read_addressed_json(dfh_inside(self.ws.root, entry['receipt']), suffix='-applied.json', error_msg='Applied text receipt changed: ' + name)
		if 'applied' != saved.get('status') or saved.get('target') != name or saved.get('candidate_sha256') != entry['sha256']:
			raise ValueError('Applied text receipt changed: ' + name)
		checked, candidate = self.ws.read_check(saved['check'])
		if True is not checked.get('valid') or any((saved.get(key) != checked.get(key) for key in APPLIED_CHECK_KEYS)):
			raise ValueError('Applied text no longer matches its admitted check')
		op, _ = self.ws.operation(saved['operation'])
		if op['target'] != name or op['base_sha256'] != saved['base_sha256']:
			raise ValueError('Applied text operation identity changed')
		claim = self.claim_snapshot(checked)
		versioned = {claim['registry']} if claim else set()
		if claim:
			claims.append(claim)
		self.__collect_applied_files(entry, saved, checked, op, candidate, versioned, files)
		return self.__collect_applied_reviews(saved, versioned, files, require_live_proof=require_live_proof)
	# @used-by :meth:`IntegrityVerifier.__collect_applied()`
	def __collect_applied_files(self, entry: dict, saved: dict, checked: dict, op: dict, candidate: str, versioned: set, files: dict) -> None:
		for reference, expected in saved['inputs'].items():
			if reference not in versioned:
				self.__add_artifact(files, reference, expected)
		op_dir = self.ws.folder / 'operations' / op['id']
		for reference in (entry['receipt'], saved['check'], checked['candidate'], (op_dir / 'operation.json').relative_to(self.ws.root).as_posix(), (op_dir / 'base.bin').relative_to(self.ws.root).as_posix()):
			self.__add_artifact(files, reference)
		for reference in saved.get('source_checks', []):
			for source, expected in SourceIntegrityChecker(self.ws.root, candidate, reference).check()['inputs'].items():
				self.__add_artifact(files, source, expected)
	# @used-by :meth:`IntegrityVerifier.__collect_applied()`
	def __collect_applied_reviews(self, saved: dict, versioned: set, files: dict, *, require_live_proof: bool) -> list:
		reviews: list = []
		if saved.get('approval'):
			approval = ApprovalIntegrityChecker(self.ws.root, saved['approval'], versioned_inputs=versioned, require_live_proof=require_live_proof).check()
			reviews = approval['reviews']
			for reference, expected in approval['files'].items():
				self.__add_artifact(files, reference, expected)
		return reviews
	# @used-by :meth:`IntegrityVerifier.claim_snapshot()`
	def __find_snapshot(self, checked: dict, registry, reference: str, versions: dict):
		from agent_tools.claims import all_claims, claim_digest
		r = checked.get('claim_snapshot')
		if None is r:
			candidates = [registry] + ([self.ws.pp.data_dir / 'text-claim-history' / (checked['inputs'][reference] + '.json')] if reference in checked['inputs'] else [])
			for path in candidates:
				try:
					candidate = dfh_claim_subset(dfh_read_json_sig(path), versions)
					if {claim['id']: claim_digest(claim) for claim in all_claims(candidate)} == versions:
						r = candidate
						break
				except (OSError, ValueError, KeyError, TypeError):
					continue
		return r
	# @used-by :meth:`IntegrityVerifier.applied_integrity()`
	def __state(self) -> dict:
		if None is self.index_state:
			self.index_state = self.ws.index()
		return self.index_state
	# @used-by :meth:`IntegrityVerifier.verify()`
	def __verify_target_artifacts(self, target: dict) -> None:
		from agent_tools.claims import all_claims, claim_digest
		for reference, expected in target['files'].items():
			if dfh_text_digest(dfh_inside(self.ws.root, reference).read_bytes()) != expected:
				raise ValueError('Historical admitted artifact changed: ' + reference)
		for claim in target['claims']:
			if {item['id']: claim_digest(item) for item in all_claims(claim['snapshot'])} != claim['versions']:
				raise ValueError('Historical admitted claim snapshot changed')
		if target.get('reviews'):
			reviews = {entry['id']: entry for entry in dfh_text_review_state(self.ws.root)['reviews']}
			if any((reviews.get(entry['id']) != entry for entry in target['reviews'])):
				raise ValueError('Historical admitted publication review changed or is missing')
	# @used-by :meth:`IntegrityVerifier.verify()`
	def __verify_target_lineage(self, target: dict) -> None:
		name = target['target']
		current = self.index_state['targets'].get(name)
		if None is current:
			raise ValueError('Historical text target registration is missing: ' + name)
		if current == target['entry']:
			if dfh_hash_or_none(dfh_target_bytes(self.ws.document(name))) != target['entry']['sha256']:
				raise ValueError('Historical text target changed without an applied revision: ' + name)
		else:
			if not current.get('receipt') and (not current.get('reconciliation')):
				raise ValueError('Later text version has no applied receipt: ' + name)
			self.verify_applied_successor(name, current, target['entry'])
			self.applied_integrity(name, current, require_live_proof=False)
	# @used-by :func:`agent_tools.text_workflow._applied_integrity()`
	# @used-by :meth:`IntegrityVerifier.__verify_target_lineage()`
	# @used-by :meth:`IntegrityVerifier.snapshot()`
	def applied_integrity(self, name: str, entry: dict, *, require_live_proof: bool=True) -> dict:
		if self.__state()['targets'].get(name) != entry or dfh_hash_or_none(dfh_target_bytes(self.ws.document(name))) != entry['sha256']:
			raise ValueError('Registered text target changed without its applied version: ' + name)
		files, claims, reviews = ({}, [], [])
		if entry.get('reconciliation') and (not entry.get('receipt')):
			for reference, expected in self.reconciled_integrity(name, entry)['files'].items():
				self.__add_artifact(files, reference, expected)
		elif entry.get('receipt'):
			reviews = self.__collect_applied(name, entry, files, claims, require_live_proof=require_live_proof)
		return {'target': name, 'entry': deepcopy(entry), 'files': files, 'claims': claims, 'reviews': reviews}
	# @used-by :func:`agent_tools.text_workflow._claim_snapshot()`
	# @used-by :meth:`IntegrityVerifier.__collect_applied()`
	def claim_snapshot(self, checked: dict):
		from agent_tools.claims import all_claims, claim_digest
		r = None
		versions = checked.get('claim_versions', {})
		if versions:
			registry = dfh_registry_path(self.ws.root, (checked.get('manifest') or {}).get('registry'))
			reference = registry.relative_to(self.ws.root).as_posix()
			snapshot = self.__find_snapshot(checked, registry, reference, versions)
			if not isinstance(snapshot, dict) or {claim['id']: claim_digest(claim) for claim in all_claims(snapshot)} != versions:
				raise ValueError('Original admitted claim revisions are missing or changed')
			r = {'registry': reference, 'versions': versions, 'snapshot': snapshot}
		return r
	# @used-by :func:`agent_tools.text_workflow._reconciled_integrity()`
	# @used-by :meth:`IntegrityVerifier.applied_integrity()`
	# @used-by :meth:`IntegrityVerifier.verify_applied_successor()`
	def reconciled_integrity(self, name: str, entry: dict) -> dict:
		from agent_tools.path_registry import same_project_root
		reference = entry.get('reconciliation')
		if not reference or entry.get('receipt'):
			raise ValueError('Explicit text baseline reconciliation is missing: ' + name)
		raw, saved = read_addressed_json(dfh_inside(self.ws.root, reference), suffix='-reconciled.json', error_msg='Explicit text baseline reconciliation identity changed: ' + name)
		if 1 != saved.get('schema_version') or 'baseline_reconciliation' != saved.get('kind') or (not same_project_root(saved.get('root'), self.ws.root)) or saved.get('target') != name or saved.get('document_kind') != entry.get('kind') or (not isinstance(saved.get('previous'), dict)) or saved.get('baseline', {}).get('sha256') != entry.get('sha256'):
			raise ValueError('Explicit text baseline reconciliation identity changed: ' + name)
		op, base = self.ws.operation(saved['operation'])
		op_dir = self.ws.folder / 'operations' / op['id']
		if op.get('reconciliation') != reference or op['target'] != name or op['kind'] != entry['kind'] or op['base_sha256'] != entry['sha256'] or 'reconcile_sha256' not in op or op['reconcile_sha256'] != entry['sha256'] or saved['baseline']['file'] != (op_dir / 'base.bin').relative_to(self.ws.root).as_posix():
			raise ValueError('Explicit text reconciliation no longer matches the captured baseline operation: ' + name)
		op_json_rel = (op_dir / 'operation.json').relative_to(self.ws.root).as_posix()
		return {'previous': saved['previous'], 'files': {reference: dfh_text_digest(raw), saved['baseline']['file']: dfh_text_digest(base), op_json_rel: dfh_text_digest((op_dir / 'operation.json').read_bytes())}}
	# @used-by :func:`agent_tools.text_workflow.integrity_snapshot()`
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.gate()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	def snapshot(self, entries: dict) -> dict:
		return {'schema_version': 1, 'root': str(self.ws.root), 'targets': [self.applied_integrity(name, entry) for name, entry in sorted(entries.items())]}
	# @used-by :func:`agent_tools.text_workflow.verify_integrity()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_workspace_integrity_and_review_classes()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	def verify(self, graph: dict) -> dict:
		with locked(self.ws.folder / 'writer.lock'):
			self.index_state = self.ws.index()
			for target in graph['targets']:
				self.__verify_target_artifacts(target)
				self.__verify_target_lineage(target)
		return {'valid': True, 'scope': 'original_admitted_artifacts'}
	# @used-by :func:`agent_tools.text_workflow._verify_applied_successor()`
	# @used-by :meth:`IntegrityVerifier.__verify_target_lineage()`
	def verify_applied_successor(self, name: str, current: dict, original: dict) -> dict:
		entry, visited = (current, set())
		while entry != original:
			reference = entry.get('receipt') or entry.get('reconciliation')
			if not reference or reference in visited:
				raise ValueError('Current text is not a proven applied successor of the admitted version: ' + name)
			visited.add(reference)
			if not entry.get('receipt'):
				entry = self.reconciled_integrity(name, entry)['previous']
			else:
				_, saved = read_addressed_json(dfh_inside(self.ws.root, reference), suffix='-applied.json', error_msg='Applied text successor identity changed: ' + name)
				if 'applied' != saved.get('status') or saved.get('target') != name or saved.get('candidate_sha256') != entry.get('sha256') or saved.get('kind') != entry.get('kind'):
					raise ValueError('Applied text successor identity changed: ' + name)
				previous = saved.get('previous')
				if not isinstance(previous, dict) or previous.get('sha256') != saved.get('base_sha256'):
					raise ValueError('Applied text successor has no exact predecessor: ' + name)
				entry = previous
		return {'valid': True, 'scope': 'exact_applied_successor_lineage'}
