# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`unittest`
class DfHarnessS11Wave2bTddTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_tdd_classifier_commands_and_lexers(self) -> None:
		from Df.Harness.Tdd.CLikeCommentLexer import CLikeCommentLexer
		from Df.Harness.Tdd.CodeClassifier import CodeClassifier
		from Df.Harness.Tdd.CommandInspector import CommandInspector
		from Df.Harness.Tdd.CommentDiff import CommentDiff
		from Df.Harness.Tdd.ExtCommentLexer import ExtCommentLexer
		from Df.Harness.Tdd.MarkupCommentLexer import MarkupCommentLexer
		from Df.Harness.Tdd.ScriptCommentLexer import ScriptCommentLexer
		cls_res = CodeClassifier('scripts/app.py').classify()
		self.assertEqual('production', cls_res)
		cmd_res = CommandInspector('pytest -x tests/test_a.py').classify_test_command()
		self.assertTrue(cmd_res['is_test_cmd'])
		cd_res = CommentDiff('a.py', 'x = 1\n', '# c\nx = 1\n').classify()
		self.assertEqual('comment_only', cd_res)
		c_lex = CLikeCommentLexer('int x = 1; // c\n', {'line_slash': True}).lex()
		self.assertIsNotNone(c_lex)
		self.assertIsNotNone(CLikeCommentLexer.lex_php('<?php // c\n$x = 1; ?>'))
		self.assertIsNotNone(CLikeCommentLexer.lex_python('# c\nx = 1\n'))
		self.assertIsNotNone(ExtCommentLexer.lex_rust('// c\nfn main() {}'))
		self.assertIsNotNone(ExtCommentLexer.lex_lua('-- c\nlocal x = 1'))
		self.assertIsNotNone(ExtCommentLexer.lex_cmake('# c\nset(A 1)'))
		self.assertIsNotNone(ExtCommentLexer.lex_fsharp('// c\nlet x = 1'))
		self.assertIsNotNone(ExtCommentLexer.lex_hcl('# c\nx = 1'))
		self.assertIsNotNone(ExtCommentLexer.lex_sass('// c\n.a\n  color: red'))
		self.assertIsNotNone(ExtCommentLexer.lex_zig('// c\nconst x = 1;'))
		self.assertIsNotNone(MarkupCommentLexer.lex_dockerfile('# c\nFROM alpine'))
		self.assertIsNotNone(MarkupCommentLexer.lex_indent_hash('# c\nall:\n\techo hi'))
		self.assertIsNotNone(MarkupCommentLexer.lex_sed('# c\ns/a/b/'))
		self.assertIsNotNone(MarkupCommentLexer.lex_sfc('<!-- c --><script>// c\nconst x = 1;</script>'))
		self.assertIsNotNone(MarkupCommentLexer.lex_tcl('# c\nset x 1'))
		self.assertIsNotNone(ScriptCommentLexer.lex_batch('REM c\necho hi'))
		self.assertIsNotNone(ScriptCommentLexer.lex_hash_script('# c\necho hi', {'sh_hash': True}))
		self.assertIsNotNone(ScriptCommentLexer.lex_sql('-- c\nSELECT 1;'))
		self.assertIsNotNone(ScriptCommentLexer.lex_vbscript("' c\nDim x"))
	# @used-by :mod:`unittest`
	def test_tdd_diff_executability_and_coverage(self) -> None:
		from Df.Harness.Tdd.DiffContract import DiffContract
		from Df.Harness.Tdd.DiffCoverage import DiffCoverage
		from Df.Harness.Tdd.DiffCoverageHook import DiffCoverageHook
		from Df.Harness.Tdd.DiffExecutability import DiffExecutability
		from Df.Harness.Tdd.Exemption import Exemption
		from Df.Harness.Tdd.MechanicalExemption import MechanicalExemption
		de_res = DiffExecutability().classify('scripts/demo.py', 'x = 1\n', '# c\nx = 1\n')
		self.assertFalse(de_res['executable'])
		warn_res = DiffContract.detect_mixed_commit_warning({'category_counts': {'comment_only': 25, 'executable': 1}, 'executable_files': ['a.py']})
		self.assertIsNotNone(warn_res)
		backend = DiffCoverageHook.resolve_trace_backend('auto')
		self.assertIn(backend, ('sys.monitoring', 'sys.settrace'))
		with tempfile.TemporaryDirectory() as td:
			env, cdir = DiffCoverageHook(Path(td), {}, Path(td)).prepare_env()
			self.assertTrue(cdir.is_dir())
			self.assertIn('HARNESS_DIFF_COV_DIR', env)
			ev_cov = DiffCoverage.evaluate_collected(Path(td), {}, cdir)
			self.assertTrue(ev_cov['valid'])
		parsed_fns = DiffCoverage.parse_module_functions('class C:\n\t@staticmethod\n\tdef f():\n\t\treturn 1\n')
		self.assertEqual(2, parsed_fns['C.f']['start_line'])
		ex_ok = Exemption.is_diff_exempt('a.py', 'x = 1\n', '# c\nx = 1\n')
		self.assertTrue(ex_ok)
		mech_ok = MechanicalExemption.matches_recipe('old = 1\n', 'new = 1\n', {'pattern': 'old', 'replacement': 'new'})
		self.assertTrue(mech_ok)
	# @used-by :mod:`unittest`
	def test_tdd_enforcement_evaluator_events_and_guards(self) -> None:
		from Df.Harness.Tdd.Enforcement import Enforcement
		from Df.Harness.Tdd.Evaluator import Evaluator
		from Df.Harness.Tdd.EventsExtractor import EventsExtractor
		from Df.Harness.Tdd.OutcomeParser import OutcomeParser
		from Df.Harness.Tdd.RatchetGuard import RatchetGuard
		from Df.Harness.Tdd.ServiceExempt import ServiceExempt
		from Df.Harness.Tdd.SubstantiveTestChecker import SubstantiveTestChecker
		from Df.Harness.Tdd.WorktreeScope import WorktreeScope
		enf_res = Enforcement().evaluate_pre_tool_use('read_file', {}, {})
		self.assertIsNone(enf_res)
		ev_res = Evaluator([]).evaluate()
		self.assertTrue(ev_res['verified'])
		cmd_ev = EventsExtractor.build_command_event(1, 'pytest -x', 'Command exited with code 0\n1 passed')
		self.assertTrue(cmd_ev['outcome']['is_pass'])
		out_res = OutcomeParser('Command exited with code 0\n1 passed').parse()
		self.assertTrue(out_res['is_pass'])
		rat_res = RatchetGuard('tests/test_a.py', 'def test_a():\n\tassert True\n', 'def test_a():\n\tpass\n').check()
		self.assertTrue(rat_res)
		svc_res = ServiceExempt().is_exempt('write_file', {'Path': 'C:/p/\ua616/data/continuation.md'})
		self.assertTrue(svc_res)
		sub_ok, _ = SubstantiveTestChecker('tests/test_a.py', 'def test_a():\n\tassert 1 == 1\n').check_content()
		self.assertTrue(sub_ok)
		ws_key = WorktreeScope.resolve_key('C:/p/\ua616/data/worktrees/w1/a.py', 'C:/p')
		self.assertIn('::wt:w1', ws_key)
if '__main__' == __name__:
	unittest.main()
