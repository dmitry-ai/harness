# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from .storage import create_bytes, data_dir_for
_SEAL = object()
# @used-by :func:`binding()`
# @used-by :func:`capture()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
def _bytes(value):
	return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
# @used-by :func:`binding()`
# @used-by :func:`capture()`
# @used-by :func:`verify()`
def _digest(value):
	return hashlib.sha256(value).hexdigest()
# @used-by :func:`agent_tools.completion._record()`
# @used-by :func:`agent_tools.journal.record_answer()`
# @used-by :func:`agent_tools.stop_emergency_capture._record_emergency_files()`
# @used-by :func:`test_project_rename._assert_renamed_journal_and_state()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
def binding(directory, requests, response, turn, request_ids):
	return {'journal': str(Path(directory).resolve()), 'turn': turn, 'request_ids': request_ids, 'requests_sha256': _digest(_bytes(requests)), 'response_sha256': _digest(response.encode('utf-8'))}
# 2026-11-03
# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
# https://github.com/dmitry-ai/harness/issues/41
class PublicationAdmission:
	# @used-by :func:`capture()`
	def __init__(self, reference, identity, *, seal=None):
		if seal is not _SEAL:
			raise ValueError('Publication admission requires the current strict gate')
		self.reference = deepcopy(reference)
		self.identity = deepcopy(identity)
		self._seal = seal
# @used-by :func:`agent_tools.completion._record()`
# @used-by :func:`agent_tools.journal.record_answer()`
# @used-by :func:`agent_tools.stop_emergency_capture._record_emergency_files()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
def capture(paths, requests, response, identity):
	from .text_workflow import gate_requests
	results = gate_requests(paths, requests, response, capture=True)
	proof = {'schema_version': 1, 'kind': 'publication_admission', 'binding': identity, 'integrity': [item['integrity'] for item in results]}
	raw = _bytes(proof)
	path = data_dir_for(Path(identity['journal'])) / 'publication-admissions' / (_digest(raw) + '.json')
	path.parent.mkdir(parents=True, exist_ok=True)
	if path.exists():
		if path.read_bytes() != raw:
			raise ValueError('Immutable publication admission proof changed')
	else:
		try:
			create_bytes(path, raw)
		except FileExistsError:
			if path.read_bytes() != raw:
				raise ValueError('Concurrent publication admission proof differs')
	reference = {'schema_version': 1, 'file': str(path), 'sha256': _digest(raw)}
	return PublicationAdmission(reference, identity, seal=_SEAL)
# 2026-11-20
# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
# https://github.com/dmitry-ai/harness/issues/101
# @used-by :func:`verify()`
def _same_binding(saved: dict | None, current: dict) -> bool:
	if not isinstance(saved, dict) or set(saved) != set(current):
		return False
	if saved == current:
		return True
	from .journal import same_journal_identity
	return same_journal_identity(saved.get('journal'), current.get('journal')) and all((saved.get(k) == current.get(k) for k in current if 'journal' != k))
# 2026-11-20
# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
# https://github.com/dmitry-ai/harness/issues/101
# @used-by :func:`verify()`
def _resolve_proof_file(raw_file: str, journal_dir: str) -> Path:
	path = Path(raw_file)
	if path.is_file():
		return path
	if 'publication-admissions' == path.parent.name and 'data' == path.parents[1].name and '\ua616' == path.parents[2].name:
		cand = data_dir_for(Path(journal_dir)) / 'publication-admissions' / path.name
		if cand.is_file():
			from .path_registry import canonicalize_root_dir
			old_anc = path.parents[4] if 5 <= len(path.parents) and '_' == path.parents[3].name else path.parents[3]
			new_anc = cand.parents[4] if 5 <= len(cand.parents) and '_' == cand.parents[3].name else cand.parents[3]
			if canonicalize_root_dir(old_anc) == canonicalize_root_dir(new_anc):
				return cand
	return path
# @used-by :func:`agent_tools.completion._record()`
# @used-by :func:`require_current()`
# @used-by :func:`test_project_rename._assert_renamed_journal_and_state()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
def verify(reference, identity):
	from .text_workflow import verify_integrity
	if not isinstance(reference, dict) or reference.get('schema_version') != 1 or not isinstance(reference.get('file'), str) or not Path(reference['file']).is_absolute():
		raise ValueError('A historical publication admission proof is required')
	# 2026-11-20
	# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
	# https://github.com/dmitry-ai/harness/issues/101
	path = _resolve_proof_file(reference['file'], identity['journal'])
	raw = path.read_bytes()
	if _digest(raw) != reference.get('sha256') or path.name != reference['sha256'] + '.json':
		raise ValueError('Publication admission proof changed')
	proof = json.loads(raw)
	# 2026-11-20
	# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
	# https://github.com/dmitry-ai/harness/issues/101
	if proof.get('schema_version') != 1 or proof.get('kind') != 'publication_admission' or (not _same_binding(proof.get('binding'), identity)) or not isinstance(proof.get('integrity'), list):
		raise ValueError('Publication admission proof belongs to another journal/request/response identity')
	for graph in proof['integrity']:
		verify_integrity(graph)
	return {'status': 'verified', 'scope': 'original_publication_admission'}
# @used-by :func:`agent_tools.journal.record_answer()`
def require_current(capability, identity):
	if not isinstance(capability, PublicationAdmission) or capability._seal is not _SEAL or capability.identity != identity:
		raise ValueError('A current proof-bound publication admission capability is required')
	verify(capability.reference, identity)
	return deepcopy(capability.reference)
