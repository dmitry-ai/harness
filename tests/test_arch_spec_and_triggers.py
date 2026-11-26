# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# @used-by :meth:`ArchSpecAndTriggersTests.test_answer_gates_enforce_architecture_pattern_specs()`
def _base_answer_ctx() -> dict:
	return {
		'root': WT_ROOT,
		'role': 'primary',
		'doc4_errs': [],
		'link_errs': [],
		'prob_errs': [],
		'source_errs': [],
		'lang_errs': [],
		'exec5_chk': {'verified': True, 'violations': []},
		'http_chk': {'verified': True, 'violations': []},
		'comp_chk': {'verified': True},
		'evicted_cited': [],
		'del_chk': {'verified': True},
		'issue_first_chk': {'verified': True, 'violations': []},
		'lifecycle_chk': {'verified': True, 'violations': []},
		'tdd_chk': {'verified': True, 'violations': []},
		'wf_errs': [],
	}
# 2026-11-26 "Add software design pattern specification validator and trigger checks": https://github.com/dmitry-ai/harness/issues/349
class ArchSpecAndTriggersTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_answer_gates_enforce_architecture_pattern_specs(self) -> None:
		from agent_tools.gates import run_answer_gates
		base_ctx = _base_answer_ctx()
		bad_resp = '## M-1. New modular pipeline\n\nCreate `scripts/agent_tools/router.py` with class `TaskRouter`, add a new `PreToolUse` gate in `gates/router.py`, and register CLI handlers in `cli_registry.py`.  \n'
		issues_bad, checks_bad = run_answer_gates({**base_ctx, 'response': bad_resp})
		self.assertFalse(checks_bad['architecture'])
		self.assertIn('architecture', [it['gate_id'] for it in issues_bad])
		good_resp = bad_resp + 'Pattern: **Chain of Responsibility** (`Behavioral`).  \nIntent: decouple gate handlers cleanly.  \nParticipants: `TaskRouter`, `gates/router.py`, `cli_registry.py`.  \nCollaboration: handlers run in priority order until one rejects.  \nConsequences: open-closed extension with linear pass cost.  \n'
		issues_good, checks_good = run_answer_gates({**base_ctx, 'response': good_resp})
		self.assertTrue(checks_good['architecture'], issues_good)
		self.assertEqual([], issues_good)
		issues_plain, checks_plain = run_answer_gates({**base_ctx, 'response': 'The fix passed all 12 tests cleanly.  \n'})
		self.assertTrue(checks_plain['architecture'])
		self.assertEqual([], issues_plain)
	# @used-by :mod:`unittest`
	def test_catalog_loads_canonical_patterns_and_resolves_aliases(self) -> None:
		from agent_tools.arch.catalog import catalog_pattern_names, load_pattern_catalog, lookup_pattern
		cat = load_pattern_catalog(WT_ROOT)
		self.assertEqual(1, cat['schema_version'])
		names = catalog_pattern_names(catalog=cat)
		self.assertIn('Proxy', names)
		self.assertIn('Chain of Responsibility', names)
		hit_alias = lookup_pattern('**Protection Proxy**', catalog=cat)
		self.assertIsNotNone(hit_alias)
		self.assertEqual('Proxy', hit_alias['name'])
		self.assertEqual('Structural', hit_alias['category'])
		hit_slash = lookup_pattern('Memento / Immutable Snapshot', catalog=cat)
		self.assertIsNotNone(hit_slash)
		self.assertEqual('Memento', hit_slash['name'])
		self.assertIsNone(lookup_pattern('MadeUpQuantumPattern', catalog=cat))
	# @used-by :mod:`unittest`
	def test_code_change_trigger_detects_structural_changes_and_ignores_trivial_fixes(self) -> None:
		from agent_tools.arch.triggers import classify_code_change_trigger, extract_code_symbols
		old_small = 'def add(a, b):\n\treturn a + b\n'
		new_small = 'def add(a, b):\n\treturn int(a) + int(b)\n'
		tr_small = classify_code_change_trigger('scripts/agent_tools/helper.py', old_small, new_small)
		self.assertFalse(tr_small['triggered'], tr_small)
		new_cls = 'from .catalog import load_pattern_catalog\nclass PolicyEngine:\n\tdef run(self):\n\t\treturn load_pattern_catalog()\n'
		tr_cls = classify_code_change_trigger('scripts/agent_tools/policy.py', old_small, new_cls)
		self.assertTrue(tr_cls['triggered'])
		self.assertIn('PolicyEngine', tr_cls['added_classes'])
		self.assertTrue(bool(tr_cls['added_cross_imports']))
		self.assertTrue(classify_code_change_trigger('scripts/agent_tools/gates/answer_checks.py', 'X = 1\n', 'X = 2\n')['triggered'])
		self.assertTrue(classify_code_change_trigger('scripts/agent_tools/a.py', old_small, new_small, changed_prod_files=['scripts/agent_tools/a.py', 'scripts/agent_tools/b.py'])['triggered'])
		self.assertFalse(classify_code_change_trigger('tests/test_sample.py', None, new_cls)['triggered'])
		syms = extract_code_symbols(new_cls, rel_path='scripts/agent_tools/policy.py')
		self.assertIn('PolicyEngine', syms['classes'])
		self.assertIn('run', syms['functions'])
		self.assertIn('WidgetProxy', extract_code_symbols('export class WidgetProxy { render() { return 1; } }\n', rel_path='web/proxy.js')['classes'])
	# @used-by :mod:`unittest`
	def test_issue_linter_enforces_architecture_pattern_specs_on_structural_parent_issues(self) -> None:
		from agent_tools.issues.linter import IssueMarkdownLinter
		linter = IssueMarkdownLinter()
		bad_issue = '## Problem\nNeed a new routing subsystem across multiple modules.\n\n## Architecture\nCreate `scripts/agent_tools/router.py` with class `TaskRouter` and hook into `gates/__init__.py` and `cli_registry.py`.\n'
		bad_errs = linter.lint(bad_issue, is_title=False, check_structure_policy=True, parent_number=None)
		self.assertIn('MISSING_ARCH_PATTERN_SPEC', {e['code'] for e in bad_errs}, bad_errs)
		good_issue = bad_issue + '\n- **Pattern:** Chain of Responsibility\n- **Category:** Behavioral\n- **Intent:** Route tool checks through ordered handlers.\n- **Participants:** `TaskRouter`, `gates/__init__.py`, `cli_registry.py`\n- **Collaboration:** Handlers inspect requests sequentially until one denies.\n- **Consequences:** Open-closed extensibility with slight dispatch indirection.\n'
		good_codes = {e['code'] for e in linter.lint(good_issue, is_title=False, check_structure_policy=True, parent_number=None)}
		self.assertNotIn('MISSING_ARCH_PATTERN_SPEC', good_codes)
		self.assertNotIn('INVALID_ARCH_PATTERN_SPEC', good_codes)
		bug_issue = '## Problem\nCommand `harness.py status` exited with code 1 when `foo` is empty.\n'
		self.assertEqual([], [e for e in linter.lint(bug_issue, is_title=False, check_structure_policy=True, parent_number=None) if 'ARCH' in e['code']])
	# @used-by :mod:`unittest`
	def test_spec_validator_accepts_gof_ru_and_idiom_exception(self) -> None:
		from agent_tools.arch.spec import extract_arch_specs, extract_declared_participants, validate_arch_spec_markdown
		valid_en = '- **Pattern:** Strategy\n- **Category:** Behavioral\n- **Intent:** Swap validation algorithms per target format.\n- **Participants:** `SpecValidator`, `IdiomValidator`\n- **Collaboration:** Dispatcher selects a validator strategy at runtime.\n- **Consequences:** Easy extension without modifying the dispatcher.\n'
		res_en = validate_arch_spec_markdown(valid_en, require_full_fields=True)
		self.assertTrue(res_en['valid'], res_en)
		self.assertEqual(['Strategy'], res_en['patterns'])
		self.assertIn('SpecValidator', extract_declared_participants(extract_arch_specs(valid_en)))
		valid_ru = '- **Паттерн:** Посредник (Mediator)\n- **Категория:** Behavioral\n- **Назначение:** Изолировать агента от аудитора через хранилище пакетов.\n- **Участники:** `ReviewStore`, `ArchAuditor`\n- **Взаимодействие:** Хранилище замораживает пакет и проверяет подпись вердикта.\n- **Последствия:** Исключён прямой сговор и подмена текста после аудита.\n'
		res_ru = validate_arch_spec_markdown(valid_ru, require_full_fields=True)
		self.assertTrue(res_ru['valid'], res_ru)
		self.assertEqual(['Mediator'], res_ru['patterns'])
		valid_idiom = '- **idiom_exception:** Strategy\n- **Native Construct:** Python first-class callable functions in a dispatch dict\n- **Rationale:** Wrapping pure functions in single-method GoF Strategy classes adds boilerplate without polymorphic state.\n- **Participants:** `answer_checks.ANSWER_GATES`, `_architecture_messages`\n'
		res_id = validate_arch_spec_markdown(valid_idiom, require_full_fields=True)
		self.assertTrue(res_id['valid'], res_id)
		self.assertEqual(1, len(res_id['idiom_exceptions']))
	# @used-by :mod:`unittest`
	def test_spec_validator_rejects_unknown_mismatched_and_incomplete_specs(self) -> None:
		from agent_tools.arch.spec import validate_arch_spec_markdown
		bad_unknown = '- **Pattern:** CosmicMagicPattern\n- **Category:** Behavioral\n- **Intent:** x\n- **Participants:** `Foo`\n- **Collaboration:** y\n- **Consequences:** z\n'
		res_unk = validate_arch_spec_markdown(bad_unknown, require_full_fields=True)
		self.assertFalse(res_unk['valid'])
		self.assertIn('UNRECOGNIZED_ARCH_PATTERN', {i['code'] for i in res_unk['issues']})
		bad_cat = '- **Pattern:** Strategy\n- **Category:** Creational\n- **Intent:** x\n- **Participants:** `Foo`\n- **Collaboration:** y\n- **Consequences:** z\n'
		res_cat = validate_arch_spec_markdown(bad_cat, require_full_fields=True)
		self.assertFalse(res_cat['valid'])
		self.assertIn('MISMATCHED_ARCH_CATEGORY', {i['code'] for i in res_cat['issues']})
		res_inc = validate_arch_spec_markdown('- **Pattern:** Strategy\n- **Category:** Behavioral\n', require_full_fields=True)
		self.assertFalse(res_inc['valid'])
		self.assertIn('INCOMPLETE_ARCH_SPEC_FIELDS', {i['code'] for i in res_inc['issues']})
		bad_idiom = '- **idiom_exception:** Strategy\n- **Native Construct:** closure\n- **Rationale:** short\n'
		res_bi = validate_arch_spec_markdown(bad_idiom, require_full_fields=True)
		self.assertFalse(res_bi['valid'])
		self.assertIn('INVALID_IDIOM_EXCEPTION', {i['code'] for i in res_bi['issues']})
	# @used-by :mod:`unittest`
	def test_runner_architecture_check_records_state_and_fails_gate_on_missing_patterns(self) -> None:
		from agent_tools.arch.evaluator import check_runner_architecture
		class _FakeRunner:
			# @used-by :meth:`ArchSpecAndTriggersTests.test_runner_architecture_check_records_state_and_fails_gate_on_missing_patterns()`
			def __init__(self, resp: str) -> None:
				self.root = WT_ROOT
				self.turn = {}
				self.value: dict = {}
				self.response = resp
				self.blocked_report = False
				self.failed: list[tuple[str, str]] = []
			# @used-by :meth:`ArchSpecAndTriggersTests.test_runner_architecture_check_records_state_and_fails_gate_on_missing_patterns()`
			def _fail_gate(self, gate_id: str, detail: str) -> None:
				self.failed.append((gate_id, detail))
		bad_r = _FakeRunner('## Architecture\nAdd new module `scripts/agent_tools/foo.py` with class `FooEngine` and wire into `gates/__init__.py`.\n')
		check_runner_architecture(bad_r)
		self.assertFalse(bad_r.value['arch_audit_check']['verified'])
		self.assertEqual(1, len(bad_r.failed))
		self.assertEqual('architecture', bad_r.failed[0][0])
if '__main__' == __name__:
	unittest.main()