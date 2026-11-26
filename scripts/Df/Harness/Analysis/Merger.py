# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Analysis.CandidateMerger import CandidateMerger
from Df.Harness.Analysis.EvidenceAuditor import EvidenceAuditor
from Df.Harness.Analysis.Saver import Saver
from Df.Harness.Analysis.Validator import Validator
from Df.Harness.Project.IssueValidator import IssueValidator
from agent_tools.path_registry import project_paths
from agent_tools.storage import locked, replace_bytes
import json
_LIST_SECTIONS = ('facts', 'identity', 'concerns', 'misconceptions', 'causes', 'methods')
_PARTIAL_IGNORED_CODES = frozenset({'analysis.empty'})
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class Merger:
	# @used-by :func:`agent_tools.analysis_merge.save_merged_analysis()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_analysis_merger_and_lifecycle_classes()`
	def __init__(self, root: Path | str, patch: dict, expected_sha256: str | None=None, *, partial: bool=False) -> None:
		self.__root = root
		self.__patch = patch
		self.__expected_sha256 = expected_sha256
		self.__partial = partial
	# @used-by :meth:`Merger.__load_base()`
	def __empty_skeleton(self) -> dict:
		return {'schema_version': 3, 'facts': [], 'identity': [], 'concerns': [], 'misconceptions': [], 'causes': [], 'methods': [], 'notes': {}, 'red_flags': [], 'websites': []}
	# @used-by :meth:`Merger.save()`
	def __load_base(self, pp) -> tuple[dict, bool]:
		draft = pp.data_dir / 'analysis-draft.json'
		target = pp.kb_dir / 'Analysis.json'
		if draft.is_file():
			r = (json.loads(draft.read_text(encoding='utf-8-sig')), True)
		elif target.is_file():
			raw = target.read_bytes()
			if (not self.__partial) and None is not self.__expected_sha256 and df_sha256(raw) != self.__expected_sha256:
				raise ValueError('Analysis changed or expected hash was not supplied; read current KB and reconcile the candidate')
			r = (json.loads(raw.decode('utf-8-sig')), False)
		else:
			r = (self.__empty_skeleton(), False)
		return r
	# @used-by :meth:`Merger.save()`
	def __validate_partial(self, root: Path, merged: dict) -> None:
		issues = [it for it in Validator(merged).issues() if it.get('code') not in _PARTIAL_IGNORED_CODES]
		if not merged.get('websites'):
			issues = [it for it in issues if not str(it.get('code') or '').startswith('website')]
		IssueValidator(issues).require_valid()
		IssueValidator(EvidenceAuditor(root, merged, skip_structural=True).issues()).require_valid()
	# @used-by :func:`agent_tools.analysis_merge.save_merged_analysis()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_analysis_merger_and_lifecycle_classes()`
	def save(self) -> dict:
		pp = project_paths(self.__root, exact_root=True)
		draft = pp.data_dir / 'analysis-draft.json'
		base, had_draft = self.__load_base(pp)
		merged = CandidateMerger(base, self.__patch).merge()
		if self.__partial:
			self.__validate_partial(pp.root, merged)
			payload = (json.dumps(merged, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
			draft.parent.mkdir(parents=True, exist_ok=True)
			with locked(pp.data_dir / 'analysis.lock'):
				replace_bytes(draft, payload)
			r = {'target': str(draft), 'sha256': df_sha256(payload), 'partial': True, 'merged': True, 'claim_counts': {sec: len(merged.get(sec) or ()) for sec in _LIST_SECTIONS}}
		else:
			res = Saver(pp.root, merged, self.__expected_sha256).save()
			cleared = False
			if had_draft and draft.is_file():
				draft.unlink()
				cleared = True
			r = {**res, 'partial': False, 'merged': True, 'draft_cleared': cleared}
		return r