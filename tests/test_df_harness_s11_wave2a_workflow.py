# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
from unittest import mock
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
# @used-by :meth:`DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
# @used-by :meth:`DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
# @used-by :meth:`DfHarnessS11Wave2aWorkflowTests.test_z_workflow_adopt_answer_complete_and_finalize()`
# @used-by :meth:`DfHarnessS11Wave2aWorkflowTests.test_z_workflow_attachment_auditor_branches()`
def _seed_project(root: Path) -> Path:
	from agent_tools.path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	snap_dir = pp.evidence_dir / 'Upwork'
	snap_dir.mkdir(parents=True, exist_ok=True)
	pp.project_json.parent.mkdir(parents=True, exist_ok=True)
	snap = {'job_id': '~01wf', 'title': 'Audit Store', 'description': 'Check checkout.'}
	snap_b = json.dumps(snap).encode('utf-8')
	snap_sha = hashlib.sha256(snap_b).hexdigest()
	snap_file = snap_dir / f'{snap_sha}.json'
	snap_file.write_bytes(snap_b)
	pp.project_json.write_text(json.dumps({'job_id': '~01wf', 'snapshot': snap_file.relative_to(pp.root).as_posix()}), encoding='utf-8')
	return snap_file
# @used-by :mod:`unittest`
class DfHarnessS11Wave2aWorkflowTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_workflow_question_registry_and_auditors(self) -> None:
		from Df.Harness.Workflow.AnalysisCardAuditor import AnalysisCardAuditor
		from Df.Harness.Workflow.AttachmentAuditor import AttachmentAuditor
		from Df.Harness.Workflow.HealthAuditor import HealthAuditor
		from Df.Harness.Workflow.KbAuditor import KbAuditor
		from Df.Harness.Workflow.QuestionAdder import QuestionAdder
		from Df.Harness.Workflow.QuestionClaimer import QuestionClaimer
		from Df.Harness.Workflow.QuestionContractAuditor import QuestionContractAuditor
		from Df.Harness.Workflow.QuestionFinisher import QuestionFinisher
		from Df.Harness.Workflow.QuestionHandoff import QuestionHandoff
		from Df.Harness.Workflow.QuestionRegistry import QuestionRegistry
		from Df.Harness.Workflow.QuestionSearchRecorder import QuestionSearchRecorder
		from Df.Harness.Workflow.StageEngine import StageEngine
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			snap_rel = _seed_project(root).relative_to(root).as_posix()
			req = [{'id': 'R-1', 'claim': 'Site responds', 'property': 'content', 'method': 'http', 'scope': {'objects': ['https://example.com']}, 'conditions': {'session': {'mode': 'unknown'}}, 'expected': '200', 'falsification': '500', 'discriminating_test': 'GET', 'completion_criterion': 'Saved', 'alternatives': ['CDN'], 'assertions': []}]
			QuestionAdder(root, 'Q-1', 'Check site', 'High', 'Saved', [snap_rel], ['\ua616/KB/out.md'], requirements=req).add()
			QuestionClaimer(root, 'Q-1', 'worker-1').claim()
			QuestionSearchRecorder(root, 'Q-1', 'worker-1', 'site checkout', True).record()
			QuestionHandoff(root, 'Q-1', 'worker-1', 'worker-2', 'Context limit').handoff()
			state = StageEngine(root).load()
			self.assertEqual('worker-2', state['questions']['Q-1']['owner'])
			self.assertTrue(QuestionContractAuditor(root, state['questions']['Q-1']).issues())
			self.assertFalse(QuestionRegistry(root).current(state))
			self.assertEqual([], AttachmentAuditor(root).issues())
			self.assertEqual([], KbAuditor(root).issues())
			self.assertTrue(AnalysisCardAuditor(root, root / '\ua616/KB/Analysis.json').issues())
			self.assertFalse(HealthAuditor(root).check_project()['valid'])
			self.assertTrue(callable(QuestionFinisher))
	# @used-by :mod:`unittest`
	def test_workflow_stage_engine_and_helpers(self) -> None:
		from Df.Harness.Workflow.AnswerRecorder import AnswerRecorder
		from Df.Harness.Workflow.FinalizeStageRunner import FinalizeStageRunner
		from Df.Harness.Workflow.HashCollector import HashCollector
		from Df.Harness.Workflow.ProgressPublisher import ProgressPublisher
		from Df.Harness.Workflow.ReceiptVerifier import ReceiptVerifier
		from Df.Harness.Workflow.RegistrationStatusChecker import RegistrationStatusChecker
		from Df.Harness.Workflow.RequestAdopter import RequestAdopter
		from Df.Harness.Workflow.RequestUnadopter import RequestUnadopter
		from Df.Harness.Workflow.StageCompleter import StageCompleter
		from Df.Harness.Workflow.StageEngine import StageEngine
		from Df.Harness.Workflow.StageStatusEvaluator import StageStatusEvaluator
		from Df.Harness.Workflow.StateLoader import StateLoader
		from Df.Harness.Workflow.StateUpdater import StateUpdater
		from Df.Harness.Workflow.StatusSnapshotBuilder import StatusSnapshotBuilder
		from Df.Harness.Workflow.WorkflowResumer import WorkflowResumer
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			snap_file = _seed_project(root)
			hmap = HashCollector(root, [snap_file.relative_to(root).as_posix()]).collect()
			self.assertEqual(64, len(HashCollector.file_hash(snap_file)))
			self.assertTrue(HashCollector.utc_now().endswith('+00:00') and ReceiptVerifier(root, {'inputs': hmap}).is_current())
			self.assertTrue(StateLoader(root).load()['legacy'] and str(StateLoader.state_path(root)).endswith('workflow.json'))
			self.assertEqual('complete', WorkflowResumer(root, 'Resume analysis', 'Check checkout.').resume()['stages']['capture'])
			state1 = StageEngine(root).load()
			statuses = StageStatusEvaluator(root, state1).evaluate()
			self.assertEqual('complete', statuses['capture'])
			self.assertTrue(RegistrationStatusChecker.target_complete('codex', {'complete': True}) and 'complete' in RegistrationStatusChecker(root).status())
			self.assertEqual('~01wf', StatusSnapshotBuilder(root, state=state1, statuses=statuses).build()['job_id'])
			ProgressPublisher(root, state1, statuses=statuses).publish()
			self.assertTrue((root / '\ua616/KB/Progress.md').is_file())
			self.assertEqual('~01wf', StateUpdater(root, {'action': 'note'}, lambda s: None).update()['job_id'])
			self.assertTrue(all((callable(c) for c in (AnswerRecorder, FinalizeStageRunner, RequestAdopter, RequestUnadopter, StageCompleter))))
	# @used-by :mod:`unittest`
	def test_z_workflow_adopt_answer_complete_and_finalize(self) -> None:
		from Df.Harness.Workflow.QuestionFinisher import QuestionFinisher
		from Df.Harness.Workflow.QuestionRegistry import QuestionRegistry
		from Df.Harness.Workflow.StageEngine import StageEngine
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			snap_rel = _seed_project(root).relative_to(root).as_posix()
			(root / '\ua616/KB/out.md').write_text('# Out\nDone.  \n', encoding='utf-8')
			eng = StageEngine(root)
			eng.resume('start', 'Check site.')
			self.assertEqual(root / '\ua616/data/workflow.json', eng.state_path())
			with mock.patch('agent_tools.metrics.native_requests', return_value=[{'id': 'req-1', 'text': 'Check site.', 'native_conversation_id': 'cid-1'}]):
				eng.adopt_requests('cid-1')
			eng.unadopt_requests(request_ids=['nonexistent'])
			reply = 'Checked site.  \n'
			r_sha = hashlib.sha256(reply.encode('utf-8')).hexdigest()
			ans = eng.record_current_answer(reply, preauthorized={'package': snap_rel, 'response_sha256': r_sha, 'review_ids': ['r1']})
			self.assertTrue(ans['journal_steps'])
			req = [{'id': 'R-1', 'claim': 'Site responds', 'property': 'content', 'method': 'http', 'scope': {'objects': ['https://example.com']}, 'conditions': {'session': {'mode': 'unknown'}}, 'expected': '200', 'falsification': '500', 'discriminating_test': 'GET', 'completion_criterion': 'Saved', 'alternatives': ['CDN'], 'assertions': []}]
			reg = QuestionRegistry(root)
			reg.add('Q-2', 'Check', 'High', 'Saved', [snap_rel], ['\ua616/KB/out.md'], requirements=req)
			reg.claim('Q-2', 'w1')
			reg.record_search('Q-2', 'w1', 'query', True)
			reg.handoff('Q-2', 'w1', 'w2', 'done')
			with self.assertRaises(ValueError):
				QuestionFinisher(root, 'Q-2', 'w2', ['\ua616/KB/out.md'], gap='gap', results=[]).finish()
			self._exercise_stage_completer_and_auditors(root, snap_rel, eng, r_sha)
	# @used-by :meth:`DfHarnessS11Wave2aWorkflowTests.test_z_workflow_adopt_answer_complete_and_finalize()`
	def _exercise_stage_completer_and_auditors(self, root: Path, snap_rel: str, eng, r_sha: str) -> None:
		from Df.Harness.Workflow.FinalizeStageRunner import FinalizeStageRunner
		from Df.Harness.Workflow.HealthAuditor import HealthAuditor
		from Df.Harness.Workflow.KbAuditor import KbAuditor
		from Df.Harness.Workflow.StageCompleter import StageCompleter
		(root / '\ua616/KB/bad.md').write_text('| A | B |\n|---|---|\n| 1 | 2 |\n', encoding='utf-8')
		(root / '\ua616/data/tmp.py').write_text('x = 1\n', encoding='utf-8')
		(root / '.md').write_text('[bad](a%20b.md)\n', encoding='utf-8')
		self.assertTrue(KbAuditor(root).issues() and HealthAuditor(root).check_project()['issues'])
		self.assertIsInstance(KbAuditor.doc4_sentence_issues('One. Two.'), list)
		eng.complete_stage('identity_init', [snap_rel], ['\ua616/KB/out.md'])
		eng.invalidate_caches()
		self.assertIsInstance(eng.evidence_hashes(), dict)
		self.assertIsInstance(eng.kb_hashes(), dict)
		self.assertIsInstance(eng.publish_progress(eng.load()), dict)
		self.assertIsInstance(eng.status(), dict)
		self.assertTrue(eng.receipt_current({'inputs': {}}))
		with self.assertRaises(ValueError):
			StageCompleter(root, 'finalize', [snap_rel], ['\ua616/KB/out.md']).complete()
		state = eng.load()
		j_reply = next((p for p in (root / '\ua66e').rglob('1.md') if '\u227a' in p.parts))
		j_rel = j_reply.relative_to(root).as_posix()
		with mock.patch('Df.Harness.Project.FinalizeDriftGuard.FinalizeDriftGuard.require', return_value=None):
			out = FinalizeStageRunner(root, state, {j_rel: 'x'}, [j_rel], authorize_fn=lambda *a, **kw: {'response_sha256': r_sha}).run()
			self.assertEqual(r_sha, out['response_sha256'])
	# @used-by :mod:`unittest`
	def test_z_workflow_attachment_auditor_branches(self) -> None:
		from Df.Harness.Workflow.AttachmentAuditor import AttachmentAuditor
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			snap_file = _seed_project(root)
			snap = json.loads(snap_file.read_text(encoding='utf-8'))
			snap['description'] = 'See https://www.loom.com/share/abc12345'
			ev_dir = root / '\ua616/KB/Evidence/Attachments'
			txt_b, img_b = (b'Doc body.', b'\x89PNG\r\n\x1a\n')
			for fname, data in (('notes.txt', txt_b), ('shot.png', img_b)):
				sha = hashlib.sha256(data).hexdigest()
				p = ev_dir / sha / fname
				p.parent.mkdir(parents=True, exist_ok=True)
				p.write_bytes(data)
				snap.setdefault('asset_evidence', []).append({'file': p.relative_to(root).as_posix(), 'sha256': sha})
			snap_file.write_text(json.dumps(snap), encoding='utf-8')
			(root / '\ua616/KB/Project.md').write_text('Description in `shot.png`\n~~~markdown\nbad\n~~~\nDescription in https://loom.com/share/abc12345\n', encoding='utf-8')
			codes = {i['code'] for i in AttachmentAuditor(root).issues()}
			self.assertTrue({'attachment.kb_missing', 'attachment.image_incomplete', 'attachment.video_incomplete'}.issubset(codes))
if '__main__' == __name__:
	unittest.main()
