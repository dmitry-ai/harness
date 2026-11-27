# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Review.ReportValidator import REVIEW_SCHEMA
from Df.Qa.lib.validation.check_strict import df_is_sne
from agent_tools.research import inside, json_data
from agent_tools.storage import write_immutable_bytes
import json
_DIFF_ERR = 'Immutable review artifact differs; preserve the original and create a new attempt'
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class DispositionRecorder:
	# @used-by :func:`agent_tools.review.disposition()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests._exercise_review_record_and_auth()`
	def __init__(self, root, review_id: str, finding_id: str, status: str, basis: str, evidence: list, parent_id: str, *, inside_fn=None) -> None:
		self.__root = Path(root).resolve()
		self.__review_id = review_id
		self.__finding_id = finding_id
		self.__status = status
		self.__basis = basis
		self.__evidence = evidence
		self.__parent_id = parent_id
		self.__inside = inside if None is inside_fn else inside_fn
	# @used-by :meth:`DispositionRecorder.record()`
	def __validate_entry(self, state: dict) -> None:
		entry = next((r for r in state['reviews'] if r.get('id') == self.__review_id), None)
		if not entry or REVIEW_SCHEMA != entry.get('schema_version') or entry['parent_id'] != self.__parent_id:
			raise ValueError('Current parent and immutable review ID required')
		data = json.loads(self.__inside(self.__root, entry['report']).read_text(encoding='utf-8'))
		if self.__finding_id not in {f['id'] for f in data['findings']}:
			raise ValueError('Finding does not exist in the original report')
	# @used-by :func:`agent_tools.review.disposition()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests._exercise_review_record_and_auth()`
	def record(self) -> dict:
		from Df.Harness.Workflow.HashCollector import HashCollector
		from Df.Harness.Workflow.StateLoader import StateLoader
		from Df.Harness.Workflow.StateUpdater import StateUpdater
		from agent_tools.path_registry import project_paths
		from agent_tools.platforms import adapter
		if self.__status not in ('resolved', 'rejected') or not df_is_sne(self.__basis) or (not self.__evidence):
			raise ValueError('Disposition needs resolved/rejected status, basis and saved evidence')
		adapter().require_current_binding(self.__root, self.__parent_id)
		self.__validate_entry(StateLoader(self.__root).load())
		payload = {'schema_version': 1, 'review_id': self.__review_id, 'finding_id': self.__finding_id, 'parent_id': self.__parent_id, 'status': self.__status, 'basis': self.__basis, 'evidence': HashCollector(self.__root, self.__evidence).collect(), 'time': HashCollector.utc_now()}
		encoded = json_data(payload)
		target = write_immutable_bytes(project_paths(self.__root, exact_root=True).evidence_dir / 'Reviews/Dispositions' / (df_sha256(encoded) + '.json'), encoded, diff_error=_DIFF_ERR)
		relative = target.relative_to(self.__root).as_posix()
		# @used-by :meth:`DispositionRecorder.record()`
		def change(current: dict) -> None:
			saved = next((r for r in current['reviews'] if r.get('id') == self.__review_id))
			saved.setdefault('dispositions', []).append({'file': relative, 'proof': HashCollector(self.__root, [relative, *payload['evidence']]).collect()})
		return StateUpdater(self.__root, {'action': 'review_disposition', 'review_id': self.__review_id, 'finding_id': self.__finding_id}, change).update()
