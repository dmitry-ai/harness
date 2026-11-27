# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from Df.Harness.Grounding.LocaleVerifier import LocaleVerifier
from Df.Harness.Grounding.ResponseAuditor import ResponseAuditor
from Df.Harness.Issue.IssueFirstPreToolEvaluator import IssueFirstPreToolEvaluator
from Df.Harness.Issue.TurnAuditor import TurnAuditor
from Df.Harness.lib.text_sections import dfh_validate_ref_range
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DfHarnessS11Wave2CCovTailTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_grounding_ingestor_kb_membership_and_locale_fallback(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'ꘖ/data').mkdir(parents=True)
			ev = root / 'ꘖ/KB/Evidence/obs1'
			ev.mkdir(parents=True)
			(ev / 'response.bin').write_text('<html><head><title>Doc Guide</title></head><body><h2 id="sec-a">Section A</h2><p>Observed verbatim text for full bundle ingestion check.</p></body></html>', encoding='utf-8')
			(ev / 'observation.json').write_text(json.dumps({'url': 'https://docs.example.com/guide', 'final_url': 'https://docs.example.com/guide', 'status': 200, 'content_type': 'text/html'}), encoding='utf-8')
			(root / 'ꘖ/KB/Notes.md').write_text('Reference https://docs.example.com/guide\n', encoding='utf-8')
			from agent_tools.path_registry import project_paths
			pjson = project_paths(root, exact_root=True).project_json
			pjson.parent.mkdir(parents=True, exist_ok=True)
			pjson.write_text('{}\n', encoding='utf-8')
			resp = 'See [Doc Guide](https://docs.example.com/guide#sec-a).\n\n> «Observed verbatim text for full bundle ingestion check.»\n'
			self.assertEqual([], ResponseAuditor(root, resp, requests=[]).validate())
			errs = LocaleVerifier('English prose with enough words to trigger Russian default check.', target_locale='und', container_text='[df-analysis](slashCommand;df-analysis)', default_locale='ru-RU').verify()
			self.assertTrue(bool(errs))
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_issue_build_write_event_parent_linked_urls_and_dense_range(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			ev = root / 'ꘖ/KB/Evidence/GitHub/o__r'
			ev.mkdir(parents=True)
			(root / '.git').mkdir()
			(root / '.git/config').write_text('[remote "origin"]\n\turl = https://github.com/o/r.git\n', encoding='utf-8')
			(ev / 'issue-5.json').write_text(json.dumps({'issue': {'number': 5, 'state': 'open', 'body': 'Parent'}}), encoding='utf-8')
			(ev / 'issue-10.json').write_text(json.dumps({'issue': {'number': 10, 'state': 'closed', 'parent_number': 5, 'body': 'Parent: #5'}}), encoding='utf-8')
			with patch('Df.Harness.Git.RepoGate.RepoGate.is_issue_tracked', return_value=True):
				write_ev = IssueFirstPreToolEvaluator.build_code_write_event(1, root / 'a.py', cwd=root, content='x = 1\n', sub_step=0)
			self.assertEqual('o/r', write_ev['repo_slug'])
			aud = TurnAuditor(root, {'touched_files': []}, None, '- M-1: first change.\n- M-2: second change.\n')
			aud.repo_touched[root.resolve()] = {'a.py'}
			aud.turn_issues['https://github.com/o/r/issues/10'] = {'repo': 'o/r', 'number': 10, 'parent_number': 5, 'state': 'closed', 'actions': ['create']}
			aud.check_multi_subtask_decomposition({root.resolve(): {'https://github.com/o/r/issues/10'}}, {root.resolve(): {'https://github.com/o/r/issues/10'}})
			self.assertTrue(any(('requires a parent problem issue' in v for v in aud.violations)))
			findings: list = []
			dfh_validate_ref_range('1.1', '1.3', {'1.1', '1.3'}, findings, 1, '§§1.1–1.3', order_key=lambda k: tuple(map(int, k.split('.'))), check_dense=True)
			self.assertTrue(any(('1.2' in f.message for f in findings)))
if '__main__' == __name__:
	unittest.main()
