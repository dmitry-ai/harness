# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract SourceDiagnosticsScanner class from diagnose_sources in text_diagnostics.py":
# https://github.com/dmitry-ai/harness/issues/68
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
HARNESS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = HARNESS_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
class SourceDiagnosticsScannerTests(unittest.TestCase):
	def _make_primary(self, root: Path) -> Path:
		prim = root / 'primary'
		(prim / 'rules').mkdir(parents=True)
		(prim / 'skills/demo').mkdir(parents=True)
		(prim / 'platforms').mkdir(parents=True)
		(prim / 'runtime.json').write_text(json.dumps({'workspace_root': str(root), 'platforms': {'antigravity': {'enabled': True}}}), encoding='utf-8')
		(prim / 'rules/00-scope.md').write_text('---\ntrigger: always_on\n---\n# Scope\n', encoding='utf-8')
		(prim / 'skills/demo/SKILL.md').write_text('---\nname: demo\n---\n# Demo\n', encoding='utf-8')
		(prim / 'platforms/antigravity.md').write_text('# Antigravity\n', encoding='utf-8')
		return prim
	def test_scanner_class_methods_and_wrapper_parity(self):
		from agent_tools.text_diagnostics import SourceDiagnosticsScanner, diagnose_sources
		with tempfile.TemporaryDirectory() as td:
			base = Path(td)
			prim = self._make_primary(base)
			proj = base / 'proj'
			(proj / '.agents/rules').mkdir(parents=True)
			(proj / '.agents/rules/00-scope.md').write_text('---\ntrigger: always_on\n---\n# Modified\n', encoding='utf-8')
			cfg = json.loads((prim / 'runtime.json').read_text(encoding='utf-8'))
			scanner = SourceDiagnosticsScanner(proj, config=cfg, primary=prim)
			res_cls = scanner.run()
			res_fn = diagnose_sources(proj, config=cfg, primary=prim)
			self.assertEqual(res_cls['configuration_sha256'], res_fn['configuration_sha256'])
			self.assertEqual([s['path'] for s in res_cls['sources']], [s['path'] for s in res_fn['sources']])
			self.assertTrue(any(('POLICY-DIVERGENCE' == c['code'] for c in res_cls['conflicts'])))
			self.assertTrue(hasattr(scanner, '_record_issue'))
			self.assertTrue(hasattr(scanner, '_add_source'))
			self.assertTrue(hasattr(scanner, '_inspect_native_toml'))
			self.assertTrue(hasattr(scanner, '_check_rule_and_skill_divergence'))
	def test_scanner_detects_missing_manifest_target_and_invalid_receipt(self):
		from agent_tools.text_diagnostics import SourceDiagnosticsScanner
		with tempfile.TemporaryDirectory() as td:
			base = Path(td)
			prim = self._make_primary(base)
			proj = base / 'proj2'
			(proj / '.agents').mkdir(parents=True)
			(proj / '.agents/rules.json').write_text(json.dumps({'entries': [{'path': 'rules/missing.md'}]}), encoding='utf-8')
			(proj / '\ua616/data').mkdir(parents=True)
			(proj / '\ua616/data/native-config.json').write_text('not-json', encoding='utf-8')
			cfg = json.loads((prim / 'runtime.json').read_text(encoding='utf-8'))
			res = SourceDiagnosticsScanner(proj, config=cfg, primary=prim).run()
			codes = {c['code'] for c in res['conflicts']}
			self.assertIn('MISSING-SOURCE', codes)
			self.assertIn('INVALID-RECEIPT', codes)
			self.assertFalse(res['valid'])
if '__main__' == __name__:
	unittest.main()
