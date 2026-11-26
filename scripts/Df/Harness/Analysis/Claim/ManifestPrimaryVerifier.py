# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Analysis.LocalSourceResolver import LocalSourceResolver
import json
import re
_HASH_RE = re.compile('^[a-f0-9]{64}$')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ManifestPrimaryVerifier:
	# @used-by :func:`agent_tools.claims._manifest_primary()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.PrimaryCapabilities.PrimaryCapabilities.resolve()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
	def __init__(self, root, ref: dict) -> None:
		self.__root = root
		self.__ref = ref
	# @used-by :meth:`ManifestPrimaryVerifier.verify()`
	def __check_intake(self, root: Path, evidence: Path, manifest_file: Path, manifest: dict, state: dict, source: Path) -> set[str]:
		from agent_tools.intake import CAPTURE_NAME, _validate_receipt
		from agent_tools.research import inside
		intake = evidence / 'Intake'
		if manifest_file.parent != intake or 1 != manifest.get('version') or manifest.get('status') not in {'prepared', 'drained'} or (manifest.get('job_id') != state.get('job_id')):
			raise ValueError('Primary intake/attachment must belong to the registered snapshot or its intake manifest')
		prov = manifest.get('original_directory_provenance')
		if not (isinstance(prov, str) and prov.strip()):
			raise ValueError('Intake primary needs the full capture receipt bound to its registered snapshot')
		capture = Path(prov)
		match = CAPTURE_NAME.fullmatch(capture.name)
		if not capture.is_absolute() or not match or '~' + match[1] != state['job_id'] or manifest_file.name != capture.name + '.json' or True is not manifest.get('original_paths_are_provenance_only'):
			raise ValueError('Intake capture identity must match its receipt filename and registered project')
		try:
			_validate_receipt(manifest, capture, root, state)
		except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, StopIteration) as exc:
			raise ValueError('Intake receipt is not bound to the permanent registered source snapshot: ' + str(exc)) from exc
		return self.__match_intake_entry(root, manifest, source, inside)
	# @used-by :meth:`ManifestPrimaryVerifier.verify()`
	def __check_snapshot(self, root: Path, manifest_file: Path, manifest: dict, source: Path) -> set[str] | None:
		raw = manifest_file.read_bytes()
		if not _HASH_RE.fullmatch(manifest_file.stem) or df_sha256(raw) != manifest_file.stem:
			raise ValueError('The registered intake snapshot must retain its content-addressed bytes')
		r: set[str] | None = None
		if 'intake' == self.__ref['kind'] and source == manifest_file:
			r = {'client_report', 'content'}
		elif 'attachment' == self.__ref['kind']:
			for asset in manifest.get('asset_evidence', []):
				if isinstance(asset, dict) and LocalSourceResolver(root, asset.get('file', '')).resolve() == source and asset.get('sha256') == self.__ref['source_sha256']:
					r = {'client_report', 'content'}
					break
		return r
	# @used-by :meth:`ManifestPrimaryVerifier.verify()`
	def __load_state(self, pp) -> tuple[dict, Path]:
		from agent_tools.research import inside
		state_file = pp.project_json
		state = json.loads(state_file.read_text(encoding='utf-8-sig')) if state_file.exists() else {}
		if not isinstance(state, dict) or True is not state.get('initialized') or (not (isinstance(state.get('job_id'), str) and state['job_id'].strip())) or (not (isinstance(state.get('snapshot'), str) and state['snapshot'].strip())):
			raise ValueError('Intake evidence needs a registered initialized project and its exact permanent snapshot')
		snapshot = inside(pp.root, state['snapshot'])
		if not snapshot.is_relative_to(pp.evidence_dir):
			raise ValueError('Registered intake snapshot must belong to project Evidence')
		snap_raw = snapshot.read_bytes()
		snap_val = json.loads(snap_raw.decode('utf-8-sig'))
		if not _HASH_RE.fullmatch(snapshot.stem) or df_sha256(snap_raw) != snapshot.stem or (not isinstance(snap_val, dict)) or snap_val.get('job_id') != state['job_id']:
			raise ValueError('The registered snapshot must retain its content-addressed bytes and project job ID')
		return (state, snapshot)
	# @used-by :meth:`ManifestPrimaryVerifier.__check_intake()`
	def __match_intake_entry(self, root: Path, manifest: dict, source: Path, inside) -> set[str]:
		r: set[str] | None = None
		for entry in manifest.get('entries', []):
			if isinstance(entry, dict) and isinstance(entry.get('durable_file'), str) and inside(root, entry['durable_file']) == source and entry.get('sha256') == self.__ref['source_sha256'] and 'identity' == entry.get('transform'):
				name = entry.get('original_relative_provenance', '')
				if 'attachment' == self.__ref['kind'] and (not name.startswith('attachments/')):
					continue
				if 'intake' == self.__ref['kind'] and name not in {'source.json', 'request.txt'}:
					raise ValueError('Intake primaries are the captured source.json or exact user request; site hypotheses and agent notes require their own primary origins')
				r = {'client_report', 'content'}
				break
		if None is r:
			raise ValueError('Source bytes are absent from the declared intake/attachment manifest')
		return r
	# @used-by :func:`agent_tools.claims._manifest_primary()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.PrimaryCapabilities.PrimaryCapabilities.resolve()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
	def verify(self) -> set[str]:
		from agent_tools.path_registry import project_paths
		pp = project_paths(self.__root, exact_root=True)
		source = LocalSourceResolver(pp.root, self.__ref['source']).resolve()
		manifest_file = LocalSourceResolver(pp.root, self.__ref['manifest']).resolve()
		manifest = json.loads(manifest_file.read_text(encoding='utf-8-sig'))
		if not isinstance(manifest, dict):
			raise ValueError('A primary manifest must be a saved JSON object')
		state, snapshot = self.__load_state(pp)
		hit = self.__check_snapshot(pp.root, manifest_file, manifest, source) if manifest_file == snapshot else None
		return hit if None is not hit else self.__check_intake(pp.root, pp.evidence_dir, manifest_file, manifest, state, source)