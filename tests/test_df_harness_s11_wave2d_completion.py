# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import argparse
import importlib
import inspect
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :mod:`unittest`
class DfHarnessS11Wave2DCompletionTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_admission_one_way_facade_behavior(self) -> None:
		from Df.Harness.Completion.PublicationAdmission import PublicationAdmission
		from agent_tools import admission
		owned_classes = [cls.__name__ for _, cls in inspect.getmembers(admission, inspect.isclass) if cls.__module__ == admission.__name__]
		self.assertEqual([], owned_classes)
		self.assertIs(admission.PublicationAdmission, PublicationAdmission)
		with tempfile.TemporaryDirectory() as td:
			jdir = Path(td).resolve()
			b = admission.binding(jdir, ['req'], 'resp', 'turn-1', ['r1'])
			self.assertEqual(str(jdir), b['journal'])
			self.assertEqual('turn-1', b['turn'])
			with self.assertRaises(ValueError):
				admission.require_current(object(), b)
			with self.assertRaises(ValueError):
				admission.verify({}, b)
	# @used-by :mod:`unittest`
	def test_completion_commands_parser_and_dispatch(self) -> None:
		from Df.Harness.lib.completion_commands import dfh_add_completion_parser_arguments, dfh_begin, dfh_check_answer, dfh_execute_completion, dfh_prepare, dfh_prepare_once, dfh_reconcile_unprepared_delivery, dfh_sync
		from agent_tools import completion
		for cmd in ('turn-begin', 'answer-check', 'answer-prepare', 'recover-checkpoint', 'recover-turn-violation', 'similar-project-exempt', 'ratchet-ok', 'tdd-check', 'issue-first-check', 'journal-sync', 'reconcile-unprepared-delivery', 'sync-conversation-title'):
			parser = argparse.ArgumentParser(prog=cmd)
			dfh_add_completion_parser_arguments(parser, cmd)
			self.assertTrue(any(('--conversation' in a.option_strings for a in parser._actions)), cmd)
		self.assertIs(completion.add_parser_arguments, dfh_add_completion_parser_arguments)
		for fn in (dfh_begin, dfh_check_answer, dfh_execute_completion, dfh_prepare, dfh_prepare_once, dfh_reconcile_unprepared_delivery, dfh_sync):
			self.assertTrue(callable(fn))
		with self.assertRaises(ValueError):
			dfh_execute_completion(argparse.Namespace(command='unknown-op'))
		with self.assertRaises(ValueError):
			dfh_check_answer(WT_ROOT, '   ')
		with self.assertRaises(ValueError):
			dfh_prepare_once(WT_ROOT, '   ')
	# @used-by :mod:`unittest`
	def test_completion_recovery_validation_and_empty_handoff(self) -> None:
		from Df.Harness.lib.completion_recovery import dfh_handoff_launcher_turn, dfh_issue_first_check_turn, dfh_ratchet_ok, dfh_recover_checkpoint, dfh_recover_turn_violation, dfh_similar_project_exempt, dfh_sync_conversation_title, dfh_tdd_check_turn
		for fn in (dfh_issue_first_check_turn, dfh_recover_checkpoint, dfh_recover_turn_violation, dfh_sync_conversation_title, dfh_tdd_check_turn):
			self.assertTrue(callable(fn))
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			self.assertEqual([], dfh_handoff_launcher_turn(None, root, '~123'))
			self.assertEqual([], dfh_handoff_launcher_turn(root, root, '~123'))
			with self.assertRaises(ValueError):
				dfh_similar_project_exempt(root, 'peer', 'short')
			with self.assertRaises(ValueError):
				dfh_similar_project_exempt(root, '', 'x' * 35)
			with self.assertRaises(ValueError):
				dfh_ratchet_ok(root, '', 'x' * 35)
	# @used-by :mod:`unittest`
	def test_dfh_turns_dir_works_without_legacy_path_registry_import(self) -> None:
		from Df.Harness.lib.journal import dfh_turns_dir
		saved = sys.modules.pop('agent_tools.path_registry', None)
		try:
			with tempfile.TemporaryDirectory() as td:
				root = Path(td).resolve()
				self.assertEqual(root / '\ua616/data/turns', dfh_turns_dir(root))
				self.assertNotIn('agent_tools.path_registry', sys.modules)
		finally:
			if None is not saved:
				sys.modules['agent_tools.path_registry'] = saved
	# @used-by :mod:`unittest`
	def test_f5_exact_seam_allowlist_across_wave2d_classes(self) -> None:
		namespaces = ('Cleanup', 'Cli', 'Completion', 'Config', 'Hook', 'Journal', 'Path', 'Platform', 'Runtime', 'Shadow')
		observed_seams: set[tuple[str, str]] = set()
		for ns in namespaces:
			for pyf in sorted((SCRIPTS / 'Df/Harness' / ns).rglob('*.py')):
				mod_name = pyf.relative_to(SCRIPTS).with_suffix('').as_posix().replace('/', '.')
				mod = importlib.import_module(mod_name)
				cls = getattr(mod, pyf.stem)
				for name, member in cls.__dict__.items():
					if callable(member) and name.startswith('_') and (not name.startswith(('__', f'_{cls.__name__}__'))):
						observed_seams.add((cls.__name__, name))
		self.assertEqual({('AnswerPreparer', '_fail_gate'), ('AnswerPreparer', '_record_journal_entry')}, observed_seams)
	# @used-by :mod:`unittest`
	def test_link_audit_tracks_completion_links_call_site(self) -> None:
		from Df.Harness.Project.LinkAudit import LinkAudit
		self.assertEqual([], LinkAudit(SCRIPTS).audit())
if '__main__' == __name__:
	unittest.main()
