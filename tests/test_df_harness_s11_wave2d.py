# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import importlib
import inspect
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
		from Df.Harness.Cleanup.StoreResolver import StoreResolver
		from agent_tools import cleanup
		self.assertIs(cleanup.ProjectCleanupScanner, Scanner)
		self.assertTrue(callable(StoreResolver))
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			proj = root / 'p1'
			proj.mkdir()
			meta = AuditLogger(timestamp='2026-11-26T00:00:00Z', project_root=proj).run()
			self.assertIn('Time', meta)
			base_dt = datetime(2026, 11, 26, tzinfo=timezone.utc)
			act = LifecycleEvaluator(proj, {}, {}, base_dt, 'fallback', lambda p: str(p)).run()
			self.assertEqual((base_dt, 'fallback'), act)
	# @used-by :mod:`unittest`
	def test_cli_subsystem_classes(self) -> None:
		from Df.Harness.Cli.Dispatcher import Dispatcher
		from Df.Harness.Cli.DomainExecutor import DomainExecutor
		from Df.Harness.Cli.GitShim import GitShim
		from Df.Harness.Cli.RegistryExecutor import RegistryExecutor
		from Df.Harness.lib.cli_input import dfh_read_input_json
		from Df.Harness.lib.rule_splitter import dfh_slugify
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			sample = root / 'in.json'
			sample.write_text('{"k": 1}', encoding='utf-8')
			self.assertEqual({'k': 1}, dfh_read_input_json(sample))
			self.assertEqual('hello-world', dfh_slugify('Hello World!'))
			cmd, env = GitShim(['status']).run()
			self.assertIsInstance(cmd, list)
			self.assertIn('--no-optional-locks', cmd)
			self.assertEqual('0', env['GIT_OPTIONAL_LOCKS'])
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
			self.assertIsInstance(BlockedReportAuditor(root, 'Clean answer.', workflow_exists=False).run(), list)
			self.assertEqual([], NarrowReconciler(root, {}, {'requests': []}, {'requests': []}, recovered=False, same_req_fn=lambda a, b, r: a == b, journal_dir_fn=lambda r, j: r).run())
			self.assertIsNone(TurnRouter(root, 'cid', 0).run())
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
		from Df.Harness.Config.ProjectionPublisher import ProjectionPublisher
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
			self.assertTrue(callable(ProjectionPublisher))
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
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			self.assertEqual({'decision': 'allow'}, MarkdownSlopGate({'toolCall': {'name': 'read_file', 'args': {}}}).run())
			self.assertTrue(CrashAuditor(root, {'source_file': ''}, {'start_step': 0}, {}, '').run()['verified'])
			self.assertTrue(AddonObserver(root, None, None, None, '').run()['verified'])
			self.assertTrue(VerificationObserver(root, None, None, None, '').run()['verified'])
		for cls in (ContinuationGuard, EmergencyCapturer, JsonRunner, PreInvocationGate, RulesServerGate, StopGate, SubagentChecker, TraceEventCache):
			self.assertTrue(callable(cls))
	# @used-by :mod:`unittest`
	def test_journal_subsystem_classes(self) -> None:
		from Df.Harness.Journal.IntegrityAuditor import IntegrityAuditor
		from Df.Harness.Journal.LivenessProbe import LivenessProbe
		from Df.Harness.Journal.OpenTurnSyncer import OpenTurnSyncer
		from Df.Harness.Journal.PendingIndex import PendingIndex
		from Df.Harness.Journal.Publisher import Publisher
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			turns = root / '\ua616/data/turns'
			turns.mkdir(parents=True)
			self.assertEqual(({}, False), PendingIndex(turns, read_fn=lambda p: json.loads(p.read_text(encoding='utf-8'))).run())
			self.assertEqual({'active_parallel': [], 'orphaned': []}, IntegrityAuditor(root).run())
			self.assertTrue(callable(LivenessProbe))
			self.assertTrue(callable(OpenTurnSyncer))
			self.assertTrue(callable(Publisher))
	# @used-by :mod:`unittest`
	def test_path_subsystem_classes(self) -> None:
		from Df.Harness.Path.CacheStore import CacheStore
		from Df.Harness.Path.PathReporter import PathReporter
		from Df.Harness.Path.ProjectPaths import ProjectPaths
		from Df.Harness.Path.Registry import Registry
		from Df.Harness.Path.SimilarProjectAuditor import SimilarProjectAuditor
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
		self.assertTrue(callable(PathReporter))
		self.assertTrue(callable(SimilarProjectAuditor))
	# @used-by :mod:`unittest`
	def test_platform_subsystem_classes(self) -> None:
		from Df.Harness.Platform.Antigravity.ExecutorMetadataReader import ExecutorMetadataReader as AgMeta
		from Df.Harness.Platform.Antigravity.ProjectRegistrar import ProjectRegistrar as AgReg
		from Df.Harness.Platform.Antigravity.ProofVerifier import ProofVerifier as AgVerifier
		from Df.Harness.Platform.Antigravity.RetryableProofError import RetryableProofError
		from Df.Harness.Platform.Antigravity.ReviewProver import ReviewProver as AgProver
		from Df.Harness.Platform.Antigravity.TitleSyncer import TitleSyncer
		from Df.Harness.Platform.Antigravity.ToolTraceReader import ToolTraceReader as AgTrace
		from Df.Harness.Platform.Antigravity.TurnScanner import TurnScanner as AgScanner
		from Df.Harness.Platform.ClarificationExtractor import ClarificationExtractor
		from Df.Harness.Platform.Codex.ExecutorMetadataReader import ExecutorMetadataReader as CxMeta
		from Df.Harness.Platform.Codex.ProjectRegistrar import ProjectRegistrar as CxReg
		from Df.Harness.Platform.Codex.ProofVerifier import ProofVerifier as CxVerifier
		from Df.Harness.Platform.Codex.ReviewProver import ReviewProver as CxProver
		from Df.Harness.Platform.Codex.TokenSummarizer import TokenSummarizer
		from Df.Harness.Platform.Codex.ToolTraceReader import ToolTraceReader as CxTrace
		from Df.Harness.Platform.Codex.TurnScanner import TurnScanner as CxScanner
		from Df.Harness.Platform.TraceAnalyzer import TraceAnalyzer
		from Df.Harness.lib.proof_metadata import dfh_proof_semantically_equivalent
		from Df.Harness.lib.request_binding import dfh_extract_leading_upwork_init_ids
		from agent_tools.platforms import antigravity, antigravity_review_helpers, codex
		self.assertIs(antigravity.AntigravityTurnScanner, AgScanner)
		self.assertIs(antigravity_review_helpers.RetryableReviewProofError, RetryableProofError)
		self.assertIs(codex.CodexTurnScanner, CxScanner)
		self.assertEqual('retry', str(RetryableProofError('retry')))
		self.assertEqual([], ClarificationExtractor([]).run())
		self.assertTrue(dfh_proof_semantically_equivalent({}, {}))
		self.assertEqual([], dfh_extract_leading_upwork_init_ids('plain text'))
		self.assertEqual([], TraceAnalyzer([]).run())
		for cls in (AgMeta, AgProver, AgReg, AgTrace, AgVerifier, CxMeta, CxProver, CxReg, CxTrace, CxVerifier, TitleSyncer, TokenSummarizer):
			self.assertTrue(callable(cls))
	# @used-by :mod:`unittest`
	def test_runtime_and_shadow_subsystem_classes(self) -> None:
		from Df.Harness.Runtime.CanaryProbe import CanaryProbe
		from Df.Harness.Runtime.LauncherRenderer import LauncherRenderer
		from Df.Harness.Runtime.SettingsLoader import SettingsLoader
		from Df.Harness.Runtime.SnapshotPromoter import SnapshotPromoter
		from Df.Harness.Shadow.CommandExecutor import CommandExecutor
		from Df.Harness.Shadow.ReplayPipeline import ReplayPipeline
		from Df.Harness.Shadow.ReplayRunner import ReplayRunner
		from Df.Harness.Shadow.WorkspaceCloner import WorkspaceCloner
		cfg = SettingsLoader(WT_ROOT / 'runtime.json').run()
		self.assertIn('platforms', cfg)
		src = LauncherRenderer(WT_ROOT).run()
		self.assertIn('def main', src)
		for cls in (CanaryProbe, CommandExecutor, ReplayPipeline, ReplayRunner, SnapshotPromoter, WorkspaceCloner):
			self.assertTrue(callable(cls))
	# @used-by :mod:`unittest`
	def test_s11_architectural_invariants_across_wave2d(self) -> None:
		namespaces = ('Cleanup', 'Cli', 'Completion', 'Config', 'Hook', 'Journal', 'Path', 'Platform', 'Runtime', 'Shadow')
		total, single_pub = (0, 0)
		observed_seams: set[tuple[str, str]] = set()
		for ns in namespaces:
			for pyf in sorted((SCRIPTS / 'Df/Harness' / ns).rglob('*.py')):
				mod_name = pyf.relative_to(SCRIPTS).with_suffix('').as_posix().replace('/', '.')
				mod = importlib.import_module(mod_name)
				owned = [cls for _, cls in inspect.getmembers(mod, inspect.isclass) if cls.__module__ == mod.__name__]
				self.assertEqual(1, len(owned), pyf.as_posix())
				cls = owned[0]
				self.assertEqual(pyf.stem, cls.__name__, pyf.as_posix())
				total += 1
				pub = [name for name, member in cls.__dict__.items() if callable(member) and (not name.startswith('_'))]
				if 1 >= len(pub):
					single_pub += 1
				for name, member in cls.__dict__.items():
					if callable(member) and name.startswith('_') and (not name.startswith(('__', f'_{cls.__name__}__'))):
						observed_seams.add((cls.__name__, name))
		self.assertEqual({('AnswerPreparer', '_fail_gate'), ('AnswerPreparer', '_record_journal_entry')}, observed_seams)
		self.assertGreaterEqual(single_pub / max(1, total), 0.85, f'{single_pub}/{total}')
if '__main__' == __name__:
	unittest.main()
