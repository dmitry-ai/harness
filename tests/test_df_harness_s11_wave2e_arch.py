# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast
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
_ARCH_MODULES = (
	'Catalog',
	'Enforcement',
	'Evaluator',
	'NativeRole',
	# 2026-11-28 "Recognize cross-repo approved arch-auditor receipts in Enforcement.verify_staged": https://github.com/dmitry-ai/harness/issues/467
	'RepoReceiptSpecification',
	'ReviewCli',
	'ReviewStore',
	'ReviewValidator',
	'SpecValidator',
	'StructureVisitor',
	'TriggerClassifier',
)
_PARENT_ID = '11111111-1111-4111-8111-111111111111'
_REVIEWER_ID = '22222222-2222-4222-8222-222222222222'
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
# @used-by :meth:`DfHarnessArchWave2eTests.test_s11_arch_invariants_and_zero_class_facades()`
def _arch_backward_imports(tree: ast.AST) -> list[str]:
	bad: list[str] = []
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			bad.extend((a.name for a in node.names if a.name.startswith('agent_tools.arch')))
		elif isinstance(node, ast.ImportFrom) and (node.module or '').startswith('agent_tools.arch'):
			bad.append(node.module or '')
	return bad
# @used-by :func:`_seed_repo()`
# @used-by :meth:`DfHarnessArchWave2eTests.test_enforcement_preserves_gates_and_395_participants()`
def _git(repo: Path, *args: str) -> None:
	subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
# @used-by :meth:`DfHarnessArchWave2eTests.test_s11_arch_invariants_and_zero_class_facades()`
def _has_decorator(fn: ast.FunctionDef | ast.AsyncFunctionDef, names: set[str]) -> bool:
	return any((isinstance(d, ast.Name) and d.id in names for d in fn.decorator_list))
# @used-by :meth:`DfHarnessArchWave2eTests.test_enforcement_preserves_gates_and_395_participants()`
# @used-by :meth:`DfHarnessArchWave2eTests.test_evaluator_checks_response_receipts_and_runner()`
# @used-by :meth:`DfHarnessArchWave2eTests.test_review_cli_registers_and_executes_all_arch_commands()`
# @used-by :meth:`DfHarnessArchWave2eTests.test_review_store_roundtrip_auth_and_patch_seam()`
# @used-by :meth:`DfHarnessArchWave2eTests.test_review_validator_and_facade_alias()`
def _sample_verdict(pkg_rel: str, pkg_sha: str, *, result: str='approved', outcome: str='grounded', participants_ok: bool=True, findings: list | None=None) -> dict:
	return {
		'schema_version': 1,
		'review_mode': 'falsifier',
		'package': pkg_rel,
		'package_sha256': pkg_sha,
		'result': result,
		'summary': 'Verified Strategy participants against module symbols.',
		'pattern_checks': [{'pattern': 'Strategy', 'category': 'Behavioral', 'participants_verified': participants_ok, 'overengineering_risk': 'low', 'outcome': outcome, 'evidence': 'Checked module symbols.'}],
		'findings': [] if None is findings else findings,
	}
# @used-by :meth:`DfHarnessArchWave2eTests.test_enforcement_preserves_gates_and_395_participants()`
# @used-by :meth:`DfHarnessArchWave2eTests.test_evaluator_checks_response_receipts_and_runner()`
def _seed_repo(base: Path) -> Path:
	repo = base / 'repo'
	repo.mkdir(parents=True)
	_git(repo, 'init', '-b', 'main')
	cfg = repo / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + '[user]\n\temail = arch@example.com\n\tname = Arch\n', encoding='utf-8')
	rule_f = repo / 'rules/12-architecture.md'
	rule_f.parent.mkdir(parents=True, exist_ok=True)
	rule_f.write_text('# Architecture\n', encoding='utf-8')
	return repo
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
class DfHarnessArchWave2eTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_catalog_and_spec_validator_resolve_patterns_and_idiom_exceptions(self) -> None:
		from Df.Harness.Arch.Catalog import Catalog
		from Df.Harness.Arch.SpecValidator import SpecValidator
		from agent_tools.arch.catalog import catalog_pattern_names, load_pattern_catalog, lookup_pattern
		from agent_tools.arch.spec import extract_arch_specs, extract_declared_participants, validate_arch_spec_markdown
		cat = Catalog.load(WT_ROOT)
		self.assertEqual(1, cat['schema_version'])
		self.assertIn('Strategy', Catalog.names(catalog=cat))
		self.assertEqual(Catalog.load()['schema_version'], load_pattern_catalog(WT_ROOT)['schema_version'])
		self.assertIn('Proxy', catalog_pattern_names(catalog=cat))
		hit = Catalog(WT_ROOT).lookup('**Protection Proxy**')
		self.assertEqual('Proxy', hit['name'])
		self.assertEqual('Memento', lookup_pattern('Memento / Immutable Snapshot', catalog=cat)['name'])
		self.assertIsNone(Catalog(catalog=cat).lookup('NoSuchPattern'))
		valid_md = '- **Pattern:** Strategy (`Behavioral`)\n- **Intent:** Swap rules.\n- **Participants:** `StrategyEngine`, `RuleSet`\n- **Collaboration:** Engine delegates.\n- **Consequences:** Open extension.\n# Next\n'
		specs = SpecValidator.extract_specs(valid_md)
		self.assertEqual(extract_arch_specs(valid_md), specs)
		self.assertEqual(['StrategyEngine', 'RuleSet'], SpecValidator.extract_declared_participants(specs))
		self.assertEqual(['StrategyEngine', 'RuleSet'], extract_declared_participants(specs))
		res_ok = SpecValidator(catalog=cat).validate(valid_md, require_full_fields=True)
		self.assertTrue(res_ok['valid'], res_ok)
		idiom_md = '- **idiom_exception:** Factory Method\n- **Native Construct:** Python direct constructor call\n- **Rationale:** Direct instantiation removes static wrapper boilerplate cleanly.\n- **Participants:** `Catalog`, `SpecValidator`\n'
		self.assertTrue(validate_arch_spec_markdown(idiom_md, require_full_fields=True, catalog=cat)['valid'])
		bad_md = '- **Pattern:** FakePattern\n- **Pattern:** Strategy\n- **Category:** Creational\n- **idiom_exception:** UnknownPat\n- **idiom_exception:** Strategy\n- **Rationale:** short\n'
		res_bad = SpecValidator(catalog=cat).validate(bad_md, require_full_fields=True)
		codes = {it['code'] for it in res_bad['issues']}
		self.assertTrue({'UNRECOGNIZED_ARCH_PATTERN', 'MISMATCHED_ARCH_CATEGORY', 'INCOMPLETE_ARCH_SPEC_FIELDS', 'INVALID_IDIOM_EXCEPTION'}.issubset(codes), codes)
		self.assertIn('MISSING_ARCH_PATTERN_SPEC', {it['code'] for it in SpecValidator(catalog=cat).validate('plain prose')['issues']})
	# @used-by :mod:`unittest`
	def test_enforcement_preserves_gates_and_395_participants(self) -> None:
		from Df.Harness.Arch.Enforcement import Enforcement
		from Df.Harness.Arch.ReviewStore import ReviewStore
		from agent_tools.arch.enforcement import evaluate_pre_tool_use_arch_audit, verify_staged_arch_audit
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			repo = _seed_repo(base / 'r1')
			mod = repo / 'scripts/a.py'
			code = 'class WaveAlpha:\n\tdef run(self):\n\t\treturn 1\n'
			self.assertIsNotNone(Enforcement.evaluate_pre_tool_use('write_file', {'Path': str(mod), 'Content': code}, {'cwd': str(repo)}))
			self.assertIsNotNone(evaluate_pre_tool_use_arch_audit('write_file', {'Path': str(mod), 'Content': code}, {'cwd': str(repo)}))
			spec = '- **Pattern:** Strategy\n- **Category:** Behavioral\n- **Intent:** Split waves.\n- **Participants:** `scripts/a.py` (`WaveAlpha`), `scripts/b.py` (`WaveBeta`)\n- **Collaboration:** Alpha calls Beta.\n- **Consequences:** Incremental waves.\n'
			prep = ReviewStore.prepare_package(repo, _PARENT_ID, kind='design', spec_text=spec)
			raw = json.dumps(_sample_verdict(prep['package'], prep['package_sha256'])).encode('utf-8')
			ReviewStore(repo, auth_fn=lambda *a, **kw: {'final_response_sha256': hashlib.sha256(raw).hexdigest(), 'proof': 'ok'}).record_review(raw, parent_id=_PARENT_ID, reviewer_id=_REVIEWER_ID)
			self.assertIsNone(Enforcement.evaluate_pre_tool_use('write_file', {'Path': str(mod), 'Content': code}, {'cwd': str(repo)}))
			mod.parent.mkdir(parents=True)
			mod.write_text(code, encoding='utf-8')
			_git(repo, 'add', 'scripts/a.py')
			self.assertEqual([], Enforcement().verify_staged(repo, ['scripts/a.py'], use_index=True))
			mod.write_text('class OtherBlob:\n\tdef run(self):\n\t\treturn 2\n', encoding='utf-8')
			_git(repo, 'add', 'scripts/a.py')
			self.assertTrue(any(('WaveAlpha' in v for v in verify_staged_arch_audit(repo, ['scripts/a.py'], use_index=True))))
			repo2 = _seed_repo(base / 'r2')
			spec2 = '- **Pattern:** Facade\n- **Category:** Structural\n- **Intent:** Path participants.\n- **Participants:** `scripts/a.py`, `scripts/b.py`\n- **Collaboration:** Facade delegates.\n- **Consequences:** Clear paths.\n'
			prep2 = ReviewStore.prepare_package(repo2, _PARENT_ID, kind='design', spec_text=spec2)
			raw2 = json.dumps(_sample_verdict(prep2['package'], prep2['package_sha256'])).encode('utf-8')
			ReviewStore(repo2, auth_fn=lambda *a, **kw: {'final_response_sha256': hashlib.sha256(raw2).hexdigest(), 'proof': 'ok'}).record_review(raw2, parent_id=_PARENT_ID, reviewer_id=_REVIEWER_ID)
			(repo2 / 'scripts').mkdir()
			(repo2 / 'scripts/a.py').write_text('class PathMod:\n\tpass\n', encoding='utf-8')
			(repo2 / 'scripts/other.py').write_text('class OtherMod:\n\tpass\n', encoding='utf-8')
			_git(repo2, 'add', 'scripts/a.py', 'scripts/other.py')
			self.assertEqual([], Enforcement().verify_staged(repo2, ['scripts/a.py'], use_index=True))
			self.assertTrue(any(('scripts/a.py' in v for v in Enforcement().verify_staged(repo2, ['scripts/other.py'], use_index=True))))
			# 2026-11-28 "Match any approved design in Enforcement.__check_uncached_staged": https://github.com/dmitry-ai/harness/issues/449
			for extra_spec in ('- **Pattern:** Strategy\n- **Category:** Behavioral\n- **Intent:** Empty.\n- **Participants:** none\n- **Collaboration:** None.\n- **Consequences:** None.\n', '- **Pattern:** Strategy\n- **Category:** Behavioral\n- **Intent:** Concurrent.\n- **Participants:** `BetaEngine`\n- **Collaboration:** Beta.\n- **Consequences:** Concurrent.\n'):
				ep = ReviewStore.prepare_package(repo2, _PARENT_ID, kind='design', spec_text=extra_spec)
				ReviewStore(repo2, auth_fn=lambda *a, **kw: {'final_response_sha256': hashlib.sha256(er).hexdigest(), 'proof': 'ok'}).record_review(er := json.dumps(_sample_verdict(ep['package'], ep['package_sha256'])).encode('utf-8'), parent_id=_PARENT_ID, reviewer_id=_REVIEWER_ID)
			self.assertEqual([], Enforcement().verify_staged(repo2, ['scripts/a.py'], use_index=True))
			self.assertTrue(any(('BetaEngine' in v for v in Enforcement().verify_staged(repo2, ['scripts/other.py'], use_index=True))))
			self.assertFalse(Enforcement.is_arch_governed(base / 'ungoverned', None, {}, []))
	# @used-by :mod:`unittest`
	def test_evaluator_checks_response_receipts_and_runner(self) -> None:
		from Df.Harness.Arch.Evaluator import Evaluator
		from Df.Harness.Arch.ReviewStore import ReviewStore
		from agent_tools.arch.evaluator import check_runner_architecture, evaluate_response_architecture
		with tempfile.TemporaryDirectory() as td:
			repo = _seed_repo(Path(td).resolve())
			sig = '## Target Architecture\nImplement `scripts/e.py` with `class StrategyEngine` in `PreToolUse` registry.  \n- **Pattern:** Strategy  \n- **Category:** Behavioral  \n'
			self.assertFalse(Evaluator().evaluate_response(repo, {}, sig)['verified'])
			self.assertTrue(evaluate_response_architecture(repo, {}, sig, blocked_report=True)['verified'])
			prep = ReviewStore.prepare_package(repo, _PARENT_ID, kind='response', response_text=sig)
			raw = json.dumps(_sample_verdict(prep['package'], prep['package_sha256'])).encode('utf-8')
			ReviewStore(repo, auth_fn=lambda *a, **kw: {'final_response_sha256': hashlib.sha256(raw).hexdigest(), 'proof': 'ok'}).record_review(raw, parent_id=_PARENT_ID, reviewer_id=_REVIEWER_ID)
			self.assertTrue(Evaluator().evaluate_response(repo, {}, sig)['verified'])
			failed: list[tuple[str, str]] = []
			bad_sig = '## Target Architecture\nImplement `scripts/e.py` with `class BadEngine` in `PreToolUse` registry.  \n'
			runner = SimpleNamespace(root=repo, turn={}, value={}, response=bad_sig, blocked_report=False, _fail_gate=lambda g, d: failed.append((g, d)))
			check_runner_architecture(runner)
			Evaluator.check_runner(runner)
			self.assertEqual(2, len(failed))
			self.assertEqual('architecture', failed[0][0])
	# @used-by :mod:`unittest`
	def test_native_role_generates_antigravity_and_codex_paths(self) -> None:
		from Df.Harness.Arch.NativeRole import NativeRole
		from agent_tools.arch.native_role import codex_role_protocol_path, populate_antigravity_roles
		self.assertTrue(NativeRole.codex_protocol_path(WT_ROOT, 'ARCH').endswith('agents/arch-protocol.md'))
		self.assertTrue(codex_role_protocol_path(WT_ROOT, 'AF').endswith('agents/worker.md'))
		outputs: dict[Path, str] = {}
		cfg = {'roles': {'AF': {'tier': 'flash'}, 'ARCH': {'selection': 'parent', 'tier': 'pro'}}}
		NativeRole().populate_antigravity(outputs, WT_ROOT, WT_ROOT, cfg)
		self.assertIn('model: flash\n', outputs[WT_ROOT / 'agents/af-worker.md'])
		self.assertNotIn('model:', outputs[WT_ROOT / 'agents/arch-auditor.md'])
		out_facade: dict[Path, str] = {}
		populate_antigravity_roles(out_facade, WT_ROOT, WT_ROOT, cfg)
		self.assertEqual(outputs, out_facade)
	# @used-by :mod:`unittest`
	def test_review_cli_registers_and_executes_all_arch_commands(self) -> None:
		from Df.Harness.Arch.ReviewCli import ReviewCli
		from Df.Harness.Arch.ReviewStore import ReviewStore
		from agent_tools.arch.review_cli import register_arch_commands
		cmds: dict[str, tuple] = {}
		# @used-by :meth:`DfHarnessArchWave2eTests.test_review_cli_registers_and_executes_all_arch_commands()`
		def _reg(name, _help, _args, handler, **kw):
			cmds[name] = (handler, kw)
		ReviewCli().register(_reg)
		self.assertEqual({'arch-check', 'arch-prepare', 'arch-record-review', 'arch-review-input'}, set(cmds))
		facade_cmds: dict[str, tuple] = {}
		register_arch_commands(lambda n, h, a, fn, **kw: facade_cmds.setdefault(n, (fn, kw)))
		self.assertEqual(set(cmds), set(facade_cmds))
		with tempfile.TemporaryDirectory() as td:
			proj = Path(td).resolve()
			scratch = proj / '\ua616/data/scratch'
			scratch.mkdir(parents=True)
			resp_f, spec_f, rep_f = (scratch / 'resp.md', scratch / 'spec.md', scratch / 'rep.json')
			resp_f.write_text('Plain response.\n', encoding='utf-8')
			spec_f.write_text('- **Pattern:** Strategy\n- **Category:** Behavioral\n- **Intent:** Swap.\n- **Participants:** `Engine`\n- **Collaboration:** Calls.\n- **Consequences:** Clean.\n', encoding='utf-8')
			prep = cmds['arch-prepare'][0](SimpleNamespace(project=proj, parent=_PARENT_ID, kind='response', response_file=resp_f, spec_file=spec_f, repo=None, file=[], issue=None, consume_input=True))
			self.assertTrue(prep['valid'])
			inp = cmds['arch-review-input'][0](SimpleNamespace(project=proj, package=prep['package'], parent=_PARENT_ID, reviewer=_REVIEWER_ID))
			self.assertEqual(1, inp['arch_review_input'])
			raw = json.dumps(_sample_verdict(prep['package'], prep['package_sha256'])).encode('utf-8')
			rep_f.write_bytes(raw)
			with patch.object(ReviewStore, 'authenticate_report', return_value={'final_response_sha256': hashlib.sha256(raw).hexdigest(), 'proof': 'p.json'}):
				rec = cmds['arch-record-review'][0](SimpleNamespace(project=proj, report=rep_f, parent=_PARENT_ID, reviewer=_REVIEWER_ID, native_evidence=None, wait_timeout=0.0, consume_input=True))
			self.assertEqual('approved', rec['result'])
			chk = cmds['arch-check'][0](SimpleNamespace(project=proj, repo=None, response_file=None, issue=None, format='text'))
			self.assertTrue(chk['valid'])
			text_fn = cmds['arch-check'][1]['text_fn']
			self.assertIsNone(text_fn(chk, SimpleNamespace(format='json')))
			self.assertIn('PASS', text_fn(chk, SimpleNamespace(format='text')) or '')
			self.assertIn('- bad', text_fn({'valid': False, 'issues': ['bad']}, SimpleNamespace(format='text')) or '')
	# @used-by :mod:`unittest`
	def test_review_store_roundtrip_auth_and_patch_seam(self) -> None:
		from Df.Harness.Arch.ReviewStore import ReviewStore
		from agent_tools import metrics
		from agent_tools.arch.review_store import inspect_arch_status, prepare_arch_package, read_arch_review_input, record_arch_review
		with tempfile.TemporaryDirectory() as td:
			proj = Path(td).resolve()
			mod = proj / 'src/engine.py'
			mod.parent.mkdir(parents=True)
			mod.write_text('class StrategyEngine:\n\tdef run(self):\n\t\treturn 1\n', encoding='utf-8')
			spec = '- **Pattern:** Strategy\n- **Category:** Behavioral\n- **Intent:** Swap rules.\n- **Participants:** `StrategyEngine`\n- **Collaboration:** Delegates.\n- **Consequences:** Modular.\n'
			prep = prepare_arch_package(proj, _PARENT_ID, kind='code_diff', spec_text=spec, repo=proj, files=['src/engine.py'])
			self.assertEqual(prep['package_sha256'], read_arch_review_input(proj, prep['package'], parent_id=_PARENT_ID, reviewer_id=_REVIEWER_ID)['package_sha256'])
			finding = {'id': 'F-1', 'violation_class': 'missing_pattern', 'severity': 'significant', 'target': 'src/engine.py', 'description': 'Needs detail.', 'status': 'open'}
			nc_raw = json.dumps(_sample_verdict(prep['package'], prep['package_sha256'], result='needs_changes', outcome='missing_pattern', participants_ok=False, findings=[finding])).encode('utf-8')
			ReviewStore(proj, auth_fn=lambda *a, **kw: {'final_response_sha256': hashlib.sha256(nc_raw).hexdigest(), 'proof': 'nc'}).record_review(nc_raw, parent_id=_PARENT_ID, reviewer_id=_REVIEWER_ID)
			self.assertFalse(inspect_arch_status(proj, response_text='Plain text')['valid'])
			ok_raw = json.dumps(_sample_verdict(prep['package'], prep['package_sha256'])).encode('utf-8')
			fake_proof = {'final_response_sha256': hashlib.sha256(ok_raw).hexdigest(), 'proof': 'seam-proof'}
			with patch('agent_tools.arch.review_store._authenticate_arch_report', return_value=fake_proof):
				rec = record_arch_review(proj, ok_raw, parent_id=_PARENT_ID, reviewer_id=_REVIEWER_ID)
			self.assertEqual('approved', rec['result'])
			self.assertEqual('seam-proof', rec['native_proof'])
			ev_f = proj / 'ev.json'
			ev_f.write_text(json.dumps(fake_proof), encoding='utf-8')
			with patch.object(metrics, 'verify_native_proof', return_value=fake_proof):
				self.assertEqual(fake_proof, ReviewStore.authenticate_report(proj, _PARENT_ID, _REVIEWER_ID, ok_raw, 'pkg.json', native_evidence=ev_f, wait_timeout=0.0, platform=None, instance=None))
			with patch.object(metrics, 'native_review_proof', return_value={'final_response_sha256': '0' * 64}):
				with self.assertRaises(ValueError):
					ReviewStore.authenticate_report(proj, _PARENT_ID, _REVIEWER_ID, ok_raw, 'pkg.json', native_evidence=None, wait_timeout=0.0, platform=None, instance=None)
	# @used-by :mod:`unittest`
	def test_review_validator_and_facade_alias(self) -> None:
		from Df.Harness.Arch.ReviewValidator import ReviewValidator
		from agent_tools.arch.review_validator import ArchitectureAuditValidator
		self.assertIs(ReviewValidator, ArchitectureAuditValidator)
		v = ReviewValidator()
		pkg_rel, pkg_sha = ('\ua616/data/arch-reviews/packages/p.json', 'd' * 64)
		self.assertEqual([], v.validate(_sample_verdict(pkg_rel, pkg_sha), {}, package_rel=pkg_rel, package_sha256=pkg_sha))
		self.assertTrue(bool(v.validate('not-a-dict')))
		bad = _sample_verdict(pkg_rel, pkg_sha, result='approved', outcome='pattern_washing', participants_ok=False, findings=['bad-item'])
		self.assertTrue(bool(v.validate(bad, {}, package_rel=pkg_rel, package_sha256=pkg_sha)))
		bad_nc = _sample_verdict(pkg_rel, pkg_sha, result='needs_changes', findings=[])
		self.assertTrue(bool(v.validate(bad_nc, {}, package_rel=pkg_rel, package_sha256=pkg_sha)))
	# @used-by :mod:`unittest`
	def test_s11_arch_invariants_and_zero_class_facades(self) -> None:
		arch_dir = SCRIPTS / 'Df/Harness/Arch'
		single_pub_count = 0
		for name in _ARCH_MODULES:
			src = (arch_dir / f'{name}.py').read_text(encoding='utf-8')
			tree = ast.parse(src)
			classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
			self.assertEqual([name], [c.name for c in classes], f'Expected single PascalCase class {name}')
			self.assertEqual([], _arch_backward_imports(tree), f'Forbidden backward import in {name}.py')
			pub_inst = 0
			for node in classes[0].body:
				if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
					if node.name.startswith('_') and (not node.name.startswith('__')):
						self.assertTrue(_has_decorator(node, {'override'}), f'Non-override single-underscore method {name}.{node.name}')
					elif (not node.name.startswith('_')) and (not _has_decorator(node, {'classmethod', 'staticmethod'})):
						pub_inst += 1
			if 1 >= pub_inst:
				single_pub_count += 1
		self.assertGreaterEqual(single_pub_count / len(_ARCH_MODULES), 0.85, f'Only {single_pub_count}/{len(_ARCH_MODULES)} classes have <=1 public instance method')
		facade_dir = SCRIPTS / 'agent_tools/arch'
		for pyf in sorted(facade_dir.glob('*.py')):
			tree = ast.parse(pyf.read_text(encoding='utf-8'))
			self.assertEqual([], [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)], f'Facade {pyf.name} must define zero classes')
	# @used-by :mod:`unittest`
	def test_structure_visitor_and_trigger_classifier_detect_df_cross_imports(self) -> None:
		from Df.Harness.Arch.StructureVisitor import StructureVisitor
		from Df.Harness.Arch.TriggerClassifier import TriggerClassifier
		from agent_tools.arch.triggers import REGISTRY_PATH_HINTS, classify_code_change_trigger, classify_markdown_arch_trigger, extract_code_symbols
		self.assertEqual(TriggerClassifier.REGISTRY_PATH_HINTS, REGISTRY_PATH_HINTS)
		code = 'import Df\nimport Df.Harness.Arch.Catalog\nimport agent_tools.runtime\nfrom Df.Harness.Arch.SpecValidator import SpecValidator\nfrom .local import helper\nclass MyProto(Protocol):\n\tasync def fetch(self):\n\t\treturn 1\n\tdef run(self):\n\t\treturn 2\n'
		vis = StructureVisitor()
		vis.visit(ast.parse(code))
		self.assertIn('Df', vis.cross_imports)
		self.assertIn('Df.Harness.Arch.Catalog', vis.cross_imports)
		self.assertIn('Df.Harness.Arch.SpecValidator', vis.cross_imports)
		self.assertIn('agent_tools.runtime', vis.cross_imports)
		self.assertIn('.local', vis.cross_imports)
		self.assertIn('MyProto', vis.interfaces)
		self.assertEqual({'fetch', 'run'}, vis.functions)
		tr = TriggerClassifier().classify_code_change('scripts/Df/Harness/Arch/Foo.py', None, code, changed_prod_files=['scripts/Df/Harness/Arch/Foo.py', 'scripts/Df/Harness/Arch/Bar.py'])
		self.assertTrue(tr['triggered'])
		self.assertIn('Df.Harness.Arch.Catalog', tr['added_cross_imports'])
		self.assertTrue(classify_code_change_trigger('runtime.json', '{"roles": {}}', '{"roles": {"ARCH": {}}}')['triggered'])
		self.assertFalse(TriggerClassifier().classify_code_change('tests/test_sample.py', None, code)['triggered'])
		self.assertEqual(set(), TriggerClassifier.extract_symbols('def (', rel_path='scripts/bad.py')['classes'])
		self.assertIn('JsWidget', extract_code_symbols('class JsWidget { render() {} }', rel_path='web/w.js')['classes'])
		md_tr = TriggerClassifier.classify_markdown('## Architecture\nCreate `scripts/Df/Harness/Arch/X.py` with `class X` in `PreToolUse` registry.\n', is_parent_issue=True)
		self.assertTrue(md_tr['triggered'] and md_tr['significant'])
		self.assertTrue(classify_markdown_arch_trigger('"architecture_change": true')['triggered'])
if '__main__' == __name__:
	unittest.main()
