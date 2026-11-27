# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from Df.Harness.Project.LinkAudit import CHAT_REPLY_CALL_SITES, LinkAudit
from Df.Harness.Research.LinkAuditor import LinkAuditor
from agent_tools import links
from agent_tools.text_browser import GuardedCDP
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DfHarnessS11Wave2CCrossWaveTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_link_audit_accepts_wave2c_call_sites_and_guarded_cdp_class_seam(self) -> None:
		self.assertIn(('Df/Harness/lib/completion_links.py', 'dfh_response_link_issues'), CHAT_REPLY_CALL_SITES)
		self.assertEqual([], LinkAudit(SCRIPTS).audit())
		self.assertEqual(LinkAuditor.readable_link_issues, links.readable_link_issues)
		self.assertEqual([], links.readable_link_issues('[ok](file:///C:/a.md)', allow_unencoded_file_uri=True))
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'ꘖ/data').mkdir(parents=True)
			cfg = {'workspace_root': str(root), 'text': {'browser': {'sessions': {'s1': {'surface': 'browser', 'endpoint': 'http://127.0.0.1:9222', 'profile': {'path': '/tmp/p', 'argument': '--user-data-dir'}, 'allowed_operations': ['read'], 'target_url_patterns': ['https://example.com/*']}}}}}
			guard = GuardedCDP(root, {'session_id': 's1'}, config=cfg)
			self.assertTrue(hasattr(GuardedCDP, '_lock'))
			with patch('agent_tools.text_browser.GuardedCDP._broker_remove_tab', return_value='ok') as patched:
				self.assertEqual('ok', guard._broker_remove_tab(None, None, None, 't1'))
				self.assertTrue(patched.called)
			with patch('agent_tools.text_browser.GuardedCDP._broker_create_tab', return_value=('t2', None)) as patched_create:
				self.assertEqual(('t2', None), guard._broker_create_tab(None, None, None, 'https://example.com/a', 'http://127.0.0.1:9222'))
				self.assertTrue(patched_create.called)
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_turn_auditor_preserves_auditor_module_close_verify_patch_hook(self) -> None:
		from Df.Harness.Issue.TurnAuditor import TurnAuditor
		from agent_tools.issues import auditor as aud_mod
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			aud = aud_mod.TurnIssueLifecycleAuditor(root, {}, None)
			with patch.object(aud_mod, 'verify_repo_issue_ready_for_close', return_value={'verified': True, 'violations': []}) as mocked:
				aud._TurnAuditor__verify_required_repo_issues(root, {'https://github.com/o/r/issues/7'})
				self.assertTrue(mocked.called)
			try:
				TurnAuditor.bind_runtime_hooks(verify_fn=None)
				aud2 = TurnAuditor(root, {}, None)
				with patch('Df.Harness.Issue.TurnAuditor.RepoGate.verify_issue_ready_for_close', return_value={'verified': True, 'violations': []}) as rg_mock:
					aud2._TurnAuditor__verify_required_repo_issues(root, {'https://github.com/o/r/issues/8'})
					self.assertTrue(rg_mock.called)
			finally:
				TurnAuditor.bind_runtime_hooks(verify_fn=lambda *a, **kw: aud_mod.verify_repo_issue_ready_for_close(*a, **kw))
if '__main__' == __name__:
	unittest.main()
