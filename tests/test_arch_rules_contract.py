# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import links, native_profiles, rules_audit, upwork_project
import check_markdown_slop
# 2026-11-26 "Add software design patterns normative contract and catalog": https://github.com/dmitry-ai/harness/issues/344
class ArchRulesContractTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_architecture_rule_is_compact_always_on_and_passes_doctor_and_rules_audit(self) -> None:
		rule_path = WT_ROOT / 'rules/12-architecture.md'
		self.assertTrue(rule_path.is_file(), 'Missing rules/12-architecture.md')
		raw = rule_path.read_bytes()
		self.assertLessEqual(len(raw), 1200, f'rules/12-architecture.md ({len(raw)} bytes) exceeds 1,200-byte budget')
		text = raw.decode('utf-8')
		self.assertEqual([], links.validate_file(rule_path, local_anchors=True, readable_links=True))
		self.assertEqual([], check_markdown_slop.markdown_slop_issues(text))
		self.assertNotIn('<!--', text)
		for token in ('## ARCH-1', '## ARCH-2', 'df-architecture', 'patterns-catalog.json', 'arch-auditor', 'idiom_exception'):
			self.assertIn(token, text, f'Missing token {token!r} in rules/12-architecture.md')
		doc = upwork_project.doctor(primary=WT_ROOT)
		self.assertIn('12-architecture.md', doc['always_on_rules'])
		self.assertLessEqual(doc['always_on_rule_bytes'], 21500)
		audit = rules_audit.audit_rules(WT_ROOT)
		self.assertTrue(audit['valid'], audit['issues'])
		self.assertEqual([], audit['issues'])
		bootstrap = WT_ROOT / 'platforms/codex/AGENTS.md'
		expected = native_profiles.shared_native_outputs(WT_ROOT)[bootstrap]
		self.assertEqual(expected, bootstrap.read_text(encoding='utf-8'))
		self.assertIn('12-architecture.md', expected)
	# @used-by :mod:`unittest`
	def test_df_architecture_skill_discovered_and_lints_cleanly(self) -> None:
		skills = native_profiles._skills(WT_ROOT)
		self.assertIn('df-architecture', skills)
		skill_path, meta = skills['df-architecture']
		self.assertEqual('df-architecture', meta['name'])
		self.assertIn('design patterns', meta['description'].lower())
		self.assertEqual([], links.validate_file(skill_path, local_anchors=True, readable_links=True))
		skill_text = skill_path.read_text(encoding='utf-8')
		self.assertEqual([], check_markdown_slop.markdown_slop_issues(skill_text))
		for token in ('Creational', 'Structural', 'Behavioral', 'Concurrency', 'Architectural', 'idiom_exception', 'arch-auditor', 'arch-prepare', 'arch-review-input', 'arch-record-review', 'arch-check', 'Participants', 'Collaboration', 'Consequences'):
			self.assertIn(token, skill_text, f'Missing token {token!r} in skills/df-architecture/SKILL.md')
		scope_text = (WT_ROOT / 'rules/00-scope.md').read_text(encoding='utf-8')
		self.assertIn('df-architecture', scope_text)
	# @used-by :mod:`unittest`
	def test_patterns_catalog_covers_wikipedia_taxonomy_and_required_fields(self) -> None:
		cat_path = WT_ROOT / 'references/architecture/patterns-catalog.json'
		self.assertTrue(cat_path.is_file(), 'Missing references/architecture/patterns-catalog.json')
		data = json.loads(cat_path.read_text(encoding='utf-8'))
		self.assertEqual(1, data.get('schema_version'))
		self.assertEqual('https://en.wikipedia.org/wiki/Software_design_pattern', data.get('source_url'))
		self.assertEqual(['Creational', 'Structural', 'Behavioral', 'Concurrency', 'Architectural'], data.get('categories'))
		self.assertEqual(['Pattern', 'Category', 'Intent', 'Participants', 'Collaboration', 'Consequences'], data.get('required_spec_fields'))
		self.assertEqual(['Pattern', 'Native Construct', 'Rationale', 'Participants'], data.get('idiom_exception_fields'))
		patterns = data.get('patterns') or []
		self.assertGreaterEqual(len(patterns), 50)
		by_cat: dict[str, set[str]] = {}
		seen_names: set[str] = set()
		for entry in patterns:
			name = str(entry['name'])
			cat = str(entry['category'])
			self.assertNotIn(name.lower(), seen_names, f'Duplicate pattern {name}')
			seen_names.add(name.lower())
			self.assertIn(cat, data['categories'])
			self.assertIsInstance(entry.get('aliases'), list)
			self.assertTrue(bool(entry.get('roles')), f'Pattern {name} needs roles')
			by_cat.setdefault(cat, set()).add(name)
		for cat in data['categories']:
			self.assertGreaterEqual(len(by_cat.get(cat, set())), 8, f'Category {cat} under-populated')
		for must_have in ('Factory Method', 'Strategy', 'Proxy', 'Chain of Responsibility', 'Mediator', 'Memento', 'Visitor', 'Template Method', 'Specification', 'Flyweight', 'Layered Architecture', 'Reactor'):
			self.assertIn(must_have.lower(), seen_names, f'Missing canonical pattern {must_have}')
if '__main__' == __name__:
	unittest.main()