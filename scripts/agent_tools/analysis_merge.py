# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add schema-help CLI, validator hints, save-analysis --merge, and af-worker file handoff":
# https://github.com/dmitry-ai/harness/issues/217
from __future__ import annotations
import json
from pathlib import Path
from .analysis import analysis_issues, digest, save_analysis
from .diagnostics import require_valid
from .evidence import evidence_issues
from .path_registry import project_paths
from .storage import locked, replace_bytes
_DICT_SECTIONS = ('notes', 'sources')
_LIST_SECTIONS = ('facts', 'identity', 'concerns', 'misconceptions', 'causes', 'methods')
_PARTIAL_IGNORED_CODES = frozenset({'analysis.empty'})
def _claim_id(item) -> str | None:
	cid = item.get('id') if isinstance(item, dict) else None
	return cid if isinstance(cid, str) and cid else None
def _empty_skeleton() -> dict:
	return {'schema_version': 3, 'facts': [], 'identity': [], 'concerns': [], 'misconceptions': [], 'causes': [], 'methods': [], 'notes': {}, 'red_flags': [], 'websites': []}
def _index_existing(existing, remove_ids: set[str]) -> tuple[list, dict[str, int]]:
	out: list = []
	idx_by_id: dict[str, int] = {}
	for item in existing if isinstance(existing, list) else ():
		cid = _claim_id(item)
		if None is not cid and cid in remove_ids:
			continue
		if None is not cid:
			idx_by_id[cid] = len(out)
		out.append(item)
	return (out, idx_by_id)
def _load_merge_base(pp, expected_sha256: str | None, partial: bool) -> tuple[dict, bool]:
	draft = pp.data_dir / 'analysis-draft.json'
	target = pp.kb_dir / 'Analysis.json'
	if draft.is_file():
		r = (json.loads(draft.read_text(encoding='utf-8-sig')), True)
	elif target.is_file():
		raw = target.read_bytes()
		if (not partial) and None is not expected_sha256 and digest(raw) != expected_sha256:
			raise ValueError('Analysis changed or expected hash was not supplied; read current KB and reconcile the candidate')
		r = (json.loads(raw.decode('utf-8-sig')), False)
	else:
		r = (_empty_skeleton(), False)
	return r
def _merge_claim_list(existing, incoming, remove_ids: set[str]) -> list:
	out, idx_by_id = _index_existing(existing, remove_ids)
	for item in incoming if isinstance(incoming, list) else ():
		cid = _claim_id(item)
		if None is not cid and cid in idx_by_id:
			out[idx_by_id[cid]] = item
		else:
			if None is not cid:
				idx_by_id[cid] = len(out)
			out.append(item)
	return out
def _merge_extra_fields(base: dict, patch: dict, merged: dict) -> None:
	for sec in _DICT_SECTIONS:
		if sec in patch and isinstance(patch[sec], dict):
			prev = base.get(sec) if isinstance(base.get(sec), dict) else {}
			merged[sec] = {**prev, **patch[sec]}
	skip = set(_LIST_SECTIONS) | set(_DICT_SECTIONS) | {'remove_claim_ids'}
	for key, val in patch.items():
		if key not in skip:
			merged[key] = val
def _validate_partial(root: Path, merged: dict) -> None:
	issues = [it for it in analysis_issues(merged) if it.get('code') not in _PARTIAL_IGNORED_CODES]
	if not merged.get('websites'):
		issues = [it for it in issues if not str(it.get('code') or '').startswith('website')]
	require_valid(issues)
	require_valid(evidence_issues(root, merged, skip_structural=True))
def merge_analysis_candidate(base: dict, patch: dict) -> dict:
	if not isinstance(patch, dict):
		raise ValueError('Analysis merge candidate must be a JSON object')
	remove_ids = {x for x in (patch.get('remove_claim_ids') or ()) if isinstance(x, str)}
	merged = dict(base)
	for sec in _LIST_SECTIONS:
		merged[sec] = _merge_claim_list(base.get(sec), patch.get(sec) if sec in patch else (), remove_ids)
	_merge_extra_fields(base, patch, merged)
	merged.setdefault('schema_version', 3)
	return merged
def save_merged_analysis(root: Path | str, patch: dict, expected_sha256: str | None=None, *, partial: bool=False) -> dict:
	pp = project_paths(root, exact_root=True)
	draft = pp.data_dir / 'analysis-draft.json'
	base, had_draft = _load_merge_base(pp, expected_sha256, partial)
	merged = merge_analysis_candidate(base, patch)
	if partial:
		_validate_partial(pp.root, merged)
		payload = (json.dumps(merged, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
		draft.parent.mkdir(parents=True, exist_ok=True)
		with locked(pp.data_dir / 'analysis.lock'):
			replace_bytes(draft, payload)
		r = {'target': str(draft), 'sha256': digest(payload), 'partial': True, 'merged': True, 'claim_counts': {sec: len(merged.get(sec) or ()) for sec in _LIST_SECTIONS}}
	else:
		res = save_analysis(pp.root, merged, expected_sha256=expected_sha256)
		cleared = False
		if had_draft and draft.is_file():
			draft.unlink()
			cleared = True
		r = {**res, 'partial': False, 'merged': True, 'draft_cleared': cleared}
	return r
