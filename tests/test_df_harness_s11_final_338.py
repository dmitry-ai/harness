# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import ast
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
CORPUS_DIR = WT_ROOT / 'tests/fixtures/feature_turns'
for p in (SCRIPTS, TESTS):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
# @used-by :meth:`DfHarnessS11Final338Tests.test_doc5_replay_auditor_saved_turns_and_worktree_verify()`
def _git(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', check=True, timeout=30)
	return (proc.stdout or '').strip()
# @used-by :meth:`DfHarnessS11Final338Tests.test_whole_repo_s11_invariants_after_final_migration()`
def _public_instance_method_count(cls_node: ast.ClassDef) -> int:
	r = 0
	for item in cls_node.body:
		if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
			continue
		if item.name.startswith('_'):
			continue
		decs = {d.id for d in item.decorator_list if isinstance(d, ast.Name)}
		if decs & {'staticmethod', 'classmethod', 'property'}:
			continue
		r += 1
	return r
# @used-by :meth:`DfHarnessS11Final338Tests.test_doc5_replay_auditor_saved_turns_and_worktree_verify()`
def _seed_saved_turns(proj: Path, backend: Path) -> str:
	from test_stop_emergency_capture_and_foreign_sync import _seed_ag_conversation
	turns_dir = proj / '\ua616/data/turns'
	res_dir = proj / '\ua66e/\u227a/1\u201320'
	turns_dir.mkdir(parents=True)
	res_dir.mkdir(parents=True)
	(turns_dir / 'badjson.json').write_text('{broken', encoding='utf-8')
	(turns_dir / 'pending.json').write_text(json.dumps({'key': 'pending', 'status': 'prepared', 'conversation_id': 'c0'}), encoding='utf-8')
	prob_rf = res_dir / '1.md'
	prob_rf.write_text('# 0. Problem Metadata\n', encoding='utf-8')
	(turns_dir / 'probturn.json').write_text(json.dumps({'key': 'probturn', 'status': 'delivered', 'platform': 'antigravity', 'conversation_id': 'c1', 'prepared': {'response_file': str(prob_rf)}}), encoding='utf-8')
	(turns_dir / 'missingbe.json').write_text(json.dumps({'key': 'missingbe', 'status': 'delivered', 'platform': 'antigravity', 'conversation_id': 'c2', 'native_backend': str(backend / 'nope')}), encoding='utf-8')
	cid = '12345678-1111-2222-3333-444444444444'
	tx = _seed_ag_conversation(backend, proj, cid, 'Run task', 'Done cleanly.  \n')
	rows = [
		{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Run task'},
		{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'content': 'Done cleanly.  \n', 'tool_calls': []},
	]
	tx.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in rows)), encoding='utf-8')
	clean_rf = res_dir / '2.md'
	clean_rf.write_text('Done cleanly.  \n', encoding='utf-8')
	state = {'key': 'cleankey', 'status': 'delivered', 'platform': 'antigravity', 'conversation_id': cid, 'native_backend': str(backend), 'native_turn_id': 'unmatched-id', 'prepared': {'response_file': str(clean_rf)}}
	(turns_dir / 'cleankey.json').write_text(json.dumps(state), encoding='utf-8')
	return 'cleankey'
# @used-by :mod:`unittest`
class DfHarnessS11Final338Tests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_cli_output_json_parser_and_facade_cover_all_branches(self) -> None:
		from Df.Harness.Grounding.CliOutputJsonParser import CliOutputJsonParser
		from agent_tools.cli_output_json import extract_top_level_json_objects, top_level_json_has_failure
		nested_body = 'Command output:\n{\n  "ok": true,\n  "sub": {\n"valid": false\n  }\n}\n'
		objs, trunc = CliOutputJsonParser.extract_objects(nested_body)
		self.assertEqual(1, len(objs))
		self.assertFalse(trunc)
		self.assertFalse(CliOutputJsonParser(nested_body).has_failure())
		self.assertEqual((objs, trunc), extract_top_level_json_objects(nested_body))
		self.assertFalse(top_level_json_has_failure(nested_body))
		self.assertTrue(CliOutputJsonParser('{"ok": false, "nested": {').has_failure())
		self.assertTrue(CliOutputJsonParser('{\n  "valid": false\n').has_failure())
		self.assertFalse(CliOutputJsonParser('{\n    "valid": false\n').has_failure())
		self.assertFalse(CliOutputJsonParser('').has_failure())
		self.assertFalse(CliOutputJsonParser('{').has_failure())
		self.assertEqual(([], False), CliOutputJsonParser.extract_objects('[1, 2]\n'))
		self.assertTrue(top_level_json_has_failure('{"valid": true}\n{"ok": false}\n'))
	# @used-by :mod:`unittest`
	def test_doc5_replay_auditor_corpus_and_subprocess(self) -> None:
		from Df.Harness.Grounding.Doc5ReplayAuditor import Doc5ReplayAuditor
		from agent_tools import doc5_replay_audit
		clean = Doc5ReplayAuditor.audit_corpus(CORPUS_DIR)
		self.assertTrue(clean['valid'], clean)
		self.assertEqual(3, clean['checked'])
		self.assertEqual(clean['checked'], doc5_replay_audit.audit_feature_turn_corpus(CORPUS_DIR)['checked'])
		all_true = Doc5ReplayAuditor.audit_corpus(CORPUS_DIR, checker_fn=lambda _ctx: True)
		self.assertFalse(all_true['valid'])
		self.assertEqual(2, len(all_true['false_positives']))
		all_false = Doc5ReplayAuditor.audit_corpus(CORPUS_DIR, checker_fn=lambda _ctx: False)
		self.assertFalse(all_false['valid'])
		self.assertEqual(1, len(all_false['false_negatives']))
		with tempfile.TemporaryDirectory() as td:
			missing = Path(td) / 'missing'
			empty = Doc5ReplayAuditor.audit_corpus(missing)
			self.assertFalse(empty['valid'])
			self.assertEqual(0, empty['checked'])
			bad_sub = Doc5ReplayAuditor.run_worktree_corpus_subprocess(Path(td), missing)
			self.assertFalse(bad_sub['valid'])
		sub_ok = Doc5ReplayAuditor.run_worktree_corpus_subprocess(WT_ROOT, CORPUS_DIR)
		self.assertTrue(sub_ok['valid'], sub_ok)
		self.assertEqual(3, sub_ok['checked'])
		self.assertFalse(sub_ok['skipped'])
	# @used-by :mod:`unittest`
	def test_doc5_replay_auditor_saved_turns_and_worktree_verify(self) -> None:
		from Df.Harness.Grounding.Doc5ReplayAuditor import Doc5ReplayAuditor
		from agent_tools import doc5_replay_audit
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			key = _seed_saved_turns(base / 'proj', base / 'backend')
			clean = Doc5ReplayAuditor.audit_saved_turns(base / 'proj', limit=1)
			self.assertTrue(clean['valid'], clean)
			self.assertEqual(1, clean['checked'])
			flagged = Doc5ReplayAuditor.audit_saved_turns(base / 'proj', limit=5, checker_fn=lambda _ctx: True)
			self.assertFalse(flagged['valid'])
			self.assertEqual([key], flagged['false_positives'])
			repo = base / 'repo'
			(repo / 'scripts/Df/Harness/Grounding').mkdir(parents=True)
			(repo / 'tests/fixtures/feature_turns').mkdir(parents=True)
			_git(repo, 'init', '-b', 'main')
			_git(repo, 'config', 'user.email', 't@example.com')
			_git(repo, 'config', 'user.name', 'T')
			(repo / 'scripts/Df/Harness/Grounding/Doc5ReplayAuditor.py').write_text('x = 1\n', encoding='utf-8')
			(repo / 'tests/fixtures/feature_turns/01.json').write_text('{}\n', encoding='utf-8')
			_git(repo, 'add', '.')
			_git(repo, 'commit', '--no-verify', '-m', 'init')
			_git(repo, 'checkout', '-b', 'feat')
			(repo / 'readme.txt').write_text('hi\n', encoding='utf-8')
			_git(repo, 'add', 'readme.txt')
			_git(repo, 'commit', '--no-verify', '-m', 'doc')
			skipped = Doc5ReplayAuditor(repo, 'main').verify_worktree()
			self.assertTrue(skipped['valid'])
			self.assertTrue(skipped['skipped'])
			(repo / 'scripts/Df/Harness/Grounding/Doc5ReplayAuditor.py').write_text('x = 2\n', encoding='utf-8')
			_git(repo, 'add', 'scripts/Df/Harness/Grounding/Doc5ReplayAuditor.py')
			_git(repo, 'commit', '--no-verify', '-m', 'gate')
			stub = {'valid': True, 'skipped': False, 'checked': 1, 'false_positives': [], 'false_negatives': []}
			ran = Doc5ReplayAuditor(repo, 'main', subprocess_runner=lambda _w, _f: dict(stub)).verify_worktree()
			self.assertTrue(ran['valid'])
			self.assertIn('scripts/Df/Harness/Grounding/Doc5ReplayAuditor.py', ran['touched_gates'])
			with patch.object(doc5_replay_audit, '_run_worktree_corpus_subprocess', return_value=dict(stub)):
				fac = doc5_replay_audit.verify_worktree_answer_gate_corpus(repo, 'main')
			self.assertTrue(fac['valid'])
	# @used-by :mod:`unittest`
	def test_draft_snapshotter_and_facade_cover_capture_verify_and_errors(self) -> None:
		from Df.Harness.Text.DraftSnapshotter import DraftSnapshotter
		from agent_tools.snapshot import snapshot_draft
		with tempfile.TemporaryDirectory() as td:
			proj = Path(td).resolve()
			(proj / '\ua616/data').mkdir(parents=True)
			other = proj / 'notes.md'
			other.write_text('hello', encoding='utf-8')
			with self.assertRaisesRegex(ValueError, 'explicit draft.md'):
				DraftSnapshotter(other, 'turn-1').snapshot()
			draft = proj / 'draft.md'
			draft.write_text('v1 content', encoding='utf-8')
			with self.assertRaisesRegex(ValueError, 'Turn ID'):
				DraftSnapshotter(draft, 'bad turn!').snapshot()
			saved = DraftSnapshotter(draft, 'turn-1').snapshot()
			self.assertTrue(saved.is_file())
			self.assertEqual(b'v1 content', saved.read_bytes())
			self.assertEqual(b'v1 content', (proj / 'draft.prev.md').read_bytes())
			self.assertEqual(saved, snapshot_draft(draft, 'turn-1'))
			(proj / 'draft.prev.md').write_text('edited prev', encoding='utf-8')
			with self.assertRaisesRegex(ValueError, 'draft.prev.md changed'):
				DraftSnapshotter(draft, 'turn-1').snapshot()
			(proj / 'draft.prev.md').write_bytes(b'v1 content')
			saved.write_bytes(b'tampered')
			with self.assertRaisesRegex(ValueError, 'Snapshot changed'):
				DraftSnapshotter(draft, 'turn-1').snapshot()
			saved.write_bytes(b'v1 content')
			receipt_p = saved.with_name('snapshot.json')
			receipt = json.loads(receipt_p.read_text(encoding='utf-8'))
			receipt['source'] = str(proj / 'other/draft.md')
			receipt_p.write_text(json.dumps(receipt), encoding='utf-8')
			with self.assertRaisesRegex(ValueError, 'different source'):
				DraftSnapshotter(draft, 'turn-1').snapshot()
	# @used-by :mod:`unittest`
	def test_whole_repo_s11_invariants_after_final_migration(self) -> None:
		non_df_classes: list[str] = []
		multi_class: list[str] = []
		stem_mismatch: list[str] = []
		total_classes = 0
		single_pub_method = 0
		for py in sorted(SCRIPTS.rglob('*.py')):
			rel = py.relative_to(SCRIPTS).as_posix()
			tree = ast.parse(py.read_text(encoding='utf-8'))
			classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
			if not rel.startswith('Df/'):
				if classes:
					non_df_classes.append(rel)
			elif rel.startswith('Df/Harness/') and (not rel.startswith('Df/Harness/lib/')) and ('__init__.py' != py.name):
				if 1 != len(classes):
					multi_class.append(rel)
				elif classes[0].name != py.stem:
					stem_mismatch.append(rel)
				else:
					total_classes += 1
					if 1 >= _public_instance_method_count(classes[0]):
						single_pub_method += 1
		self.assertEqual([], non_df_classes)
		self.assertEqual([], multi_class)
		self.assertEqual([], stem_mismatch)
		self.assertGreaterEqual(total_classes, 550)
		self.assertGreaterEqual(single_pub_method / total_classes, 0.85)
if '__main__' == __name__:
	unittest.main()
