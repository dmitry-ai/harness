# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from Df.Core.lib.json_io import df_json_bytes
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Completion.PublicationAdmission import PublicationAdmission, SEAL
from Df.Harness.lib.journal_core import dfh_same_journal_identity
from Df.Harness.lib.path_resolve import dfh_load_registry
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir
from Df.Harness.lib.storage import dfh_create_bytes, dfh_data_dir_for
import json
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`Df.Harness.lib.completion_record._commit_or_verify_journal_group()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
# @used-by :func:`test_project_rename._assert_renamed_journal_and_state()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__prepare_context()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_admission_one_way_facade_behavior()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_journal_tail()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :mod:`agent_tools.admission`
def dfh_admission_binding(directory, requests, response: str, turn: str, request_ids) -> dict:
	return {'journal': str(Path(directory).resolve()), 'turn': turn, 'request_ids': request_ids, 'requests_sha256': df_sha256(df_json_bytes(requests)), 'response_sha256': df_sha256(response.encode('utf-8'))}
# @used-by :func:`dfh_verify_admission()`
# @used-by :mod:`agent_tools.admission`
def dfh_admission_same_binding(saved: dict | None, current: dict) -> bool:
	if not isinstance(saved, dict) or set(saved) != set(current):
		r = False
	elif saved == current:
		r = True
	else:
		r = dfh_same_journal_identity(saved.get('journal'), current.get('journal')) and all((saved.get(k) == current.get(k) for k in current if 'journal' != k))
	return r
# @used-by :func:`Df.Harness.lib.completion_record._commit_or_verify_journal_group()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
# @used-by :meth:`Df.Harness.Completion.AdmissionGuard.AdmissionGuard.run()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__prepare_context()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_journal_tail()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :mod:`agent_tools.admission`
def dfh_capture_admission(paths, requests, response: str, identity: dict) -> PublicationAdmission:
	from agent_tools.text_workflow import gate_requests
	results = gate_requests(paths, requests, response, capture=True)
	proof = {'schema_version': 1, 'kind': 'publication_admission', 'binding': identity, 'integrity': [item['integrity'] for item in results]}
	raw = df_json_bytes(proof)
	path = dfh_data_dir_for(Path(identity['journal'])) / 'publication-admissions' / (df_sha256(raw) + '.json')
	path.parent.mkdir(parents=True, exist_ok=True)
	if path.exists():
		if path.read_bytes() != raw:
			raise ValueError('Immutable publication admission proof changed')
	else:
		try:
			dfh_create_bytes(path, raw)
		except FileExistsError:
			if path.read_bytes() != raw:
				raise ValueError('Concurrent publication admission proof differs')
	return PublicationAdmission({'schema_version': 1, 'file': str(path), 'sha256': df_sha256(raw)}, identity, seal=SEAL)
# @used-by :meth:`Df.Harness.Completion.AdmissionGuard.AdmissionGuard.run()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__prepare_context()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_admission_one_way_facade_behavior()`
# @used-by :mod:`agent_tools.admission`
def dfh_require_current_admission(capability, identity: dict) -> dict:
	if not isinstance(capability, PublicationAdmission) or capability._seal is not SEAL or capability.identity != identity:
		raise ValueError('A current proof-bound publication admission capability is required')
	dfh_verify_admission(capability.reference, identity)
	return deepcopy(capability.reference)
# @used-by :func:`dfh_verify_admission()`
# @used-by :mod:`agent_tools.admission`
def dfh_resolve_admission_proof_file(raw_file: str, journal_dir: str) -> Path:
	path = Path(raw_file)
	r = path
	if not path.is_file() and 'publication-admissions' == path.parent.name and 'data' == path.parents[1].name and '\ua616' == path.parents[2].name:
		cand = dfh_data_dir_for(Path(journal_dir)) / 'publication-admissions' / path.name
		if cand.is_file():
			reg = dfh_load_registry()
			old_anc = path.parents[4] if 5 <= len(path.parents) and '_' == path.parents[3].name else path.parents[3]
			new_anc = cand.parents[4] if 5 <= len(cand.parents) and '_' == cand.parents[3].name else cand.parents[3]
			if dfh_canonicalize_root_dir(old_anc, reg) == dfh_canonicalize_root_dir(new_anc, reg):
				r = cand
	return r
# @used-by :func:`Df.Harness.lib.completion_record._commit_or_verify_journal_group()`
# @used-by :func:`dfh_require_current_admission()`
# @used-by :func:`test_project_rename._assert_renamed_journal_and_state()`
# @used-by :meth:`Df.Harness.Completion.AdmissionGuard.AdmissionGuard.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_admission_one_way_facade_behavior()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :mod:`agent_tools.admission`
def dfh_verify_admission(reference, identity: dict) -> dict:
	from agent_tools.text_workflow import verify_integrity
	if not isinstance(reference, dict) or 1 != reference.get('schema_version') or (not isinstance(reference.get('file'), str)) or (not Path(reference['file']).is_absolute()):
		raise ValueError('A historical publication admission proof is required')
	path = dfh_resolve_admission_proof_file(reference['file'], identity['journal'])
	raw = path.read_bytes()
	if df_sha256(raw) != reference.get('sha256') or path.name != reference['sha256'] + '.json':
		raise ValueError('Publication admission proof changed')
	proof = json.loads(raw)
	if 1 != proof.get('schema_version') or 'publication_admission' != proof.get('kind') or (not dfh_admission_same_binding(proof.get('binding'), identity)) or (not isinstance(proof.get('integrity'), list)):
		raise ValueError('Publication admission proof belongs to another journal/request/response identity')
	for graph in proof['integrity']:
		verify_integrity(graph)
	return {'status': 'verified', 'scope': 'original_publication_admission'}
