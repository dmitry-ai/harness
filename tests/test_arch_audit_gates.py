# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add blocking architecture audit gates with module-hash caching":
# https://github.com/dmitry-ai/harness/issues/363
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
_PARENT_ID = '11111111-1111-4111-8111-111111111111'
_REVIEWER_ID = '22222222-2222-4222-8222-222222222222'
# @used-by :func:`_seed_governed_repo()`
# @used-by :meth:`ArchAuditGatesTests.test_staged_pre_commit_enforces_approved_receipts_cache_and_anti_pattern_washing()`
# @used-by :meth:`ArchAuditGatesTests.test_staged_pre_commit_handles_participant_file_paths_and_incremental_multi_wave_commits()`
def _git(repo: Path, *args: str) -> None:
	subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
# @used-by :meth:`ArchAuditGatesTests.test_answer_and_stop_gates_enforce_significant_response_receipt_and_open_findings()`
# @used-by :meth:`ArchAuditGatesTests.test_pre_tool_use_blocks_unaudited_structural_write_and_allows_cached_or_approved_design()`
# @used-by :meth:`ArchAuditGatesTests.test_staged_pre_commit_enforces_approved_receipts_cache_and_anti_pattern_washing()`
# @used-by :meth:`ArchAuditGatesTests.test_staged_pre_commit_handles_participant_file_paths_and_incremental_multi_wave_commits()`
def _record_verdict(proj: Path, prep: dict, *, result: str='approved', outcome: str='grounded', participants_ok: bool=True, findings: list | None=None) -> dict:
	from agent_tools.arch.review_store import record_arch_review
	verdict = {'schema_version': 1, 'review_mode': 'falsifier', 'package': prep['package'], 'package_sha256': prep['package_sha256'], 'result': result, 'summary': 'Falsifier architecture audit verdict.', 'pattern_checks': [{'pattern': 'Strategy', 'category': 'Behavioral', 'participants_verified': participants_ok, 'overengineering_risk': 'low', 'outcome': outcome, 'evidence': 'Checked module symbols and participants.'}], 'findings': [] if None is findings else findings}
	raw = json.dumps(verdict).encode('utf-8')
	proof = {'surface': 'antigravity-ui', 'parent_id': _PARENT_ID, 'reviewer_id': _REVIEWER_ID, 'agent_name': 'arch-auditor', 'final_response': raw.decode('utf-8'), 'final_response_sha256': hashlib.sha256(raw).hexdigest(), 'native_log_sha256': 'e' * 64}
	with patch('agent_tools.arch.review_store._authenticate_arch_report', return_value=proof):
		r = record_arch_review(proj, raw, parent_id=_PARENT_ID, reviewer_id=_REVIEWER_ID)
	return r
# @used-by :meth:`ArchAuditGatesTests.test_arch_audit_gate_spawns_zero_subprocesses_and_allows_trivial_or_test_edits()`
# @used-by :meth:`ArchAuditGatesTests.test_pre_tool_use_blocks_unaudited_structural_write_and_allows_cached_or_approved_design()`
# @used-by :meth:`ArchAuditGatesTests.test_staged_pre_commit_enforces_approved_receipts_cache_and_anti_pattern_washing()`
# @used-by :meth:`ArchAuditGatesTests.test_staged_pre_commit_handles_participant_file_paths_and_incremental_multi_wave_commits()`
def _seed_governed_repo(base: Path, *, with_rule: bool=True) -> Path:
	repo = base / 'repo'
	repo.mkdir(parents=True)
	_git(repo, 'init', '-b', 'main')
	cfg = repo / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + '[user]\n\temail = arch@example.com\n\tname = Arch\n', encoding='utf-8')
	if with_rule:
		rule_f = repo / 'rules/12-architecture.md'
		rule_f.parent.mkdir(parents=True, exist_ok=True)
		rule_f.write_text('# Architecture\n', encoding='utf-8')
	return repo
class ArchAuditGatesTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_answer_and_stop_gates_enforce_significant_response_receipt_and_open_findings(self) -> None:
		from agent_tools.arch.evaluator import evaluate_response_architecture
		from agent_tools.arch.review_store import prepare_arch_package
		from agent_tools.gates import run_stop_gates
		with tempfile.TemporaryDirectory() as td:
			proj = Path(td).resolve()
			(proj / 'rules').mkdir()
			(proj / 'rules/12-architecture.md').write_text('# Architecture\n', encoding='utf-8')
			sig_resp = '## Target Architecture\n\nImplement `scripts/engine.py` with `class StrategyEngine` in `PreToolUse` registry.  \n- **Pattern:** Strategy  \n- **Category:** Behavioral  \n- **Intent:** Encapsulate interchangeable rules.  \n- **Participants:** `StrategyEngine`  \n- **Collaboration:** Engine delegates to strategy.  \n- **Consequences:** Open for extension.  \n'
			chk_missing = evaluate_response_architecture(proj, {}, sig_resp)
			self.assertFalse(chk_missing['verified'])
			self.assertTrue(any(('MISSING_ARCH_AUDIT_RECEIPT' in v for v in chk_missing['violations'])))
			prep = prepare_arch_package(proj, _PARENT_ID, kind='response', response_text=sig_resp)
			_record_verdict(proj, prep, result='approved')
			chk_ok = evaluate_response_architecture(proj, {}, sig_resp)
			self.assertTrue(chk_ok['verified'], chk_ok)
			prep_bad = prepare_arch_package(proj, _PARENT_ID, kind='design', spec_text=sig_resp)
			_record_verdict(proj, prep_bad, result='needs_changes', outcome='pattern_washing', participants_ok=False, findings=[{'id': 'F-9', 'violation_class': 'pattern_washing', 'severity': 'significant', 'target': 'scripts/engine.py', 'description': 'Strategy participant missing.', 'status': 'open'}])
			chk_open = evaluate_response_architecture(proj, {}, 'Plain status update without architecture changes.  \n')
			self.assertFalse(chk_open['verified'])
			self.assertTrue(any(('OPEN_ARCH_FINDING' in v for v in chk_open['violations'])))
		stop_hit = run_stop_gates({'status': 'prepared', 'prepared': {'response_sha256': 'a'}, 'readiness_check': {'verified': True}, 'issue_first_check': {'verified': True}, 'code_lifecycle_check': {'verified': True}, 'arch_audit_check': {'verified': False, 'violations': ['ARCH-2: missing receipt']}, 'tdd_check': {'verified': True}})
		self.assertIsNotNone(stop_hit)
		self.assertEqual('continue', stop_hit['decision'])
		self.assertIn('ARCH', stop_hit['reason'])
		stop_ok = run_stop_gates({'status': 'prepared', 'prepared': {'response_sha256': 'a'}, 'readiness_check': {'verified': True}, 'issue_first_check': {'verified': True}, 'code_lifecycle_check': {'verified': True}, 'arch_audit_check': {'verified': True}, 'tdd_check': {'verified': True}})
		self.assertIsNone(stop_ok)
	# @used-by :mod:`unittest`
	def test_arch_audit_gate_priority_manifest_and_lazy_export(self) -> None:
		from agent_tools.gates import _BUILTIN_TOOLS_MANIFEST, discover_pre_tool_gates
		import check_rules_and_server_gate as rg
		gates = discover_pre_tool_gates()
		by_name = {g['name']: g for g in gates}
		self.assertIn('ARCH-AUDIT-GATE', by_name)
		self.assertEqual(105, by_name['ARCH-AUDIT-GATE']['priority'])
		names = [g['name'] for g in gates]
		self.assertLess(names.index('EXEC-5-ISSUE-FIRST-GATE'), names.index('ARCH-AUDIT-GATE'))
		self.assertLess(names.index('ARCH-AUDIT-GATE'), names.index('EXEC-2-TDD-GATE'))
		self.assertEqual(frozenset({'write_file', 'edit_file'}), _BUILTIN_TOOLS_MANIFEST.get('arch_audit'))
		self.assertTrue(callable(rg.check_arch_audit_gate))
	# @used-by :mod:`unittest`
	def test_arch_audit_gate_spawns_zero_subprocesses_and_allows_trivial_or_test_edits(self) -> None:
		from agent_tools.gates.arch_audit import check as check_arch_gate
		with tempfile.TemporaryDirectory() as td:
			repo = _seed_governed_repo(Path(td).resolve(), with_rule=True)
			util = repo / 'src/util.py'
			util.parent.mkdir(parents=True)
			util.write_text('VAL = 1\n', encoding='utf-8')
			with patch.object(subprocess, 'run', wraps=subprocess.run) as spy:
				r_test = check_arch_gate('write_file', {'Path': str(repo / 'tests/test_u.py'), 'Content': 'class T:\n\tpass\n'}, {'cwd': str(repo)})
				r_triv = check_arch_gate('edit_file', {'Path': str(util), 'Target': 'VAL = 1', 'Replacement': 'VAL = 2'}, {'cwd': str(repo)})
				self.assertEqual(0, spy.call_count)
			self.assertIsNone(r_test)
			self.assertIsNone(r_triv)
	# @used-by :mod:`unittest`
	def test_pre_tool_use_blocks_unaudited_structural_write_and_allows_cached_or_approved_design(self) -> None:
		from agent_tools.arch.review_store import prepare_arch_package
		from agent_tools.gates.arch_audit import check as check_arch_gate
		with tempfile.TemporaryDirectory() as td:
			repo = _seed_governed_repo(Path(td).resolve(), with_rule=True)
			mod_p = repo / 'src/engine.py'
			code = 'class StrategyEngine:\n\tdef run(self):\n\t\treturn 1\n'
			spec = '- **Pattern:** Strategy\n- **Category:** Behavioral\n- **Intent:** Swap engine rules.\n- **Participants:** `StrategyEngine`\n- **Collaboration:** Engine delegates to strategy.\n- **Consequences:** Open for extension.\n'
			denied = check_arch_gate('write_file', {'Path': str(mod_p), 'Content': code}, {'cwd': str(repo)})
			self.assertIsNotNone(denied)
			self.assertIn('ARCH-AUDIT-GATE', denied or '')
			prep_design = prepare_arch_package(repo, _PARENT_ID, kind='design', spec_text=spec)
			_record_verdict(repo, prep_design, result='approved')
			self.assertIsNone(check_arch_gate('write_file', {'Path': str(mod_p), 'Content': code}, {'cwd': str(repo)}))
			mod_p.parent.mkdir(parents=True, exist_ok=True)
			mod_p.write_text(code, encoding='utf-8')
			prep_bad = prepare_arch_package(repo, _PARENT_ID, kind='code_diff', spec_text=spec, repo=repo, files=['src/engine.py'])
			_record_verdict(repo, prep_bad, result='needs_changes', outcome='pattern_washing', participants_ok=False, findings=[{'id': 'F-1', 'violation_class': 'pattern_washing', 'severity': 'significant', 'target': 'src/engine.py', 'description': 'Strategy mismatch.', 'status': 'open'}])
			blocked_open = check_arch_gate('edit_file', {'Path': str(mod_p), 'Target': 'return 1', 'Replacement': 'return 2'}, {'cwd': str(repo)})
			self.assertIsNotNone(blocked_open)
			self.assertIn('F-1', blocked_open or '')
			_record_verdict(repo, prep_bad, result='approved')
			self.assertIsNone(check_arch_gate('write_file', {'Path': str(mod_p), 'Content': code}, {'cwd': str(repo)}))
	# @used-by :mod:`unittest`
	def test_stage4_docs_document_arch_audit_gate_and_lint_cleanly(self) -> None:
		from agent_tools import links
		import check_markdown_slop
		checks = (
			(WT_ROOT / 'scripts/README-agent-tools.md', ('arch-prepare', 'arch-record-review', 'ARCH-AUDIT-GATE')),
			(WT_ROOT / 'scripts/docs/plugin-registries.md', ('ARCH-AUDIT-GATE', '105', 'arch_audit')),
			(WT_ROOT / 'references/turn-completion.md', ('arch_audit_check', 'ARCH-1')),
			(WT_ROOT / 'platforms/antigravity.md', ('arch-auditor', 'df-architecture')),
			(WT_ROOT / 'platforms/codex.md', ('arch-auditor', 'df-architecture')),
		)
		for path, tokens in checks:
			txt = path.read_text(encoding='utf-8')
			for tok in tokens:
				self.assertIn(tok, txt, f'{path.name} missing token {tok}')
			self.assertEqual([], links.validate_file(path, local_anchors=True, readable_links=True), f'Link issues in {path.name}')
			self.assertEqual([], check_markdown_slop.markdown_slop_issues(txt), f'DOC-4 issues in {path.name}')
	# @used-by :mod:`unittest`
	def test_staged_pre_commit_enforces_approved_receipts_cache_and_anti_pattern_washing(self) -> None:
		from agent_tools.arch.review_store import prepare_arch_package
		from agent_tools.staged_gates import verify_staged_extra_gates
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			ungov = _seed_governed_repo(base / 'u', with_rule=False)
			(ungov / 'src').mkdir()
			(ungov / 'src/mod.py').write_text('class Plain:\n\tpass\n', encoding='utf-8')
			_git(ungov, 'add', 'src/mod.py')
			self.assertEqual([], [v for v in verify_staged_extra_gates(ungov, ['src/mod.py'], use_index=True) if 'ARCH-AUDIT-GATE' in v])
			repo = _seed_governed_repo(base / 'g', with_rule=True)
			mod_p = repo / 'src/engine.py'
			mod_p.parent.mkdir(parents=True)
			mod_p.write_text('class ProceduralBlob:\n\tdef run(self):\n\t\treturn 1\n', encoding='utf-8')
			_git(repo, 'add', 'src/engine.py')
			v_un = [v for v in verify_staged_extra_gates(repo, ['src/engine.py'], use_index=True) if 'ARCH-AUDIT-GATE' in v]
			self.assertTrue(bool(v_un), 'Expected unaudited staged structural change to fail')
			spec = '- **Pattern:** Strategy\n- **Category:** Behavioral\n- **Intent:** Swap engine rules.\n- **Participants:** `StrategyEngine`\n- **Collaboration:** Engine delegates to strategy.\n- **Consequences:** Open for extension.\n'
			prep_d = prepare_arch_package(repo, _PARENT_ID, kind='design', spec_text=spec)
			_record_verdict(repo, prep_d, result='approved')
			v_pw = [v for v in verify_staged_extra_gates(repo, ['src/engine.py'], use_index=True) if 'ARCH-AUDIT-GATE' in v]
			self.assertTrue(any(('StrategyEngine' in v for v in v_pw)), f'Expected missing participant failure, got {v_pw}')
			mod_p.write_text('class StrategyEngine:\n\tdef run(self):\n\t\treturn 1\n', encoding='utf-8')
			_git(repo, 'add', 'src/engine.py')
			self.assertEqual([], [v for v in verify_staged_extra_gates(repo, ['src/engine.py'], use_index=True) if 'ARCH-AUDIT-GATE' in v])
			prep_c = prepare_arch_package(repo, _PARENT_ID, kind='code_diff', spec_text=spec, repo=repo, files=['src/engine.py'])
			_record_verdict(repo, prep_c, result='approved')
			self.assertEqual([], [v for v in verify_staged_extra_gates(repo, ['src/engine.py'], use_index=True) if 'ARCH-AUDIT-GATE' in v])
			_record_verdict(repo, prep_c, result='needs_changes', outcome='overengineered', participants_ok=False, findings=[{'id': 'F-2', 'violation_class': 'overengineering', 'severity': 'critical', 'target': 'src/engine.py', 'description': 'Unnecessary wrapper.', 'status': 'open'}])
			v_open = [v for v in verify_staged_extra_gates(repo, ['src/engine.py'], use_index=True) if 'ARCH-AUDIT-GATE' in v]
			self.assertTrue(any(('F-2' in v for v in v_open)), f'Expected open finding failure, got {v_open}')
	# 2026-11-27 "Fix _missing_design_participants for file paths and multi-wave commits": https://github.com/dmitry-ai/harness/issues/395
	# @used-by :mod:`unittest`
	def test_staged_pre_commit_handles_participant_file_paths_and_incremental_multi_wave_commits(self) -> None:
		from agent_tools.arch.review_store import prepare_arch_package
		from agent_tools.staged_gates import verify_staged_extra_gates
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			r1 = _seed_governed_repo(base / 'mixed', with_rule=True)
			mixed_spec = '- **Pattern:** Strategy\n- **Category:** Behavioral\n- **Intent:** Split waves across modules.\n- **Participants:** `scripts/a.py` (`WaveAlpha`), `scripts/b.py` (`WaveBeta`)\n- **Collaboration:** WaveAlpha collaborates with WaveBeta.\n- **Consequences:** Incremental multi-wave commits.\n'
			_record_verdict(r1, prepare_arch_package(r1, _PARENT_ID, kind='design', spec_text=mixed_spec), result='approved')
			a1 = r1 / 'scripts/a.py'
			a1.parent.mkdir(parents=True)
			a1.write_text('class WaveAlpha:\n\tdef run(self):\n\t\treturn 1\n', encoding='utf-8')
			_git(r1, 'add', 'scripts/a.py')
			self.assertEqual([], [v for v in verify_staged_extra_gates(r1, ['scripts/a.py'], use_index=True) if 'ARCH-AUDIT-GATE' in v])
			a1.write_text('class ProceduralBlob:\n\tdef run(self):\n\t\treturn 1\n', encoding='utf-8')
			_git(r1, 'add', 'scripts/a.py')
			v_bad = [v for v in verify_staged_extra_gates(r1, ['scripts/a.py'], use_index=True) if 'ARCH-AUDIT-GATE' in v]
			self.assertTrue(any(('WaveAlpha' in v for v in v_bad)), f'Expected missing symbol failure, got {v_bad}')
			r2 = _seed_governed_repo(base / 'path_only', with_rule=True)
			path_spec = '- **Pattern:** Facade\n- **Category:** Structural\n- **Intent:** Group modules behind facade.\n- **Participants:** `scripts/a.py`, `scripts/b.py`\n- **Collaboration:** Module a calls module b.\n- **Consequences:** Clear file boundaries.\n'
			_record_verdict(r2, prepare_arch_package(r2, _PARENT_ID, kind='design', spec_text=path_spec), result='approved')
			a2 = r2 / 'scripts/a.py'
			a2.parent.mkdir(parents=True)
			a2.write_text('class PathMod:\n\tdef run(self):\n\t\treturn 1\n', encoding='utf-8')
			_git(r2, 'add', 'scripts/a.py')
			self.assertEqual([], [v for v in verify_staged_extra_gates(r2, ['scripts/a.py'], use_index=True) if 'ARCH-AUDIT-GATE' in v])
			o2 = r2 / 'scripts/other.py'
			o2.write_text('class OtherMod:\n\tdef run(self):\n\t\treturn 2\n', encoding='utf-8')
			_git(r2, 'add', 'scripts/other.py')
			v_other = [v for v in verify_staged_extra_gates(r2, ['scripts/other.py'], use_index=True) if 'ARCH-AUDIT-GATE' in v]
			self.assertTrue(any(('scripts/a.py' in v for v in v_other)), f'Expected missing path participant failure, got {v_other}')
if '__main__' == __name__:
	unittest.main()
