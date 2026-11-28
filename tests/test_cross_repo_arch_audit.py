# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
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
# 2026-11-28 "Recognize cross-repo approved arch-auditor receipts in Enforcement.verify_staged": https://github.com/dmitry-ai/harness/issues/467
# @used-by :func:`_seed_repo()`
# @used-by :meth:`CrossRepoArchAuditTests.test_pre_tool_use_and_verify_staged_scope_receipts_and_findings_by_slug()`
# @used-by :meth:`CrossRepoArchAuditTests.test_pre_tool_use_isolates_foreign_cwd_and_null_issue_receipts()`
def _git(repo: Path, *args: str) -> None:
	subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
# @used-by :meth:`CrossRepoArchAuditTests.test_pre_tool_use_and_verify_staged_scope_receipts_and_findings_by_slug()`
# @used-by :meth:`CrossRepoArchAuditTests.test_pre_tool_use_isolates_foreign_cwd_and_null_issue_receipts()`
# @used-by :meth:`CrossRepoArchAuditTests.test_review_store_scopes_cross_repo_module_cache_and_finding_clearing()`
def _record(root: Path, prep: dict, *, result: str='approved', outcome: str='grounded', participants_ok: bool=True, findings: list | None=None) -> dict:
	from Df.Harness.Arch.ReviewStore import ReviewStore
	verdict = {'schema_version': 1, 'review_mode': 'falsifier', 'package': prep['package'], 'package_sha256': prep['package_sha256'], 'result': result, 'summary': 'Verified.', 'pattern_checks': [{'pattern': 'Repository', 'category': 'Architectural', 'participants_verified': participants_ok, 'overengineering_risk': 'low', 'outcome': outcome, 'evidence': 'Checked.'}], 'findings': [] if None is findings else findings}
	raw = json.dumps(verdict).encode('utf-8')
	return ReviewStore(root, auth_fn=lambda *a, **kw: {'final_response_sha256': hashlib.sha256(raw).hexdigest(), 'proof': 'ok'}).record_review(raw, parent_id=_PARENT_ID, reviewer_id=_REVIEWER_ID)
# @used-by :meth:`CrossRepoArchAuditTests.test_arch_role_allows_downward_target_repo_only_and_blocks_ancestors_and_aa()`
# @used-by :meth:`CrossRepoArchAuditTests.test_pre_tool_use_and_verify_staged_scope_receipts_and_findings_by_slug()`
# @used-by :meth:`CrossRepoArchAuditTests.test_pre_tool_use_isolates_foreign_cwd_and_null_issue_receipts()`
# @used-by :meth:`CrossRepoArchAuditTests.test_review_store_scopes_cross_repo_module_cache_and_finding_clearing()`
def _seed_repo(repo: Path, *, origin: str | None=None) -> Path:
	repo.mkdir(parents=True, exist_ok=True)
	_git(repo, 'init', '-b', 'main')
	cfg = repo / '.git/config'
	extra = f'[user]\n\temail = arch@example.com\n\tname = Arch\n' + (f'[remote "origin"]\n\turl = {origin}\n' if origin else '')
	cfg.write_text(cfg.read_text(encoding='utf-8') + extra, encoding='utf-8')
	rule_f = repo / 'rules/12-architecture.md'
	rule_f.parent.mkdir(parents=True, exist_ok=True)
	rule_f.write_text('# Architecture\n', encoding='utf-8')
	return repo
# 2026-11-28 "Recognize cross-repo approved arch-auditor receipts in Enforcement.verify_staged": https://github.com/dmitry-ai/harness/issues/467
class CrossRepoArchAuditTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_arch_role_allows_downward_target_repo_only_and_blocks_ancestors_and_aa(self) -> None:
		from Df.Harness.Arch.ReviewStore import ReviewStore
		from Df.Harness.lib.trace_review import dfh_build_native_review_proof
		with tempfile.TemporaryDirectory() as td:
			ai_root = Path(td).resolve() / 'AI'
			harness_root = ai_root / 'harness'
			peer_root = ai_root / 'products/Google/Addons'
			peer_code = _seed_repo(peer_root / '\u2c0f/\u227b/\u2655/\u26ef', origin='https://github.com/dmitry-ai/antigravity-addons.git')
			other_root = ai_root / 'products/OpenAI/ChatGPT'
			(harness_root / '\ua616/data').mkdir(parents=True, exist_ok=True)
			(peer_code / 'Multi-Account').mkdir(parents=True, exist_ok=True)
			other_root.mkdir(parents=True, exist_ok=True)
			target_file = peer_code / 'Multi-Account/launcher.js'
			target_file.write_text('module.exports = {};\n', encoding='utf-8')
			other_file = other_root / 'secret.js'
			other_file.write_text('x\n', encoding='utf-8')
			spec = '- **Pattern:** Facade\n- **Category:** Structural\n- **Intent:** Provision.\n- **Participants:** `Multi-Account/launcher.js`\n- **Collaboration:** Calls.\n- **Consequences:** Clean.\n'
			prep = ReviewStore.prepare_package(harness_root, _PARENT_ID, kind='design', spec_text=spec, repo=peer_code, issue_url='https://github.com/dmitry-ai/antigravity-addons/issues/75')
			pkg_data = json.loads((harness_root / prep['package']).read_text(encoding='utf-8'))
			self.assertEqual(peer_code.resolve().as_posix(), pkg_data.get('target_repo'))
			prompt = f"Audit `{prep['package']}` in `{harness_root.as_posix()}`."
			ok_rows = [{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'read_file', 'args': {'Path': str(target_file)}}]}]
			proof = dfh_build_native_review_proof(harness_root, 'antigravity-ui', _PARENT_ID, _REVIEWER_ID, 'arch-auditor', harness_root / 'c.jsonl', harness_root / 'p.jsonl', b'{}', 2, '{}', [prompt], ok_rows, write=False, role='ARCH')
			self.assertEqual('completed', proof['status'])
			anc_rows = [{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'find_by_name', 'args': {'SearchPath': str(ai_root / 'products')}}]}]
			with self.assertRaisesRegex(ValueError, 'sibling project path'):
				dfh_build_native_review_proof(harness_root, 'antigravity-ui', _PARENT_ID, _REVIEWER_ID, 'arch-auditor', harness_root / 'c.jsonl', harness_root / 'p.jsonl', b'{}', 2, '{}', [prompt], anc_rows, write=False, role='ARCH')
			with self.assertRaisesRegex(ValueError, 'sibling project path'):
				dfh_build_native_review_proof(harness_root, 'antigravity-ui', _PARENT_ID, _REVIEWER_ID, 'self', harness_root / 'c.jsonl', harness_root / 'p.jsonl', b'{}', 2, '{}', [prompt], ok_rows, write=False, role='AA')
			other_rows = [{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'read_file', 'args': {'Path': str(other_file)}}]}]
			with self.assertRaisesRegex(ValueError, 'sibling project path'):
				dfh_build_native_review_proof(harness_root, 'antigravity-ui', _PARENT_ID, _REVIEWER_ID, 'arch-auditor', harness_root / 'c.jsonl', harness_root / 'p.jsonl', b'{}', 2, '{}', [prompt], other_rows, write=False, role='ARCH')
			write_rows = [{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'edit_file', 'args': {'Path': str(target_file)}}]}]
			with self.assertRaisesRegex(ValueError, 'mutating tool'):
				dfh_build_native_review_proof(harness_root, 'antigravity-ui', _PARENT_ID, _REVIEWER_ID, 'arch-auditor', harness_root / 'c.jsonl', harness_root / 'p.jsonl', b'{}', 2, '{}', [prompt], write_rows, write=False, role='ARCH')
	# @used-by :mod:`unittest`
	def test_pre_tool_use_isolates_foreign_cwd_and_null_issue_receipts(self) -> None:
		from Df.Harness.Arch.Enforcement import Enforcement
		from Df.Harness.Arch.RepoReceiptSpecification import RepoReceiptSpecification
		from Df.Harness.Arch.ReviewStore import ReviewStore
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			harness_root = base / 'harness'
			_seed_repo(harness_root / '\u2c0f/\u227b/\u2655/\u26ef', origin='https://github.com/dmitry-ai/harness.git')
			peer = _seed_repo(base / 'peer', origin='https://github.com/dmitry-ai/antigravity-addons.git')
			local_only = _seed_repo(base / 'local_only')
			peer_mod = peer / 'Multi-Account/profile-manager.js'
			peer_code = 'class ProfileRepository {\n\tload() { return []; }\n}\n'
			peer_mod.parent.mkdir(parents=True)
			peer_mod.write_text(peer_code, encoding='utf-8')
			_git(peer, 'add', 'Multi-Account/profile-manager.js')
			h_spec = '- **Pattern:** Adapter\n- **Category:** Structural\n- **Intent:** Harness only.\n- **Participants:** `ProfileRepository`, `HarnessEngine`\n- **Collaboration:** Isolated.\n- **Consequences:** Isolated.\n'
			_record(harness_root, ReviewStore.prepare_package(harness_root, _PARENT_ID, kind='design', spec_text=h_spec, issue_url='https://github.com/dmitry-ai/harness/issues/464'), result='approved')
			_record(harness_root, ReviewStore.prepare_package(harness_root, _PARENT_ID, kind='design', spec_text=h_spec), result='approved')
			with patch.object(RepoReceiptSpecification, 'harness_arch_root', return_value=harness_root):
				self.assertTrue(any(('lacks a matching approved' in v for v in Enforcement().verify_staged(peer, ['Multi-Account/profile-manager.js'], use_index=True))))
				with patch.object(subprocess, 'run', wraps=subprocess.run) as spy:
					denied_peer = Enforcement.evaluate_pre_tool_use('write_file', {'Path': str(peer / 'Multi-Account/new-manager.js'), 'Content': peer_code}, {'cwd': str(harness_root)})
					denied_local = Enforcement.evaluate_pre_tool_use('write_file', {'Path': str(local_only / 'src/x.py'), 'Content': 'class X:\n\tpass\n'}, {'cwd': str(harness_root)})
					self.assertEqual(0, spy.call_count)
				self.assertIsNotNone(denied_peer)
				self.assertIsNotNone(denied_local)
	# @used-by :mod:`unittest`
	def test_pre_tool_use_and_verify_staged_scope_receipts_and_findings_by_slug(self) -> None:
		from Df.Harness.Arch.Enforcement import Enforcement
		from Df.Harness.Arch.RepoReceiptSpecification import RepoReceiptSpecification
		from Df.Harness.Arch.ReviewStore import ReviewStore
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			harness_root = base / 'harness'
			harness_code = _seed_repo(harness_root / '\u2c0f/\u227b/\u2655/\u26ef', origin='https://github.com/dmitry-ai/harness.git')
			peer = _seed_repo(base / 'peer', origin='https://github.com/dmitry-ai/antigravity-addons.git')
			peer_mod = peer / 'Multi-Account/profile-manager.js'
			peer_code = 'class ProfileRepository {\n\tload() { return []; }\n}\n'
			peer_mod.parent.mkdir(parents=True)
			peer_mod.write_text(peer_code, encoding='utf-8')
			_git(peer, 'add', 'Multi-Account/profile-manager.js')
			h_spec = '- **Pattern:** Adapter\n- **Category:** Structural\n- **Intent:** Harness only.\n- **Participants:** `HarnessEngine`\n- **Collaboration:** Isolated.\n- **Consequences:** Isolated.\n'
			_record(harness_root, ReviewStore.prepare_package(harness_root, _PARENT_ID, kind='design', spec_text=h_spec, issue_url='https://github.com/dmitry-ai/harness/issues/464'), result='approved')
			p_spec = '- **Pattern:** Repository\n- **Category:** Architectural\n- **Intent:** Manage profiles.\n- **Participants:** `ProfileRepository`\n- **Collaboration:** Persists profiles.\n- **Consequences:** Clean boundary.\n'
			p_peer = ReviewStore.prepare_package(harness_root, _PARENT_ID, kind='design', spec_text=p_spec, repo=peer, issue_url='https://github.com/dmitry-ai/antigravity-addons/issues/75')
			_record(harness_root, p_peer, result='approved')
			with patch.object(RepoReceiptSpecification, 'harness_arch_root', return_value=harness_root):
				self.assertEqual([], Enforcement().verify_staged(peer, ['Multi-Account/profile-manager.js'], use_index=True))
				with patch.object(subprocess, 'run', wraps=subprocess.run) as spy:
					self.assertIsNone(Enforcement.evaluate_pre_tool_use('write_file', {'Path': str(peer_mod), 'Content': peer_code}, {'cwd': str(peer)}))
					self.assertIsNone(Enforcement.evaluate_pre_tool_use('write_file', {'Path': str(peer_mod), 'Content': peer_code}, {'cwd': str(harness_root)}))
					self.assertEqual(0, spy.call_count)
				_record(harness_root, p_peer, result='needs_changes', outcome='pattern_washing', participants_ok=False, findings=[{'id': 'ARCH-F9', 'violation_class': 'other', 'severity': 'significant', 'target': 'Multi-Account/profile-manager.js', 'description': 'Blocking peer finding.', 'status': 'open'}])
				self.assertTrue(any(('ARCH-F9' in v for v in Enforcement().verify_staged(peer, ['Multi-Account/profile-manager.js'], use_index=True))))
				h_mod = harness_code / 'scripts/engine.py'
				h_code = 'class HarnessEngine:\n\tdef run(self):\n\t\treturn 1\n'
				h_mod.parent.mkdir(parents=True)
				h_mod.write_text(h_code, encoding='utf-8')
				_git(harness_code, 'add', 'scripts/engine.py')
				self.assertEqual([], Enforcement().verify_staged(harness_code, ['scripts/engine.py'], use_index=True))
				self.assertIsNone(Enforcement.evaluate_pre_tool_use('write_file', {'Path': str(h_mod), 'Content': h_code}, {'cwd': str(harness_root)}))
	# @used-by :mod:`unittest`
	def test_review_store_scopes_cross_repo_module_cache_and_finding_clearing(self) -> None:
		from Df.Harness.Arch.ReviewStore import ReviewStore
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			harness_root = _seed_repo(base / 'harness', origin='https://github.com/dmitry-ai/harness.git')
			peer = _seed_repo(base / 'peer', origin='https://github.com/dmitry-ai/antigravity-addons.git')
			(harness_root / 'src').mkdir()
			(harness_root / 'src/shared.py').write_text('class LocalMod:\n\tpass\n', encoding='utf-8')
			(peer / 'src').mkdir()
			(peer / 'src/shared.py').write_text('class PeerMod:\n\tpass\n', encoding='utf-8')
			spec = '- **Pattern:** Repository\n- **Category:** Architectural\n- **Intent:** Mod.\n- **Participants:** `LocalMod`, `PeerMod`\n- **Collaboration:** Isolated.\n- **Consequences:** Safe.\n'
			p_local = ReviewStore.prepare_package(harness_root, _PARENT_ID, kind='code_diff', spec_text=spec, repo=harness_root, files=['src/shared.py'], issue_url='https://github.com/dmitry-ai/harness/issues/1')
			_record(harness_root, p_local, result='needs_changes', outcome='pattern_washing', participants_ok=False, findings=[{'id': 'LOC-1', 'violation_class': 'other', 'severity': 'significant', 'target': 'src/shared.py', 'description': 'Local open.', 'status': 'open'}])
			p_peer = ReviewStore.prepare_package(harness_root, _PARENT_ID, kind='code_diff', spec_text=spec, repo=peer, files=['src/shared.py'], issue_url='https://github.com/dmitry-ai/antigravity-addons/issues/75')
			_record(harness_root, p_peer, result='approved')
			idx = json.loads((harness_root / '\ua616/data/arch-reviews/index.json').read_text(encoding='utf-8'))
			self.assertNotIn('src/shared.py', idx['approved_modules'])
			self.assertTrue(any(('LOC-1' == f.get('id') for f in idx['open_findings'])))
if '__main__' == __name__:
	unittest.main()