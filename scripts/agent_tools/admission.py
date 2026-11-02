# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Bind publication admission to immutable historical integrity proofs":
# https://github.com/dmitry-ai/harness/issues/41
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from .storage import create_bytes, data_dir_for
_SEAL = object()
def _bytes(value):
	return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
def _digest(value):
	return hashlib.sha256(value).hexdigest()
def binding(directory, requests, response, turn, request_ids):
	return {'journal': str(Path(directory).resolve()), 'turn': turn, 'request_ids': request_ids, 'requests_sha256': _digest(_bytes(requests)), 'response_sha256': _digest(response.encode('utf-8'))}
class PublicationAdmission:
	def __init__(self, reference, identity, *, seal=None):
		if seal is not _SEAL:
			raise ValueError('Publication admission requires the current strict gate')
		self.reference = deepcopy(reference)
		self.identity = deepcopy(identity)
		self._seal = seal
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
def verify(reference, identity):
	from .text_workflow import verify_integrity
	if not isinstance(reference, dict) or reference.get('schema_version') != 1 or not isinstance(reference.get('file'), str) or not Path(reference['file']).is_absolute():
		raise ValueError('A historical publication admission proof is required')
	path = Path(reference['file'])
	raw = path.read_bytes()
	if _digest(raw) != reference.get('sha256') or path.name != reference['sha256'] + '.json':
		raise ValueError('Publication admission proof changed')
	proof = json.loads(raw)
	if proof.get('schema_version') != 1 or proof.get('kind') != 'publication_admission' or proof.get('binding') != identity or not isinstance(proof.get('integrity'), list):
		raise ValueError('Publication admission proof belongs to another journal/request/response identity')
	for graph in proof['integrity']:
		verify_integrity(graph)
	return {'status': 'verified', 'scope': 'original_publication_admission'}
def require_current(capability, identity):
	if not isinstance(capability, PublicationAdmission) or capability._seal is not _SEAL or capability.identity != identity:
		raise ValueError('A current proof-bound publication admission capability is required')
	verify(capability.reference, identity)
	return deepcopy(capability.reference)
