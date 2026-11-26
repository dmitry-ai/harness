# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import check_markdown_slop
from agent_tools import workflow
# 2026-11-24
# "Unify PreToolUse/Stop JSON hook harnesses, turns/*.json iterators, DOC-4 sentence scanning, and GitHub Evidence resolvers":
# https://github.com/dmitry-ai/harness/issues/79
class HookUnificationTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_doc4_scanner_supports_hook_and_workflow_modes(self):
		from agent_tools import hook_runtime
		hook_doc = '---\ntitle: Demo\n---\nFirst sentence here. Second sentence on same line.\nNext run-on line\n'
		hook_issues = hook_runtime.scan_doc4_sentence_issues(hook_doc, mode='hook')
		self.assertEqual(hook_issues, check_markdown_slop.markdown_slop_issues(hook_doc))
		self.assertTrue(any(('multiple sentences' in item for item in hook_issues)))
		self.assertTrue(any(('hard line break' in item for item in hook_issues)))
		wf_doc = '- **Item**: First sentence here. Second sentence ends here.\nAlpha beta gamma delta. Epsilon zeta eta theta.\n'
		wf_issues = hook_runtime.scan_doc4_sentence_issues(wf_doc, mode='workflow')
		self.assertEqual(wf_issues, workflow.doc4_sentence_issues(wf_doc))
		self.assertEqual(2, len(wf_issues))
	# @used-by :mod:`unittest`
	def test_iter_turn_state_files_skips_aux_files(self):
		from agent_tools import hook_runtime
		with tempfile.TemporaryDirectory() as tmp:
			tdir = Path(tmp)
			(tdir / 'turn1.json').write_text(json.dumps({'status': 'open', 'id': 1}), encoding='utf-8')
			(tdir / 'turn1-checkpoint-recovery.json').write_text(json.dumps({'status': 'open'}), encoding='utf-8')
			(tdir / 'turn1-similar-exemptions.json').write_text(json.dumps({'status': 'open'}), encoding='utf-8')
			(tdir / 'broken.json').write_text('{bad', encoding='utf-8')
			loaded = hook_runtime.iter_turn_state_files(tdir)
			self.assertEqual([('turn1.json', 1)], [(p.name, d['id']) for p, d in loaded])
	# @used-by :mod:`unittest`
	def test_read_last_user_segment_positional_and_by_step(self):
		from agent_tools import hook_runtime
		with tempfile.TemporaryDirectory() as tmp:
			tfile = Path(tmp) / 'transcript_full.jsonl'
			rows = [
				{'step_index': 1, 'type': 'USER_INPUT', 'content': 'old'},
				{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'content': 'old reply'},
				{'step_index': 3, 'type': 'USER_INPUT', 'content': 'new'},
				{'step_index': 4, 'type': 'PLANNER_RESPONSE', 'content': 'new reply'},
			]
			tfile.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			_, last_idx, seg_pos = hook_runtime.read_last_user_segment(tfile)
			self.assertEqual(2, last_idx)
			self.assertEqual([4], [r['step_index'] for r in seg_pos])
			_, last_step, seg_step = hook_runtime.read_last_user_segment(tfile, by_step_index=True)
			self.assertEqual(3, last_step)
			self.assertEqual([4], [r['step_index'] for r in seg_step])
	# @used-by :mod:`unittest`
	def test_run_json_hook_dispatches_and_fails_open(self):
		from agent_tools import hook_runtime
		out_ok = io.StringIO()
		res_ok = hook_runtime.run_json_hook(lambda p: {'decision': 'deny', 'reason': p['k']}, stdin=io.StringIO('{"k":"blocked"}'), stdout=out_ok)
		self.assertEqual({'decision': 'deny', 'reason': 'blocked'}, res_ok)
		self.assertEqual({'decision': 'deny', 'reason': 'blocked'}, json.loads(out_ok.getvalue()))
		out_err = io.StringIO()
		# @used-by :meth:`HookUnificationTests.test_run_json_hook_dispatches_and_fails_open()`
		def boom(_payload):
			raise RuntimeError('transient')
		res_err = hook_runtime.run_json_hook(boom, stdin=io.StringIO('{"k":"x"}'), stdout=out_err)
		self.assertEqual({'decision': 'allow'}, res_err)
		self.assertEqual({'decision': 'allow'}, json.loads(out_err.getvalue()))
if '__main__' == __name__:
	unittest.main()
