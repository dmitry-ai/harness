# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :mod:`unittest`
class DfHarnessS11Wave2CTextFlowTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_claims_sources_and_cli_runner_classes(self) -> None:
		from Df.Harness.Research.Response import Response
		from Df.Harness.Text.ClaimMapValidator import ClaimMapValidator
		from Df.Harness.Text.ClaimRegistryStore import ClaimRegistryStore
		from Df.Harness.Text.CliRunner import CliRunner
		from Df.Harness.Text.IntakeSourceEvaluator import IntakeSourceEvaluator
		from Df.Harness.Text.SourceCheckValidator import SourceCheckValidator
		from Df.Harness.Text.SourceEvaluator import SourceEvaluator
		from Df.Harness.Text.SourceIntegrityChecker import SourceIntegrityChecker
		from Df.Harness.Text.SourceProber import SourceProber
		from Df.Harness.Text.SourceReceiptReader import SourceReceiptReader
		from Df.Harness.Text.SourceReceiptStore import SourceReceiptStore
		from Df.Harness.lib.text_claims import dfh_text_digest
		from Df.Harness.lib.text_sources import dfh_source_urls
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / '\ua616/data').mkdir(parents=True)
			(root / '\ua616/KB').mkdir(parents=True)
			text = 'Hello client.'
			manifest = {'schema_version': 1, 'blocks': [{'key': 'greet', 'section': '1', 'text_sha256': dfh_text_digest(text.encode()), 'role': 'nonfactual', 'goal_basis': 'Greeting', 'new_content': 'Opening', 'claim_ids': [], 'nonfactual_basis': 'Salutation'}]}
			self.assertTrue(ClaimMapValidator(root, text, 'letter', manifest).validate()['valid'])
			saved = ClaimRegistryStore(root, {'schema_version': 3, 'facts': []}).save()
			self.assertEqual(64, len(saved['sha256']))
			self.assertEqual(['https://example.org/p'], dfh_source_urls('See https://example.org/p for details.'))
			self.assertEqual([], SourceCheckValidator(root, 'No links here.', []).validate()['issues'])
			probed = SourceProber(root, 'See https://example.org/p for details.', fetcher=lambda u, _h, _t: Response(u, 200, 'text/html', b'<html><body>Valid page content here.</body></html>')).probe()
			self.assertEqual('http-ok', probed['results'][0]['status'])
			self.assertEqual([], probed['findings'])
			fields_f, limits_f = (root / 'fields.json', root / 'limits.json')
			fields_f.write_text(json.dumps({'cover': 'Hi'}), encoding='utf-8')
			limits_f.write_text(json.dumps({'cover': 20}), encoding='utf-8')
			self.assertEqual(0, CliRunner(['fields', '--fields', str(fields_f), '--limits', str(limits_f)]).run())
			self.assertTrue(all((callable(c) for c in (IntakeSourceEvaluator, SourceEvaluator, SourceReceiptStore, SourceReceiptReader, SourceIntegrityChecker))))
	# @used-by :mod:`unittest`
	def test_workspace_integrity_and_review_classes(self) -> None:
		from Df.Harness.Text.ApprovalIntegrityChecker import ApprovalIntegrityChecker
		from Df.Harness.Text.IntegrityVerifier import IntegrityVerifier
		from Df.Harness.Text.ReviewAuthorizer import ReviewAuthorizer
		from Df.Harness.Text.ReviewPackageReader import ReviewPackageReader
		from Df.Harness.Text.ReviewPreparer import ReviewPreparer
		from Df.Harness.Text.ReviewRecorder import ReviewRecorder
		from Df.Harness.Text.Workspace import Workspace
		from Df.Harness.Text.WorkspaceCheckRunner import WorkspaceCheckRunner
		from Df.Harness.Text.WorkspaceScopeChecker import WorkspaceScopeChecker
		from Df.Harness.lib.text_review import dfh_text_report_contract
		from agent_tools import text_workflow
		self.assertIs(Workspace, text_workflow.ClientTextWorkspace)
		self.assertIs(IntegrityVerifier, text_workflow.TextIntegrityVerifier)
		self.assertIn('evidence', dfh_text_report_contract()['required_scope'])
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / '\ua616/data').mkdir(parents=True)
			draft = root / 'draft.md'
			body = '1. Storefront returned status 200.\n'
			draft.write_bytes(body.encode('utf-8'))
			ws = Workspace(root, strict=True)
			op = ws.begin({'kind': 'proposal', 'mode': 'edit', 'changes': 'renumber', 'goal': 'Renumber points', 'requests': ['Renumber draft.md'], 'target': 'draft.md'})
			self.assertEqual([], WorkspaceScopeChecker(op, body, body).check())
			checked = WorkspaceCheckRunner(ws, op['id'], body).run()
			self.assertTrue(checked['valid'])
			self.assertEqual('mechanical', checked['coverage'])
			with self.assertRaises(ValueError):
				ReviewPreparer(root, checked['check'], 'parent-1').prepare()
			applied = ws.apply(checked['check'])
			self.assertEqual('applied', applied['status'])
			gated = ws.gate(targets=['draft.md'], capture=True)
			self.assertTrue(gated['valid'])
			self.assertTrue(IntegrityVerifier(ws).verify(gated['integrity'])['valid'])
			self.assertTrue(all((callable(c) for c in (ApprovalIntegrityChecker, ReviewAuthorizer, ReviewPackageReader, ReviewRecorder))))
if '__main__' == __name__:
	unittest.main()
