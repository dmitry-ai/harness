# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
# @used-by :mod:`unittest`
class DfHarnessDedupS8Tests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_normalize_and_trim_delegation_to_df(self) -> None:
		from Df.Core.lib.text.n.normalize import df_normalize
		from Df.Core.lib.text.trim import df_trim_text_left, df_trim_text_left_right
		from agent_tools import markdown_links, worktree_flow
		from agent_tools.issues import linter
		from agent_tools.xref import java_tags, js_tags
		with patch.object(linter, 'df_normalize', wraps=df_normalize) as m_norm:
			self.assertEqual('a\nb\nc', linter.IssueMarkdownLinter.normalize_newlines('a\r\nb\rc'))
			self.assertGreaterEqual(m_norm.call_count, 1)
		with patch.object(worktree_flow, 'df_trim_text_left', wraps=df_trim_text_left) as m_wt:
			cur: dict = {}
			worktree_flow._apply_porcelain_line(cur, 'branch refs/heads/task/demo')
			self.assertEqual('task/demo', cur['branch'])
			self.assertGreaterEqual(m_wt.call_count, 1)
		with patch.object(markdown_links, 'df_trim_text_left', wraps=df_trim_text_left) as m_ml:
			self.assertEqual('example.com/a', markdown_links.display_address('https://www.example.com/a'))
			self.assertGreaterEqual(m_ml.call_count, 1)
		with patch.object(java_tags, 'df_trim_text_left_right', wraps=df_trim_text_left_right) as m_jt:
			self.assertIn('Doc line', java_tags._parse_javadoc_lines(['/** Doc line */'], 0, 0, 'Demo.java')['desc_lines'])
			self.assertGreaterEqual(m_jt.call_count, 1)
		with patch.object(js_tags, 'df_trim_text_left_right', wraps=df_trim_text_left_right) as m_jst:
			self.assertIn('Js line', js_tags._parse_jsdoc_lines(['/** Js line */'], 0, 0, 'demo.js')['desc_lines'])
			self.assertGreaterEqual(m_jst.call_count, 1)
	# @used-by :mod:`unittest`
	def test_clean_null_and_unique_fast_delegation_to_df(self) -> None:
		from Df.Core.lib.array.clean.main import df_clean_null
		from Df.Core.lib.array.other.unique_fast import dfa_unique_fast
		from agent_tools import diagnostics, shell_audit
		from agent_tools.meta import blocks
		from agent_tools.tdd import commands
		with patch.object(diagnostics, 'df_clean_null', wraps=df_clean_null) as m_diag:
			prob = diagnostics.problem('code.x', 'field.y', 'msg', hint=None)
			self.assertNotIn('hint', prob)
			self.assertGreaterEqual(m_diag.call_count, 1)
		with patch.object(blocks, 'df_clean_null', wraps=df_clean_null) as m_blk:
			out = blocks._build_turn_trace(turn_index=1, turn_id='ag-1-0', turn_key='k1', start_step=0)
			self.assertEqual('ag-1-0', out['ID'])
			self.assertGreaterEqual(m_blk.call_count, 1)
		with patch.object(shell_audit, 'dfa_unique_fast', wraps=dfa_unique_fast) as m_sa:
			urls = shell_audit.extract_issue_urls('https://github.com/a/b/issues/1 https://github.com/a/b/issues/1')
			self.assertEqual(['https://github.com/a/b/issues/1'], urls)
			self.assertGreaterEqual(m_sa.call_count, 1)
		with patch.object(commands, 'dfa_unique_fast', wraps=dfa_unique_fast) as m_cmd:
			res = commands.classify_test_command('pytest tests/test_a.py tests/test_a.py')
			self.assertEqual(['tests/test_a.py'], res['target_paths'])
			self.assertGreaterEqual(m_cmd.call_count, 1)
	# @used-by :mod:`unittest`
	def test_first_last_starts_with_and_is_windows_delegation_to_df(self) -> None:
		from Df.Core.lib.array.first import df_first, df_last
		from Df.Core.lib.state import df_is_windows
		from Df.Core.lib.text.starts_ends import df_starts_with
		from agent_tools import hook_runtime, issue_first_gate, process_tree, storage
		from agent_tools.platforms import clarifications
		from agent_tools.tdd import outcomes
		with patch.object(outcomes, 'df_first', wraps=df_first) as m_first:
			parsed = outcomes.parse_command_outcome('Tool is running as a background task with task id: conv/task-7')
			self.assertEqual('conv/task-7', parsed['background_task_id'])
			self.assertGreaterEqual(m_first.call_count, 1)
		with patch.object(clarifications, 'df_last', wraps=df_last) as m_last:
			self.assertIsNone(clarifications._find_generic_output([], 0, 0))
			self.assertGreaterEqual(m_last.call_count, 1)
		with patch.object(issue_first_gate, 'df_starts_with', wraps=df_starts_with) as m_sw:
			self.assertTrue(issue_first_gate._is_excluded_meta_rel('\ua616/data/state.json'))
			self.assertGreaterEqual(m_sw.call_count, 1)
		self.assertIs(df_is_windows, process_tree.df_is_windows)
		self.assertIs(df_is_windows, storage.df_is_windows)
		self.assertIs(df_last, hook_runtime.df_last)
if '__main__' == __name__:
	unittest.main()