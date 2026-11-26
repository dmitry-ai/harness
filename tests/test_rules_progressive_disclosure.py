# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import configuration, upwork_project
def _seed_primary(root: Path, rules: dict[str, str]) -> Path:
	primary = root / 'primary'
	for rel in ('rules', 'platforms', 'skills/upwork-init', 'agents', 'scripts'):
		(primary / rel).mkdir(parents=True, exist_ok=True)
	for name, body in rules.items():
		(primary / 'rules' / name).write_text(body, encoding='utf-8')
	(primary / 'platforms/codex.md').write_text('# Codex\n', encoding='utf-8')
	(primary / 'skills/upwork-init/SKILL.md').write_text('---\nname: upwork-init\ndescription: "Init"\n---\n# Init\n', encoding='utf-8')
	(primary / 'agents/worker.md').write_text('# Worker\n', encoding='utf-8')
	(primary / 'runtime.json').write_text(json.dumps({'version': 2, 'workspace_root': str(root), 'timezone': 'Europe/Istanbul', 'registration': {'targets': []}, 'platforms': {'antigravity': {'enabled': True, 'surface': 'antigravity-ui', 'adapter': 'antigravity', 'instances': {}}, 'codex': {'enabled': True, 'surface': 'codex-ui', 'adapter': 'codex', 'instances': {}}}}), encoding='utf-8')
	return primary
# 2026-11-25
# "Support model_decision trigger class in doctor and Codex loader":
# https://github.com/dmitry-ai/harness/issues/241
class RulesProgressiveDisclosureTests(unittest.TestCase):
	def test_doctor_accepts_model_decision_and_reports_trigger_metrics(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			primary = _seed_primary(Path(td), {'00-scope.md': '---\ntrigger: always_on\ndescription: "Core scope"\n---\n# Scope\nStay in scope.  \n', '11-code-formatting.md': '---\ntrigger: model_decision\ndescription: "Read before editing source code files"\n---\n# Code\nUse tabs.  \n'})
			rep = upwork_project.doctor(primary=primary)
			self.assertEqual(['00-scope.md'], rep['always_on_rules'])
			self.assertEqual(['11-code-formatting.md'], rep['model_decision_rules'])
			self.assertEqual((primary / 'rules/00-scope.md').stat().st_size, rep['always_on_rule_bytes'])
			self.assertGreater(rep['always_on_estimated_tokens'], 0)
			self.assertLess(rep['always_on_rule_bytes'], rep['rule_bytes'])
	def test_doctor_rejects_invalid_trigger_or_undescribed_model_decision(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			base = Path(td)
			p_missing_desc = _seed_primary(base / 'no_desc', {'00-scope.md': '---\ntrigger: always_on\n---\n# Scope\n', '11-code.md': '---\ntrigger: model_decision\n---\n# Code\n'})
			with self.assertRaises(ValueError):
				upwork_project.doctor(primary=p_missing_desc)
			p_bad_trig = _seed_primary(base / 'bad_trig', {'00-scope.md': '---\ntrigger: sometimes\ndescription: "Bad"\n---\n# Scope\n'})
			with self.assertRaises(ValueError):
				upwork_project.doctor(primary=p_bad_trig)
			p_no_trig = _seed_primary(base / 'no_trig', {'00-scope.md': '# Scope without frontmatter\n'})
			with self.assertRaises(ValueError):
				upwork_project.doctor(primary=p_no_trig)
	def test_loader_separates_always_on_and_catalogs_model_decision_with_description(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			primary = _seed_primary(Path(td), {'00-scope.md': '---\ntrigger: always_on\ndescription: "Core scope"\n---\n# Scope\n', '11-code-formatting.md': '---\ntrigger: model_decision\ndescription: "Read before editing source code"\n---\n# Code\n', '90-legacy.md': 'Plain rule without frontmatter.\n'})
			loader = configuration._loader(primary)
			always_part, sep, on_demand_part = loader.partition('On-demand shared rules (trigger: model_decision')
			self.assertTrue(bool(sep), f'Missing model_decision catalog section in loader:\n{loader}')
			self.assertIn((primary / 'rules/00-scope.md').as_posix(), always_part)
			self.assertIn((primary / 'rules/90-legacy.md').as_posix(), always_part)
			self.assertNotIn((primary / 'rules/11-code-formatting.md').as_posix(), always_part)
			self.assertIn(f'- {(primary / "rules/11-code-formatting.md").as_posix()} — Read before editing source code', on_demand_part)
	def test_loader_omits_on_demand_header_when_all_rules_are_always_on(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			primary = _seed_primary(Path(td), {'00-scope.md': '---\ntrigger: always_on\n---\n# Scope\n'})
			loader = configuration._loader(primary)
			self.assertIn((primary / 'rules/00-scope.md').as_posix(), loader)
			self.assertNotIn('On-demand shared rules', loader)
	def test_token_estimator_is_positive_and_monotonic(self) -> None:
		from agent_tools.rules_manifest import estimate_tokens
		short_t = estimate_tokens('Hello world.')
		long_t = estimate_tokens('Hello world. ' * 50)
		self.assertGreater(short_t, 0)
		self.assertGreater(long_t, short_t)
if '__main__' == __name__:
	unittest.main()