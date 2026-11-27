# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-27 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
# @used-by :mod:`unittest`
class DfHarnessS11Wave2aFacadeExportsTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_review_facade_reexports_json_data(self) -> None:
		from agent_tools import research, review
		payload = {'b': 1, 'a': 2}
		self.assertEqual(research.json_data(payload), review.json_data(payload))
	# @used-by :mod:`unittest`
	def test_stage_completer_passes_platform_and_targets_to_registry_register(self) -> None:
		from Df.Harness.Project.Registry import Registry
		from Df.Harness.Workflow.StageCompleter import StageCompleter
		from unittest import mock
		import tempfile
		calls: list[dict] = []
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			(root / '\ua616/KB/Evidence').mkdir(parents=True, exist_ok=True)
			(root / '\ua616/project.json').write_text('{"initialized": true, "job_id": "~01test"}\n', encoding='utf-8')
			(root / '\ua616/KB/Evidence/init.json').write_text('{}\n', encoding='utf-8')
			reg_state = {'platform': 'codex', 'required': True, 'complete': True, 'all_registered': False, 'pending_targets': ['antigravity']}
			with mock.patch('Df.Harness.Workflow.RegistrationStatusChecker.RegistrationStatusChecker.status', return_value=reg_state), mock.patch.object(Registry, 'register', side_effect=lambda **kw: calls.append(kw) or {'complete': True}):
				StageCompleter(root, 'identity_init', ['\ua616/project.json'], ['\ua616/KB/Evidence/init.json'], update_fn=lambda r, ev, fn: {'action': ev['action']}).complete()
		self.assertEqual([{'platform': 'codex', 'targets': ['codex', 'antigravity']}], calls)
	# @used-by :mod:`unittest`
	def test_upwork_project_facade_reexports_normalize_job_id(self) -> None:
		from agent_tools import upwork_project
		self.assertEqual('~021234567890', upwork_project.normalize_job_id('https://www.upwork.com/jobs/~021234567890'))
if '__main__' == __name__:
	unittest.main()
