# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from argparse import Namespace
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import io
import json
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-27 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :mod:`unittest`
class DfHarnessS11Wave2dCliCovTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_cli_domain_ops_all_handlers_and_collect_merge(self) -> None:
		from Df.Harness.Cli.DomainExecutor import DomainExecutor
		from Df.Harness.lib import cli_domain_ops as ops
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / '\ua616/KB/Evidence').mkdir(parents=True)
			(root / '\ua616/data/scratch').mkdir(parents=True)
			spec = root / '\ua616/data/scratch/s.json'
			spec.write_text(json.dumps({'id': 'Q1', 'question': 'q', 'impact': 'i', 'done_when': 'd', 'inputs': [], 'outputs': []}), encoding='utf-8')
			ans = root / '\ua616/data/scratch/ans.md'
			ans.write_text('body\n', encoding='utf-8')
			an_in = root / '\ua616/KB/a.json'
			an_in.write_text(json.dumps({'domain': 'example.com'}), encoding='utf-8')
			self.assertEqual(ops.dfh_analysis_root(an_in), root)
			self.assertEqual(ops._resolve_project_input(root, 'rel.json'), str(root / 'rel.json'))
			target = root / '\ua616/KB/Evidence/rep.json'
			target.write_bytes(json.dumps({'results': [{'request_key': 'k1', 'url': 'https://a'}], 'complete': True}).encode('utf-8'))
			rcpt = root / '\ua616/data/rendered.json'
			rcpt.write_text(json.dumps({str(target): {'sha256': 'ok'}}), encoding='utf-8')
			merged = ops._merge_prior_collection(root, target, rcpt, {'results': [{'request_key': 'k2'}], 'complete': True}, lambda _b: 'ok', lambda _p, items: {'n': len(items)})
			self.assertEqual(len(merged['results']), 2)
			ns = Namespace(command='status', operation='status', package='pkg', project=str(root), conversation='c1', allow_finalized=False, url='https://a', urls=['https://a'], url_file=None, tab_id='1', session_id=None, refresh_reason=None, profile='p', scope='s', browser='auto', cdp_port=None, anchors=False, grep=None, context_lines=2, max_matches=5, source='src', git_subcommand='status', git_args=[], short=True, stat=False, check=False, traces=['t.jsonl'], bindings=None, instance=None, platform=None, role='A.A', parent='p1', save=False, reviewer='r1', wait_timeout=0.0, spec=str(spec), amendment_of=None, amendment_reason=None, response_file=str(ans), id='Q1', owner='A.A', output=None, gap=None, results=None, previous_owner='A.A', new_owner='A.F', reason='r', query='q', useful=True, method_change=None, report=str(ans), native_evidence=None, input=str(an_in), promote_domain=True, request_file=None, review_id='rv1', finding_id='f1', status='fixed', basis='b', evidence='e', candidate=str(an_in), expected_sha256=None, merge=False, partial=False, file='f', part='p', stage='1', note='n', media_descriptions=None, no_fetch_videos=True, request_id=None, plan=str(spec), consume_input=False)
			stub = lambda *_a, **_k: {'ok': True, 'target': str(an_in), 'status': 'written', 'publication': {'status': 'written'}}
			with ExitStack() as st:
				for mod, attrs in (('agent_tools.workflow', ('adopt_requests', 'check_project', 'prepare_review', 'add_question', 'claim_question', 'finish_question', 'handoff', 'record_search', 'record_current_answer', 'record_review', 'resume', 'record_review_disposition', 'review_input', 'complete_stage', 'status', 'unadopt_requests')), ('agent_tools.research', ('capture_dom', 'collect_browser', 'collect_http', 'evidence_query', 'extract_observation', 'extract_file', 'collect_plan')), ('agent_tools.metrics', ('summarize', 'project_metrics', 'native_executor_metadata', 'native_review_proof')), ('agent_tools.experiments', ('prepare_experiment', 'record_experiment')), ('agent_tools.analysis', ('publish_analysis', 'save_analysis', 'publish_owned'))):
					st.enter_context(patch.multiple(mod, **{a: stub for a in attrs}))
				for target_sym in ('agent_tools.project_rename.apply_domain_promotion', 'agent_tools.git_gate.read_git', 'agent_tools.evidence.source_reference', 'agent_tools.knowledge.sync_project_attachments_and_kb'):
					st.enter_context(patch(target_sym, stub))
				for op_name in sorted(ops.OPERATION_HANDLERS):
					ns.command = op_name
					self.assertIsNotNone(DomainExecutor(ns).run())
	# @used-by :mod:`unittest`
	def test_cli_input_guards_and_error_payloads(self) -> None:
		from Df.Harness.lib import cli_input as ci
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			scratch = root / '\ua616/data/scratch'
			scratch.mkdir(parents=True)
			f = scratch / 'note.txt'
			f.write_bytes(b'hello')
			self.assertEqual(ci.dfh_verify_scratch_input_path(root, f), f.resolve())
			args = Namespace(project=str(root), consume_input=True)
			data = ci.dfh_load_operation_input(args, f)
			self.assertEqual(data, b'hello')
			res = ci.dfh_consume_scratch_input(args, f, data, {'valid': True})
			self.assertTrue(res['consumed_input'])
			self.assertFalse(f.exists())
			f2 = scratch / 'other.txt'
			f2.write_bytes(b'abc')
			self.assertEqual(ci.dfh_consume_unchanged_files([(f2, b'abc')]), [str(f2.resolve())])
			err = ci.dfh_operation_error_payload(ValueError('bad'))
			self.assertFalse(err['valid'])
			(root / '\ua616/data/turns').mkdir(parents=True)
			(root / '\ua616/data/turns/other.json').write_text(json.dumps({'status': 'open', 'conversation_id': 'c2'}), encoding='utf-8')
			with self.assertRaises(ValueError):
				ci._check_parallel_answer_md_guard(Namespace(project=str(root), command='answer-prepare', conversation='c1'), scratch / 'answer.md')
	# @used-by :mod:`unittest`
	def test_cli_registry_handlers_formatters_and_docs(self) -> None:
		from Df.Harness.Cli.RegistryExecutor import RegistryExecutor
		from Df.Harness.lib import cli_registry_defs as rdefs, cli_registry_handlers as rh
		self.assertIn('xref-check', rdefs.dfh_registered_commands())
		self.assertIn('xref-check', rdefs.dfh_render_cli_index())
		self.assertIn('commands', rdefs._exec_cli_docs(Namespace()))
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			resp = root / 'r.md'
			resp.write_text('body\n', encoding='utf-8')
			ns = Namespace(command='schema-help', operation='schema-help', response_file=str(resp), consume_input=False, mode='single', repo=str(root), owner='o', wait=False, timeout=1.0, ttl=1.0, poll_interval=0.1, force=False, issue='https://github.com/a/b/issues/1', project=str(root), source_project=None, no_issue=False, domain='d', topic='cli', daily_root=None, no_register=True, launcher_root=None, apply=False, push=False, include_task_groups=False, extra_commit=[], primary=str(root), workspace=None, semantic_brief=True, target=str(root), workers=1, module_timeout=10, no_failfast=False, pattern=None, module=None, runner='pytest', store_dir=str(root), keep=False, conversation='c1', launcher=None, platform='antigravity', backend=None, exec_rename_domain=None, command_spec=None, replacement='x', reason='r', regex=False, ignore_case=False, turn_key=None, clean=True, lease_free=True, poll=0.1, task='t', base='main', worktrees_dir=None, worktree=str(root), no_tests=True, remove=False, tag=False, no_tests_reason='doc', lang='python', file=None, dry_run=True, format='text')
			stub = lambda *_a, **_k: {'valid': True, 'markdown': 'md\n', 'ok': True}
			txt = lambda _r: 'ok'
			with ExitStack() as st:
				for sym, fn in (('agent_tools.landing_lease.acquire_lease', stub), ('agent_tools.landing_lease.release_lease', stub), ('agent_tools.landing_lease.lease_status', stub), ('agent_tools.perf.suite_profiler.run_perf_profile_cli', stub), ('agent_tools.perf.suite_profiler.format_profile_text', txt), ('agent_tools.perf.timesheet.run_perf_timesheet_cli', stub), ('agent_tools.perf.timesheet.format_timesheet_text', txt), ('agent_tools.metadata.build_problem_metadata', stub), ('agent_tools.metadata.render_metadata_header', lambda _m: 'hdr'), ('agent_tools.project_rename.rename_project', stub), ('agent_tools.repo_tags.run_repo_tag_cli', stub), ('agent_tools.repo_tags.retro_tag_repo', stub), ('agent_tools.rules_audit.audit_rules', stub), ('agent_tools.rules_audit.build_semantic_audit_brief', stub), ('agent_tools.rules_audit.format_rules_audit_text', txt), ('agent_tools.rules_manifest.resolve_rules_primary', lambda p, _d: Path(p)), ('agent_tools.suite_runner.run_test_suite', stub), ('agent_tools.suite_runner.format_text_report', txt), ('Df.Harness.lib.cli_registry_handlers.SnapshotPromoter.run', stub), ('Df.Harness.lib.cli_registry_handlers.dfh_check_runtime_snapshot', stub), ('agent_tools.schema_help.schema_help_payload', stub), ('agent_tools.schema_help.format_schema_help_text', txt), ('Df.Harness.lib.cli_registry_handlers.ReplayRunner.run', stub), ('agent_tools.tdd.mechanical.record_mechanical_exemption', stub), ('agent_tools.watchdog_runner.run_watchdog_cli', stub), ('agent_tools.repo_wait.wait_for_repo', stub), ('agent_tools.worktree_flow.worktree_begin', stub), ('agent_tools.worktree_flow.worktree_cleanup', stub), ('agent_tools.worktree_flow.worktree_land', stub), ('agent_tools.worktree_flow.worktree_status', stub), ('agent_tools.xref.run_xref_check', stub), ('agent_tools.xref.run_xref_sync', stub), ('agent_tools.xref.format_xref_text', txt)):
					st.enter_context(patch(sym, fn))
				for fn in (rh.dfh_exec_analysis_check, rh.dfh_exec_land_acquire, rh.dfh_exec_land_release, rh.dfh_exec_land_status, rh.dfh_exec_perf_profile_tests, rh.dfh_exec_perf_timesheet, rh.dfh_exec_problem_metadata, rh.dfh_exec_rename_project, rh.dfh_exec_repo_tag, rh.dfh_exec_repo_tag_retro, rh.dfh_exec_rules_audit, rh.dfh_exec_run_tests, rh.dfh_exec_runtime_promote, rh.dfh_exec_runtime_status, rh.dfh_exec_schema_help, rh.dfh_exec_shadow_replay, rh.dfh_exec_tdd_exempt_mechanical, rh.dfh_exec_test_watchdog, rh.dfh_exec_wait_repo, rh.dfh_exec_worktree_begin, rh.dfh_exec_worktree_cleanup, rh.dfh_exec_worktree_land, rh.dfh_exec_worktree_status, rh.dfh_exec_xref_check, rh.dfh_exec_xref_sync):
					self.assertIsInstance(fn(ns), dict)
				for fmt in (rh.dfh_format_perf_profile_tests, rh.dfh_format_perf_timesheet, rh.dfh_format_problem_metadata, rh.dfh_format_rules_audit, rh.dfh_format_run_tests, rh.dfh_format_schema_help, rh.dfh_format_test_watchdog, rh.dfh_format_xref):
					fmt({'markdown': 'm'}, ns)
				self.assertTrue(RegistryExecutor(ns).run()[0])
	# @used-by :mod:`unittest`
	def test_dispatcher_and_git_shim_modes(self) -> None:
		from Df.Harness.Cli.Dispatcher import Dispatcher
		from Df.Harness.Cli.GitShim import GitShim
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			jdir = root / '\ua66e'
			doc = root / 'a.md'
			doc.write_text('# Title\nBody.\n', encoding='utf-8')
			stm = root / 'stm'
			(stm / '01').mkdir(parents=True)
			(stm / '01/.md').write_text('s\n', encoding='utf-8')
			(stm / '01/Statement.md').write_text('s\n', encoding='utf-8')
			(stm / '01/Test.md').write_text('t\n', encoding='utf-8')
			buf = io.StringIO()
			with patch('sys.stdout', buf), patch('agent_tools.snapshot.snapshot_draft', return_value='snap'), patch('agent_tools.git_gate.commit', return_value=['a.md']), patch('agent_tools.context.generate', return_value=(root / 'C.md', 'ctx', ['a.md'])), patch('agent_tools.links.check_network', return_value=[{'status': 'http-ok'}]):
				self.assertEqual(Dispatcher('snapshot_draft', [str(doc), '--turn', '1']).run(), 0)
				self.assertEqual(Dispatcher('safe_commit', ['--repo', str(root), '--file', 'a.md', '-m', 'msg']).run(), 0)
				self.assertEqual(Dispatcher('validate_statements', [str(stm)]).run(), 0)
				self.assertEqual(Dispatcher('generate_context', [str(root), '--dry-run']).run(), 0)
				self.assertEqual(Dispatcher('record_step', ['--dir', str(jdir), '--req', 'q', '--res', 'a']).run(), 0)
				self.assertEqual(Dispatcher('validate_step', ['--dir', str(jdir), '--step', '1']).run(), 0)
				self.assertEqual(Dispatcher('validate_links', [str(doc)]).run(), 0)
				self.assertEqual(Dispatcher('validate_anchors', [str(doc)]).run(), 0)
			git_exe = GitShim([], mode='resolve_git').run()
			self.assertTrue(Path(git_exe).is_file())
			with patch('Df.Harness.Cli.GitShim.subprocess.run', return_value=Namespace(returncode=0)), patch('Df.Harness.Cli.GitShim.cleanup_stale_credential_locks'):
				self.assertEqual(GitShim(['status'], mode='main').run(), 0)
				with patch('Df.Harness.Cli.GitShim.run_git_hook', return_value=0):
					self.assertEqual(GitShim(['--hook', 'pre-commit'], mode='main').run(), 0)
if '__main__' == __name__:
	unittest.main()
