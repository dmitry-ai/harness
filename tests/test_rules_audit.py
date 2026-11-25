# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add deterministic rules-audit CLI and aggregate budget enforcement":
# https://github.com/dmitry-ai/harness/issues/244
from __future__ import annotations
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
def _seed_harness(root: Path, rules: dict[str, str], *, codex_md: str='# Codex\nUse `answer-<turn_key>.md`.  \n', skill_md: str='', ws_agents: str | None=None) -> tuple[Path, Path]:
	ws = root / 'ws'
	prim = ws / 'code'
	for rel in ('rules', 'platforms', 'skills/demo', 'scripts', 'references', 'agents'):
		(prim / rel).mkdir(parents=True, exist_ok=True)
	(prim / 'paths.json').write_text('{}', encoding='utf-8')
	(prim / 'runtime.json').write_text(json.dumps({'version': 2, 'workspace_root': str(ws), 'timezone': 'Europe/Istanbul', 'registration': {'targets': []}, 'platforms': {'antigravity': {'enabled': True, 'surface': 'antigravity-ui', 'adapter': 'antigravity', 'instances': {}}, 'codex': {'enabled': True, 'surface': 'codex-ui', 'adapter': 'codex', 'instances': {}}}}), encoding='utf-8')
	(prim / 'scripts/README-agent-tools.md').write_text('# Tools\n', encoding='utf-8')
	(prim / 'references/note.md').write_text('# Note\nBody text.  \n', encoding='utf-8')
	(prim / 'agents/worker.md').write_text('# Worker\n', encoding='utf-8')
	for name, body in rules.items():
		(prim / 'rules' / name).write_text(body, encoding='utf-8')
	(prim / 'platforms/codex.md').write_text(codex_md, encoding='utf-8')
	if skill_md:
		(prim / 'skills/demo/SKILL.md').write_text(skill_md, encoding='utf-8')
	if None is not ws_agents:
		(ws / 'AGENTS.md').write_text(ws_agents, encoding='utf-8')
	return (ws, prim)
class RulesAuditTests(unittest.TestCase):
	def test_cli_rules_audit_and_semantic_brief_and_live_harness_green(self) -> None:
		from agent_tools import upwork_project
		proc = subprocess.run([sys.executable, str(SCRIPTS / 'harness.py'), 'rules-audit', '--primary', str(WT_ROOT), '--format', 'json'], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=30, check=False)
		self.assertEqual(0, proc.returncode, f'STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
		rep = json.loads(proc.stdout)
		self.assertTrue(rep['valid'], rep)
		self.assertEqual([], rep['issues'])
		self.assertLessEqual(rep['total_always_on_bytes'], 20000)
		self.assertLessEqual(rep['total_always_on_tokens'], 7000)
		brief_proc = subprocess.run([sys.executable, str(SCRIPTS / 'harness.py'), 'rules-audit', '--primary', str(WT_ROOT), '--semantic-brief', '--format', 'text'], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=30, check=False)
		self.assertEqual(0, brief_proc.returncode, brief_proc.stderr)
		brief = brief_proc.stdout
		for token in ('read-only', 'A.A', 'Skill Leakage', 'Lint Leakage', 'Blind References', 'Conflicting Instructions', '/doctor prompt-audit'):
			self.assertIn(token, brief)
		self.assertNotIn('"approved"', brief.lower())
		doc = upwork_project.doctor(primary=WT_ROOT)
		self.assertIn('rules_audit', doc)
		self.assertTrue(doc['rules_audit']['valid'], doc['rules_audit'])
		self.assertEqual(0, doc['rules_audit']['issue_count'])
	def test_detects_broken_links_blind_references_drift_and_skill_leakage(self) -> None:
		from agent_tools.rules_audit import audit_rules
		dup_block = '```bash\npython scripts/harness.py run-tests tests --module-timeout 300\npython scripts/harness.py doctor --platform codex\npython scripts/harness.py build-native --check\n```\n'
		with tempfile.TemporaryDirectory() as td:
			ws, prim = _seed_harness(
				Path(td),
				{
					'00-scope.md': '---\ntrigger: always_on\ndescription: "Scope"\n---\n# Scope\nAll shared rules remain `always_on`; avoid duplication.  \nSee `scripts/README-agent-tools.md`.  \nRead [broken](../references/missing-doc.md) before running checks.  \n' + dup_block,
					'11-code.md': '---\ntrigger: model_decision\ndescription: "Read before editing code"\n---\n# Code\nUse tabs.  \n',
				},
				codex_md='# Codex\nWrite output to `<root>/ꘖ/data/scratch/answer.md` before finalizing.  \n',
				skill_md='---\nname: demo\ndescription: "Demo"\n---\n# Demo\n' + dup_block,
			)
			rep = audit_rules(prim, workspace=ws)
			self.assertFalse(rep['valid'])
			codes = {item['code'] for item in rep['issues']}
			self.assertIn('BROKEN_LINK', codes, rep['issues'])
			self.assertIn('BLIND_REFERENCE', codes, rep['issues'])
			self.assertIn('INSTRUCTION_DRIFT', codes, rep['issues'])
			self.assertIn('SKILL_LEAKAGE_DUPLICATE', codes, rep['issues'])
			drift_details = ' '.join((item['detail'] for item in rep['issues'] if 'INSTRUCTION_DRIFT' == item['code']))
			self.assertIn('answer.md', drift_details)
			self.assertIn('always_on', drift_details)
	def test_detects_budget_html_comment_and_cross_platform_codex_leaks(self) -> None:
		from agent_tools.rules_audit import audit_rules
		filler = ('Keep rules concise and actionable for every session.  \n' * 85)
		with tempfile.TemporaryDirectory() as td:
			ws, prim = _seed_harness(
				Path(td),
				{
					'00-a.md': '---\ntrigger: always_on\ndescription: "A"\n---\n# A\n' + filler + '<!-- https://github.com/dmitry-ai/harness/issues/99 -->  \n',
					'01-b.md': '---\ntrigger: always_on\ndescription: "B"\n---\n# B\n' + filler,
					'02-c.md': '---\ntrigger: always_on\ndescription: "C"\n---\n# C\n' + filler,
					'03-d.md': '---\ntrigger: always_on\ndescription: "D"\n---\n# D\n' + filler,
					'04-e.md': '---\ntrigger: always_on\ndescription: "E"\n---\n# E\n' + filler + ('Extra line.  \n' * 120),
					'11-md.md': '---\ntrigger: model_decision\ndescription: "Read when editing code"\n---\n# Code\n```html\n<!-- allowed in fence -->\n```\n',
				},
				ws_agents='# Codex: Upwork\nRun turn-begin --platform codex using CODEX_THREAD_ID.  \n',
			)
			rep = audit_rules(prim, workspace=ws)
			self.assertFalse(rep['valid'])
			codes = {item['code'] for item in rep['issues']}
			self.assertIn('PER_FILE_BUDGET', codes, rep['issues'])
			self.assertIn('AGGREGATE_ALWAYS_ON_BYTES', codes, rep['issues'])
			self.assertIn('AGGREGATE_ALWAYS_ON_TOKENS', codes, rep['issues'])
			self.assertIn('NON_STRIPPED_HTML_COMMENT', codes, rep['issues'])
			self.assertIn('CROSS_PLATFORM_CODEX_LEAK', codes, rep['issues'])
			html_files = {item['file'] for item in rep['issues'] if 'NON_STRIPPED_HTML_COMMENT' == item['code']}
			self.assertIn('rules/00-a.md', html_files)
			self.assertNotIn('rules/11-md.md', html_files)
			proc = subprocess.run([sys.executable, str(SCRIPTS / 'harness.py'), 'rules-audit', '--primary', str(prim), '--workspace', str(ws)], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=30, check=False)
			self.assertEqual(2, proc.returncode, proc.stderr)
	def test_doctor_and_rules_audit_default_to_active_checkout_rules(self) -> None:
		from agent_tools import rules_manifest, upwork_project
		doc = upwork_project.doctor()
		self.assertEqual(str((WT_ROOT / 'rules/00-scope.md').resolve()), doc['paths']['rules'][0])
		self.assertTrue(doc['rules_audit']['valid'], doc['rules_audit'])
		with tempfile.TemporaryDirectory() as td:
			custom = Path(td).resolve() / 'custom_primary'
			custom.mkdir()
			self.assertEqual(custom, rules_manifest.resolve_rules_primary(None, custom).resolve())
		proc = subprocess.run([sys.executable, str(SCRIPTS / 'harness.py'), 'rules-audit', '--format', 'json'], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=30, check=False)
		self.assertEqual(0, proc.returncode, f'STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
		rep = json.loads(proc.stdout)
		self.assertEqual(WT_ROOT.resolve().as_posix(), rep['primary'])
		self.assertTrue(rep['valid'], rep)
	def test_pre_tool_use_rules_budget_and_doctor_and_pre_commit_enforce_limits(self) -> None:
		from agent_tools import staged_gates, upwork_project
		from agent_tools.gates import rules_budget
		with tempfile.TemporaryDirectory() as td:
			ws, prim = _seed_harness(
				Path(td),
				{
					'00-scope.md': '---\ntrigger: always_on\ndescription: "Scope"\n---\n# Scope\nStay in scope.  \n',
					'01-a.md': '---\ntrigger: always_on\ndescription: "A"\n---\n# A\n' + ('Alpha invariant.  \n' * 300),
					'02-b.md': '---\ntrigger: always_on\ndescription: "B"\n---\n# B\n' + ('Beta invariant.  \n' * 300),
					'03-c.md': '---\ntrigger: always_on\ndescription: "C"\n---\n# C\n' + ('Gamma invariant.  \n' * 300),
					'04-d.md': '---\ntrigger: always_on\ndescription: "D"\n---\n# D\n' + ('Delta invariant.  \n' * 300),
				},
			)
			target = prim / 'rules/00-scope.md'
			self.assertIsNotNone(rules_budget.check('write_file', {'Path': str(target), 'Content': '---\ntrigger: always_on\ndescription: "Scope"\n---\n' + ('x' * 6200)}))
			self.assertIsNotNone(rules_budget.check('write_file', {'Path': str(target), 'Content': '---\ntrigger: always_on\ndescription: "Scope"\n---\n<!-- bad comment -->\n'}))
			self.assertIsNotNone(rules_budget.check('write_file', {'Path': str(target), 'Content': '---\ntrigger: always_on\ndescription: "Scope"\n---\n' + ('Budget push line.  \n' * 220)}))
			self.assertIsNone(rules_budget.check('write_file', {'Path': str(target), 'Content': '---\ntrigger: always_on\ndescription: "Scope"\n---\n# Scope\nCompact rule.  \n'}))
			self.assertIsNotNone(rules_budget.check('write_file', {'Path': str(ws / '.agents/rules/90-project.md'), 'Content': 'x' * 4100}))
			with self.assertRaises(ValueError):
				(prim / 'rules/00-scope.md').write_text('---\ntrigger: always_on\ndescription: "Scope"\n---\n' + ('y' * 6200), encoding='utf-8')
				upwork_project.doctor(primary=prim)
			(prim / 'rules/00-scope.md').write_text('---\ntrigger: always_on\ndescription: "Scope"\n---\n# Scope\n<!-- leak -->  \n', encoding='utf-8')
			staged_errs = staged_gates.verify_staged_extra_gates(prim, ['rules/00-scope.md'], use_index=False)
			self.assertTrue(any(('NON_STRIPPED_HTML_COMMENT' in e for e in staged_errs)), staged_errs)
			(prim / 'rules/00-scope.md').write_text('---\ntrigger: always_on\ndescription: "Scope"\n---\n# Scope\nCompact rule.  \n', encoding='utf-8')
			for stale in ('01-a.md', '02-b.md', '03-c.md', '04-d.md'):
				(prim / 'rules' / stale).unlink()
			self.assertEqual([], staged_gates.verify_staged_extra_gates(prim, ['rules/00-scope.md'], use_index=False))
if '__main__' == __name__:
	unittest.main()
