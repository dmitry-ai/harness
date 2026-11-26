# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import ast
import json
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :mod:`unittest`
class DfHarnessS11Wave2DTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_cleanup_subsystem_classes(self) -> None:
		from Df.Harness.Cleanup.AuditLogger import AuditLogger
		from Df.Harness.Cleanup.LifecycleEvaluator import LifecycleEvaluator
		from Df.Harness.Cleanup.Scanner import Scanner
		from agent_tools import cleanup
		self.assertIs(cleanup.ProjectCleanupScanner, Scanner)
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			proj = root / 'p1'
			proj.mkdir()
			meta = AuditLogger(root, 'antigravity', {}, [], []).run()
			self.assertIn('cleanup_at', meta)
			act = LifecycleEvaluator(proj, {}, {}).run()
			self.assertIsInstance(act, dict)
	# @used-by :mod:`unittest`
	def test_cli_subsystem_classes(self) -> None:
		from Df.Harness.Cli.Dispatcher import Dispatcher
		from Df.Harness.Cli.DomainExecutor import DomainExecutor
		from Df.Harness.Cli.GitShim import GitShim
		from Df.Harness.Cli.InputLoader import InputLoader
		from Df.Harness.Cli.RegistryExecutor import RegistryExecutor
		from Df.Harness.Cli.RuleSplitter import RuleSplitter
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			sample = root / 'in.json'
			sample.write_text('{"k": 1}', encoding='utf-8')
			self.assertEqual({'k': 1}, InputLoader(sample).run())
			self.assertEqual('hello-world', RuleSplitter('Hello World!').run())
			cmd = GitShim(['status']).run()
			self.assertIsInstance(cmd, list)
			self.assertTrue(callable(Dispatcher))
			self.assertTrue(callable(DomainExecutor))
			self.assertTrue(callable(RegistryExecutor))
	# @used-by :mod:`unittest`
	def test_completion_subsystem_classes(self) -> None:
		from Df.Harness.Completion.AdmissionGuard import AdmissionGuard
		from Df.Harness.Completion.AnswerPreparer import AnswerPreparer
		from Df.Harness.Completion.BlockedReportAuditor import BlockedReportAuditor
		from Df.Harness.Completion.BudgetEvaluator import BudgetEvaluator
		from Df.Harness.Completion.EnvIsolationAuditor import EnvIsolationAuditor
		from Df.Harness.Completion.JournalReconciler import JournalReconciler
		from Df.Harness.Completion.NarrowReconciler import NarrowReconciler
		from Df.Harness.Completion.PublicationAdmission import PublicationAdmission
		from Df.Harness.Completion.TurnRouter import TurnRouter
		from agent_tools import admission, completion
		self.assertIs(completion.AnswerPreparationRunner, AnswerPreparer)
		self.assertIs(completion.TurnJournalReconciler, JournalReconciler)
		self.assertIs(admission.PublicationAdmission, PublicationAdmission)
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			self.assertIsInstance(BudgetEvaluator(root, {}).run(), dict)
			self.assertEqual([], BlockedReportAuditor(root, 'Clean answer.').run())
			self.assertEqual([], NarrowReconciler([], [], {}).run())
			self.assertIsNone(TurnRouter(root, 'cid', []).run())
			self.assertTrue(callable(AdmissionGuard))
			self.assertTrue(callable(EnvIsolationAuditor))
	# @used-by :mod:`unittest`
	def test_config_and_native_profile_classes(self) -> None:
		from Df.Harness.Config.AtomicWriter import AtomicWriter
		from Df.Harness.Config.NativeBuilder import NativeBuilder
		from Df.Harness.Config.NativeProfile.Applier import Applier
		from Df.Harness.Config.NativeProfile.ApplyFailure import ApplyFailure
		from Df.Harness.Config.NativeProfile.ManagedLink import ManagedLink
		from Df.Harness.Config.NativeProfile.Plan import Plan
		from agent_tools import native_profiles
		self.assertIs(native_profiles._ApplyFailure, ApplyFailure)
		self.assertIs(native_profiles._ManagedLink, ManagedLink)
		self.assertIs(native_profiles._Plan, Plan)
		err = ApplyFailure('boom', {'status': 'complete', 'issues': []}, [])
		self.assertIn('boom', str(err))
		plan = Plan()
		plan.issue(Path('a.json'), 'bad')
		self.assertEqual(1, len(plan.readonly_issues()))
		with tempfile.TemporaryDirectory() as td:
			target = Path(td).resolve() / 'out.bin'
			AtomicWriter(target, b'abc').run()
			self.assertEqual(b'abc', target.read_bytes())
			self.assertTrue(callable(Applier))
			self.assertTrue(callable(NativeBuilder))
	# @used-by :mod:`unittest`
	def test_hook_subsystem_classes(self) -> None:
		from Df.Harness.Hook.AddonObserver import AddonObserver
		from Df.Harness.Hook.ContinuationGuard import ContinuationGuard
		from Df.Harness.Hook.CrashAuditor import CrashAuditor
		from Df.Harness.Hook.EmergencyCapturer import EmergencyCapturer
		from Df.Harness.Hook.JsonRunner import JsonRunner
		from Df.Harness.Hook.MarkdownSlopGate import MarkdownSlopGate
		from Df.Harness.Hook.PreInvocationGate import PreInvocationGate
		from Df.Harness.Hook.RulesServerGate import RulesServerGate
		from Df.Harness.Hook.StopGate import StopGate
		from Df.Harness.Hook.SubagentChecker import SubagentChecker
		from Df.Harness.Hook.TraceEventCache import TraceEventCache
		from Df.Harness.Hook.VerificationObserver import VerificationObserver
		self.assertEqual({'decision': 'allow'}, MarkdownSlopGate({'toolCall': {'name': 'read_file', 'args': {}}}).run())
		self.assertEqual([], CrashAuditor({'source_file': ''}, {'start_step': 0}).run())
		self.assertIsInstance(AddonObserver([]).run(), dict)
		self.assertEqual([], VerificationObserver([], {}).run())
		self.assertTrue(callable(ContinuationGuard))
		self.assertTrue(callable(EmergencyCapturer))
		self.assertTrue(callable(JsonRunner))
		self.assertTrue(callable(PreInvocationGate))
		self.assertTrue(callable(RulesServerGate))
		self.assertTrue(callable(StopGate))
		self.assertTrue(callable(SubagentChecker))
		self.assertTrue(callable(TraceEventCache))
	# @used-by :mod:`unittest`
	def test_journal_subsystem_classes(self) -> None:
		from Df.Harness.Journal.IntegrityAuditor import IntegrityAuditor
		from Df.Harness.Journal.OpenTurnSyncer import OpenTurnSyncer
		from Df.Harness.Journal.PendingIndex import PendingIndex
		from Df.Harness.Journal.Publisher import Publisher
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			turns = root / '\ua616/data/turns'
			turns.mkdir(parents=True)
			self.assertEqual([], PendingIndex(turns).run())
			self.assertIsInstance(IntegrityAuditor(root).run(), list)
			self.assertTrue(callable(OpenTurnSyncer))
			self.assertTrue(callable(Publisher))
	# @used-by :mod:`unittest`
	def test_path_subsystem_classes(self) -> None:
		from Df.Harness.Path.CacheStore import CacheStore
		from Df.Harness.Path.ProjectPaths import ProjectPaths
		from Df.Harness.Path.Registry import Registry
		from agent_tools import path_registry
		self.assertIs(path_registry.PathRegistry, Registry)
		self.assertIs(path_registry.ProjectPaths, ProjectPaths)
		raw = json.loads((WT_ROOT / 'paths.json').read_text(encoding='utf-8'))
		reg = Registry(WT_ROOT / 'paths.json', raw)
		self.assertIn('HARNESS_CODE', reg.resolved_variables)
		self.assertEqual('a/b', reg.expand('a/b'))
		pp = ProjectPaths(WT_ROOT.parents[2] if (WT_ROOT.parents[2] / '.agents').exists() else WT_ROOT, registry=reg, _register_links=False)
		self.assertEqual(pp.root, pp.data_dir.parents[1] if 2 <= len(pp.data_dir.parents) else pp.root)
		self.assertIsInstance(CacheStore(WT_ROOT).run(), Path)
	# @used-by :mod:`unittest`
	def test_platform_subsystem_classes(self) -> None:
		from Df.Harness.Platform.Antigravity.RetryableProofError import RetryableProofError
		from Df.Harness.Platform.Antigravity.TurnScanner import TurnScanner as AgScanner
		from Df.Harness.Platform.ClarificationExtractor import ClarificationExtractor
		from Df.Harness.Platform.Codex.TurnScanner import TurnScanner as CxScanner
		from Df.Harness.Platform.ProofEquivalence import ProofEquivalence
		from Df.Harness.Platform.RequestBinder import RequestBinder
		from Df.Harness.Platform.TraceAnalyzer import TraceAnalyzer
		from agent_tools.platforms import antigravity, antigravity_review_helpers, codex
		self.assertIs(antigravity.AntigravityTurnScanner, AgScanner)
		self.assertIs(antigravity_review_helpers.RetryableReviewProofError, RetryableProofError)
		self.assertIs(codex.CodexTurnScanner, CxScanner)
		self.assertEqual('retry', str(RetryableProofError('retry')))
		self.assertEqual([], ClarificationExtractor([]).run())
		self.assertTrue(ProofEquivalence({}, {}).run())
		self.assertIsNone(RequestBinder('plain text').run())
		self.assertEqual([], TraceAnalyzer([]).run())
	# @used-by :mod:`unittest`
	def test_runtime_and_shadow_subsystem_classes(self) -> None:
		from Df.Harness.Runtime.CanaryProbe import CanaryProbe
		from Df.Harness.Runtime.LauncherRenderer import LauncherRenderer
		from Df.Harness.Runtime.SettingsLoader import SettingsLoader
		from Df.Harness.Runtime.SnapshotPromoter import SnapshotPromoter
		from Df.Harness.Shadow.CommandExecutor import CommandExecutor
		from Df.Harness.Shadow.ReplayRunner import ReplayRunner
		from Df.Harness.Shadow.WorkspaceCloner import WorkspaceCloner
		cfg = SettingsLoader(WT_ROOT / 'runtime.json').run()
		self.assertIn('platforms', cfg)
		src = LauncherRenderer(WT_ROOT).run()
		self.assertIn('def main', src)
		self.assertTrue(callable(CanaryProbe))
		self.assertTrue(callable(SnapshotPromoter))
		self.assertTrue(callable(CommandExecutor))
		self.assertTrue(callable(ReplayRunner))
		self.assertTrue(callable(WorkspaceCloner))
	# @used-by :mod:`unittest`
	def test_s11_architectural_invariants_across_wave2d(self) -> None:
		namespaces = ('Cleanup', 'Cli', 'Completion', 'Config', 'Hook', 'Journal', 'Path', 'Platform', 'Runtime', 'Shadow')
		total, single_pub = (0, 0)
		for ns in namespaces:
			for pyf in sorted((SCRIPTS / 'Df/Harness' / ns).rglob('*.py')):
				tree = ast.parse(pyf.read_text(encoding='utf-8'))
				classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
				self.assertEqual(1, len(classes), pyf.as_posix())
				cls = classes[0]
				self.assertEqual(pyf.stem, cls.name, pyf.as_posix())
				total += 1
				pub = [m.name for m in cls.body if isinstance(m, ast.FunctionDef) and (not m.name.startswith('_'))]
				if 1 >= len(pub):
					single_pub += 1
				bad_priv = [m.name for m in cls.body if isinstance(m, ast.FunctionDef) and m.name.startswith('_') and (not m.name.startswith('__'))]
				self.assertEqual([], bad_priv, f'{pyf.as_posix()}: {bad_priv}')
		self.assertGreaterEqual(single_pub / max(1, total), 0.85, f'{single_pub}/{total}')
if '__main__' == __name__:
	unittest.main()
