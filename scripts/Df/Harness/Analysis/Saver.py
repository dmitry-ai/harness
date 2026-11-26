# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Analysis.EvidenceAuditor import EvidenceAuditor
from Df.Harness.Analysis.Validator import Validator
from Df.Harness.Project.IssueValidator import IssueValidator
from agent_tools.storage import create_bytes, locked, replace_bytes, write_immutable_bytes
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class Saver:
	# @used-by :func:`agent_tools.analysis.save_analysis()`
	# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.save()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_analysis_merger_and_lifecycle_classes()`
	def __init__(self, root, candidate, expected_sha256=None) -> None:
		self.__root = root
		self.__candidate = candidate
		self.__expected_sha256 = expected_sha256
	# @used-by :meth:`Saver.__commit_locked()`
	def __check_expected(self, previous: bytes | None) -> None:
		if None is not previous and df_sha256(previous) != self.__expected_sha256:
			raise ValueError('Analysis changed or expected hash was not supplied; read current KB and reconcile the candidate')
		if None is previous and None is not self.__expected_sha256:
			raise ValueError('Expected existing analysis is missing; preserve candidate and inspect state')
	# @used-by :meth:`Saver.save()`
	def __commit_locked(self, pp, payload: bytes) -> str:
		target = pp.kb_dir / 'Analysis.json'
		target.parent.mkdir(parents=True, exist_ok=True)
		with locked(pp.data_dir / 'analysis.lock'):
			previous = target.read_bytes() if target.exists() else None
			self.__check_expected(previous)
			if None is not previous and previous != payload:
				write_immutable_bytes(pp.data_dir / 'analysis-history' / (df_sha256(previous) + '.json'), previous)
			if (target.read_bytes() if target.exists() else None) != previous:
				raise ValueError('Analysis changed during commit; external edit preserved')
			if None is previous:
				create_bytes(target, payload)
			elif previous != payload:
				replace_bytes(target, payload)
		return str(target)
	# @used-by :func:`agent_tools.analysis.save_analysis()`
	# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.save()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_analysis_merger_and_lifecycle_classes()`
	def save(self) -> dict:
		from agent_tools.path_registry import project_paths
		from agent_tools.research import inside
		pp = project_paths(self.__root, exact_root=True)
		value = self.__candidate if isinstance(self.__candidate, dict) else json.loads(inside(pp.root, self.__candidate).read_text(encoding='utf-8-sig'))
		IssueValidator(Validator(value).issues()).require_valid()
		Validator.require_current_contract(value)
		IssueValidator(EvidenceAuditor(pp.root, value, skip_structural=True).issues()).require_valid()
		payload = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
		target = self.__commit_locked(pp, payload)
		return {'target': target, 'sha256': df_sha256(payload), 'schema_valid': True, 'evidence_checked': True, 'detail': 'Primary references checked; update dependent agent KB modules before independent semantic review'}