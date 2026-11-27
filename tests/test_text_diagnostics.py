# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from typing import override
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from agent_tools.text_diagnostics import diagnose_sources
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
class TextDiagnosticsTests(unittest.TestCase):
	# 2026-11-26
	# "Apply cross-reference annotations across Harness Python and JavaScript":
	# https://github.com/dmitry-ai/harness/issues/305
	# @used-by :meth:`unittest.TestCase.setUp()`
	# @used-by :mod:`unittest`
	# @see :meth:`unittest.TestCase.setUp()`
	@override
	def setUp(self):
		self.temp = tempfile.TemporaryDirectory()
		self.addCleanup(self.temp.cleanup)
		self.workspace = Path(self.temp.name)
		self.primary = self.workspace / 'shared/.agents'
		self.root = self.workspace / 'project'
		self.root.mkdir()
		self.config = {'version': 2, 'workspace_root': str(self.workspace), 'platforms': {'codex': {}}}
		self.write(self.primary / 'runtime.json', json.dumps(self.config))
		self.write(self.primary / 'rules/00-scope.md', '---\ntrigger: always_on\nversion: 3\n---\nScope\n')
		self.write(self.primary / 'platforms/codex.md', 'Codex adapter\n')
	# @used-by :meth:`TextDiagnosticsTests.setUp()`
	# @used-by :meth:`TextDiagnosticsTests.test_conflicting_local_rule_is_visible_without_assumed_precedence()`
	# @used-by :meth:`TextDiagnosticsTests.test_explicit_root_required_and_sibling_not_discovered()`
	# @used-by :meth:`TextDiagnosticsTests.test_native_loader_found_at_workspace_without_project_manifest()`
	# @used-by :meth:`TextDiagnosticsTests.test_path_manifest_reports_actual_trigger_and_missing_source()`
	# @used-by :meth:`TextDiagnosticsTests.test_profile_instructions_are_separate_candidates_without_guessing_active_account()`
	# @used-by :meth:`TextDiagnosticsTests.test_projection_receipt_detects_manual_edit_without_writing()`
	# @used-by :meth:`TextDiagnosticsTests.test_stub_skill_resolves_canonical_instead_of_false_duplicate()`
	# @used-by :meth:`TextDiagnosticsTests.test_unsupported_inheritance_is_unknown_and_malformed_files_visible()`
	def write(self, path, text):
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(text, encoding='utf-8')
	# @used-by :meth:`TextDiagnosticsTests.test_conflicting_local_rule_is_visible_without_assumed_precedence()`
	# @used-by :meth:`TextDiagnosticsTests.test_explicit_root_required_and_sibling_not_discovered()`
	# @used-by :meth:`TextDiagnosticsTests.test_missing_optional_manifests_do_not_mean_shared_rules_absent()`
	# @used-by :meth:`TextDiagnosticsTests.test_native_loader_found_at_workspace_without_project_manifest()`
	# @used-by :meth:`TextDiagnosticsTests.test_path_manifest_reports_actual_trigger_and_missing_source()`
	# @used-by :meth:`TextDiagnosticsTests.test_profile_instructions_are_separate_candidates_without_guessing_active_account()`
	# @used-by :meth:`TextDiagnosticsTests.test_projection_receipt_detects_manual_edit_without_writing()`
	# @used-by :meth:`TextDiagnosticsTests.test_stub_skill_resolves_canonical_instead_of_false_duplicate()`
	# @used-by :meth:`TextDiagnosticsTests.test_unsupported_inheritance_is_unknown_and_malformed_files_visible()`
	def report(self):
		return diagnose_sources(self.root, platform='codex', config=self.config, primary=self.primary)
	# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_extract()`
	# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_extract_file()`
	# @used-by :meth:`TextDiagnosticsTests.test_conflicting_local_rule_is_visible_without_assumed_precedence()`
	# @used-by :meth:`TextDiagnosticsTests.test_missing_optional_manifests_do_not_mean_shared_rules_absent()`
	# @used-by :meth:`TextDiagnosticsTests.test_native_loader_found_at_workspace_without_project_manifest()`
	# @used-by :meth:`TextDiagnosticsTests.test_path_manifest_reports_actual_trigger_and_missing_source()`
	# @used-by :meth:`TextDiagnosticsTests.test_projection_receipt_detects_manual_edit_without_writing()`
	# @used-by :meth:`TextDiagnosticsTests.test_stub_skill_resolves_canonical_instead_of_false_duplicate()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.check_and_review()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_proof_evidence_review_document_and_journal_changes_remain_conflicts()`
	def source(self, report, path):
		return next((item for item in report['sources'] if item['path'] == str(path.resolve())))
	# @used-by :mod:`unittest`
	def test_missing_optional_manifests_do_not_mean_shared_rules_absent(self):
		report = self.report()
		self.assertTrue(report['valid'])
		self.assertEqual(report['platform_injection']['status'], 'unknown')
		self.assertEqual(self.source(report, self.primary / 'rules/00-scope.md')['trigger'], 'always_on')
		self.assertFalse(self.source(report, self.root / '.agents/rules.json')['exists'])
		self.assertFalse(any(('MISSING-SOURCE' == item['code'] for item in report['conflicts'])))
	# @used-by :mod:`unittest`
	def test_explicit_root_required_and_sibling_not_discovered(self):
		sibling = self.workspace / 'sibling/.agents/rules/private.md'
		self.write(sibling, 'Other project')
		with self.assertRaises(ValueError):
			diagnose_sources(None, config=self.config, primary=self.primary)
		report = self.report()
		self.assertNotIn(str(sibling.resolve()), [item['path'] for item in report['sources']])
	# @used-by :mod:`unittest`
	def test_native_loader_found_at_workspace_without_project_manifest(self):
		native = self.workspace / '.codex/config.toml'
		source = self.primary / 'rules/00-scope.md'
		self.write(native, 'developer_instructions = ' + json.dumps('Read:\n- ' + source.as_posix()) + '\n')
		report = self.report()
		self.assertIn(str(native), self.source(report, source)['configured_via'])
		self.assertTrue(self.source(report, native)['developer_instructions_configured'])
		self.assertEqual(report['platform_injection']['status'], 'unknown')
	# @used-by :mod:`unittest`
	def test_path_manifest_reports_actual_trigger_and_missing_source(self):
		rule = self.workspace / 'extra/conditional.md'
		self.write(rule, '---\ntrigger: glob\nglobs: "*.md"\n---\nConditional\n')
		manifest = self.root / '.agents/rules.json'
		self.write(manifest, json.dumps({'entries': [{'path': str(rule)}, {'path': '../absent.md'}]}))
		report = self.report()
		self.assertFalse(report['valid'])
		self.assertEqual(self.source(report, rule)['selection'], 'conditional-or-manual')
		self.assertTrue(any(('MISSING-SOURCE' == item['code'] for item in report['conflicts'])))
	# @used-by :mod:`unittest`
	def test_conflicting_local_rule_is_visible_without_assumed_precedence(self):
		local = self.root / '.agents/rules/00-scope.md'
		self.write(local, '---\ntrigger: always_on\n---\nOld content\n')
		report = self.report()
		conflict = next((item for item in report['conflicts'] if 'POLICY-DIVERGENCE' == item['code']))
		self.assertEqual(conflict['severity'], 'warning')
		self.assertEqual(self.source(report, local)['injection'], 'unknown')
	# @used-by :mod:`unittest`
	def test_stub_skill_resolves_canonical_instead_of_false_duplicate(self):
		canonical = self.primary / 'skills/df-article/SKILL.md'
		self.write(canonical, '---\nname: df-article\ndescription: Article\n---\nArticle body\n')
		local = self.root / '.agents/skills/df-article/SKILL.md'
		self.write(local, '---\nname: df-article\n---\nRead [SKILL.md](<' + canonical.as_posix() + '>).\n')
		report = self.report()
		self.assertIn(str(local), self.source(report, canonical)['configured_via'])
		self.assertFalse(any(('SKILL-DIVERGENCE' == item['code'] for item in report['conflicts'])))
		self.write(local, '---\nname: df-article\n---\nIndependent stale body\n')
		self.assertTrue(any(('SKILL-DIVERGENCE' == item['code'] for item in self.report()['conflicts'])))
	# @used-by :mod:`unittest`
	def test_projection_receipt_detects_manual_edit_without_writing(self):
		projection = self.root / '.agents/skills/generated/SKILL.md'
		self.write(projection, 'old projection')
		self.write(self.root / 'ꘖ/data/native-config.json', json.dumps({str(projection.resolve()): hashlib.sha256(projection.read_bytes()).hexdigest()}))
		self.assertEqual(self.source(self.report(), projection)['projection'], 'matches-receipt')
		self.write(projection, 'user edit')
		before = {str(path): path.read_bytes() for path in self.workspace.rglob('*') if path.is_file()}
		report = self.report()
		after = {str(path): path.read_bytes() for path in self.workspace.rglob('*') if path.is_file()}
		self.assertEqual(before, after)
		self.assertFalse(report['valid'])
		self.assertTrue(any(('PROJECTION-DRIFT' == item['code'] for item in report['conflicts'])))
	# @used-by :mod:`unittest`
	def test_unsupported_inheritance_is_unknown_and_malformed_files_visible(self):
		self.write(self.root / '.agents/rules.json', '{"inherits": ["elsewhere"], "entries": []}')
		self.write(self.root / '.codex/config.toml', 'developer_instructions = [')
		report = self.report()
		self.assertFalse(report['valid'])
		self.assertEqual({item['code'] for item in report['conflicts']}, {'UNRESOLVED-INHERITANCE', 'INVALID-NATIVE-CONFIG'})
	# @used-by :mod:`unittest`
	def test_profile_instructions_are_separate_candidates_without_guessing_active_account(self):
		homes = {'C1': str(self.workspace / 'home1'), 'C2': str(self.workspace / 'home2')}
		self.config['platforms']['codex']['homes'] = homes
		for name, home in homes.items():
			self.write(Path(home) / 'config.toml', 'developer_instructions = ' + json.dumps(name + ' policy') + '\n')
		report = self.report()
		self.assertIsNone(report['selected_profile'])
		self.assertTrue(any(('PROFILE-INSTRUCTIONS-DIFFER' == item['code'] for item in report['conflicts'])))
		selected = diagnose_sources(self.root, platform='codex', profile='C2', config=self.config, primary=self.primary)
		self.assertEqual(selected['selected_profile'], 'C2')
		self.assertEqual({item['configured_profile'] for item in selected['sources'] if item.get('configured_profile')}, {'C2'})
		self.assertEqual(selected['platform_injection']['status'], 'unknown')
if '__main__' == __name__:
	unittest.main()
