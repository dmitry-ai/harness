# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
from copy import deepcopy
import io
import json
import os
from pathlib import Path
from contextlib import redirect_stdout
import sys
import unittest
for _d in (Path(__file__).resolve().parent, Path(__file__).resolve().parents[1] / 'scripts'):
	if str(_d) not in sys.path:
		sys.path.insert(0, str(_d))
from test_agent_tools import TemporaryCase
from agent_tools import git_gate, github_issue, journal, path_registry as pr, runtime, storage, upwork_project as up
import check_markdown_slop
import check_stop_gate


class PathRegistryTests(TemporaryCase):
	def tearDown(self):
		pr.clear_registry_cache()
		super().tearDown()

	def test_live_registry_and_runtime_contain_no_hardcoded_host_paths_outside_r_and_validate_five_overlays(self):
		raw_runtime = json.loads((runtime.PRIMARY / 'runtime.json').read_text(encoding='utf-8'))
		serialized_runtime = json.dumps(raw_runtime)
		for forbidden in ('C:/work', 'C:/Users', 'C:/tools', 'C:/ChromeU', 'C:/server'):
			self.assertNotIn(forbidden, serialized_runtime)
		rep = pr.paths_report(check=True)
		self.assertTrue(rep['valid'], rep['issues'])
		self.assertEqual(rep['issues'], [])
		by_root = {item['project_root']: item for item in rep['discovered_overlays']}
		expected_projects = {
			'C:/work/research/provision/code/AI/harness': 'dual_repo',
			'C:/work/upwork/code/proposals/daily/2026/10/26/1 - smokeday.com': 'upwork',
			'C:/work/research/provision/code/AI/products/Google/Antigravity/Addons': 'dual_repo',
			'C:/work/research/provision/code/AI/products/OpenAI/ChatGPT/Desktop/Addons': 'dual_repo',
			'C:/work/git/dmitrii-fediuk/code/5.9.188.84': 'server',
		}
		for root_str, expected_profile in expected_projects.items():
			self.assertIn(root_str, by_root)
			self.assertEqual(by_root[root_str]['profile'], expected_profile)

	def test_apache_prefix_concatenation_windows_env_vars_globs_and_escapes(self):
		vars_map = {
			'WORK_ROOT': 'C:/work',
			'DF_CLIENTS': '${WORK_ROOT}/clients/',
			'LOCAL_INSTALL': '%LOCALAPPDATA%/Programs/antigravity',
			'ENV_COLON': '${ENV:APPDATA}/Codex-Profile2',
			'GLOB_BIN': '${WORK_ROOT}/tools/*/headless.exe',
		}
		env = {'LOCALAPPDATA': 'C:\\Users\\demo\\AppData\\Local', 'appdata': 'C:\\Users\\demo\\AppData\\Roaming'}
		self.assertEqual(
			pr.expand_template('${DF_CLIENTS}smokeday.com/m/2026-10-26/code', vars_map, env=env),
			'C:/work/clients/smokeday.com/m/2026-10-26/code',
		)
		self.assertEqual(
			pr.expand_template('${DF_CLIENTS}/smokeday.com/m/2026-10-26/code', vars_map, env=env),
			'C:/work/clients/smokeday.com/m/2026-10-26/code',
		)
		self.assertEqual(pr.expand_template('${DF_CLIENTS}', vars_map, env=env), 'C:/work/clients')
		self.assertEqual(pr.expand_template('${LOCAL_INSTALL}/Antigravity.exe', vars_map, env=env), 'C:/Users/demo/AppData/Local/Programs/antigravity/Antigravity.exe')
		self.assertEqual(pr.expand_template('${ENV_COLON}', vars_map, env=env), 'C:/Users/demo/AppData/Roaming/Codex-Profile2')
		self.assertEqual(pr.expand_template('${GLOB_BIN}', vars_map, env=env), 'C:/work/tools/*/headless.exe')
		self.assertEqual(pr.expand_template('C:/work/$${LITERAL}/100%%_ok', vars_map, env=env), 'C:/work/${LITERAL}/100%_ok')
		self.assertEqual(pr.expand_template('', vars_map, env=env), '')
		self.assertEqual(pr.expand_template('//fileserver/share//a/../b/', vars_map, env=env), '//fileserver/share/b')
		empty_env_res = pr.expand_template('%LOCALAPPDATA%/Sub', {}, env={})
		self.assertTrue(empty_env_res.endswith('/AppData/Local/Sub'))

	def test_template_and_schema_error_paths_reject_cycles_unknowns_symlinks_and_conflicts(self):
		with self.assertRaisesRegex(ValueError, 'Cyclic path template variable reference: A -> A'):
			pr.expand_template('${A}', {'A': '${A}'})
		with self.assertRaisesRegex(ValueError, 'Cyclic path template variable reference: A -> B -> C -> A'):
			pr.expand_template('${A}', {'A': '${B}/1', 'B': '${C}/2', 'C': '${A}/3'})
		with self.assertRaisesRegex(ValueError, 'Unknown path template variable'):
			pr.expand_template('${MISSING_VAR}/x', {'WORK': 'C:/work'})
		with self.assertRaisesRegex(ValueError, 'Unresolved environment variable'):
			pr.expand_template('%DEFINITELY_MISSING_ENV_VAR%/x', {}, env={})
		with self.assertRaisesRegex(ValueError, 'Unresolved environment variable'):
			pr.expand_template('${ENV:DEFINITELY_MISSING_ENV_VAR}/x', {}, env={})
		with self.assertRaisesRegex(ValueError, 'Unclosed template variable'):
			pr.expand_template('C:/work/${UNCLOSED', {'UNCLOSED': 'x'})
		with self.assertRaisesRegex(ValueError, 'Invalid path template variable syntax'):
			pr.expand_template('${123_BAD}', {})
		with self.assertRaisesRegex(ValueError, 'Invalid path template variable syntax'):
			pr.expand_template('${}', {})

		bad_reg = self.put('bad-paths.json', json.dumps({'version': 2}))
		with self.assertRaisesRegex(ValueError, 'version 1'):
			pr.load_registry(bad_reg)

		cyclic_prof_data = deepcopy(pr.load_registry().raw)
		cyclic_prof_data['project_profiles']['p1'] = {'extends': 'p2', 'paths': {}}
		cyclic_prof_data['project_profiles']['p2'] = {'extends': 'p1', 'paths': {}}
		cyclic_reg = self.put('cyclic-prof.json', json.dumps(cyclic_prof_data))
		with self.assertRaisesRegex(ValueError, 'Cyclic project profile inheritance'):
			pr.load_registry(cyclic_reg)

		proj = self.root / 'conflict_proj'
		self.put('conflict_proj/.agents/paths.json', json.dumps({'version': 1, 'paths': {'scratch_dir': 'a'}}))
		self.put('conflict_proj/\ua616/paths.json', json.dumps({'version': 1, 'paths': {'scratch_dir': 'b'}}))
		with self.assertRaisesRegex(ValueError, 'Conflicting project paths.json overlays'):
			pr.project_paths(proj)

		real_ov = self.put('outside.json', json.dumps({'version': 1}))
		sym_proj = self.root / 'sym_proj'
		(sym_proj / '.agents').mkdir(parents=True)
		sym_file = sym_proj / '.agents/paths.json'
		try:
			sym_file.symlink_to(real_ov)
		except OSError:
			pass
		else:
			with self.assertRaisesRegex(ValueError, 'Linked project paths.json overlay'):
				pr.project_paths(sym_proj)

	def test_project_overlay_dag_cascades_and_remains_isolated_per_project(self):
		proj_a = self.root / 'proj_a'
		ext_client = self.root / 'external_client'
		ext_code = ext_client / 'code'
		(ext_code / '.git').mkdir(parents=True)
		overlay_a = {
			'version': 1,
			'profile': 'upwork',
			'variables': {
				'EXT_CLIENT': ext_client.as_posix(),
				'CUSTOM_SLOT': '${PROJECT_ROOT}/custom_slot_val',
			},
			'paths': {
				'agent_dir': '${PROJECT_ROOT}/_isolated_agent',
				'journal_dir': '${JOURNAL_ROOT_DIR}/CustomJournal',
				'custom_slot': '${CUSTOM_SLOT}',
				'letters_dir': '${EXT_CLIENT}/Letters',
			},
			'code_repos': ['${EXT_CLIENT}/code'],
			'linked_roots': ['${EXT_CLIENT}'],
		}
		self.put('proj_a/.agents/paths.json', json.dumps(overlay_a))
		proj_b = self.root / 'proj_b'
		(proj_b / '\ua616').mkdir(parents=True)

		pp_a = pr.project_paths(proj_a)
		pp_b = pr.project_paths(proj_b)
		self.assertEqual(pp_a.agent_dir, (proj_a / '_isolated_agent').resolve())
		self.assertEqual(pp_a.data_dir, (proj_a / '_isolated_agent/data').resolve())
		self.assertEqual(pp_a.turns_dir, (proj_a / '_isolated_agent/data/turns').resolve())
		self.assertEqual(pp_a.kb_dir, (proj_a / '_isolated_agent/KB').resolve())
		self.assertEqual(pp_a.evidence_dir, (proj_a / '_isolated_agent/KB/Evidence').resolve())
		self.assertEqual(pp_a.metrics_json, (proj_a / '_isolated_agent/data/research-metrics.json').resolve())
		self.assertEqual(pp_a.journal_dir, (proj_a / '\ua66e/CustomJournal').resolve())
		self.assertEqual(pp_a.path('custom_slot'), (proj_a / 'custom_slot_val').resolve())
		self.assertEqual(pp_a.path('letters_dir'), (ext_client / 'Letters').resolve())
		self.assertEqual(storage.data_dir_for(proj_a), (proj_a / '_isolated_agent/data').resolve())
		self.assertEqual(journal.resolve_journal_dir(proj_a), (proj_a / '\ua66e/CustomJournal').resolve())
		self.assertEqual(pr.resolve_project_root(ext_client / 'Letters/EN/1.md'), proj_a.resolve())
		self.assertTrue(git_gate.GitRepoGate(ext_code).is_issue_tracked())

		self.assertEqual(pp_b.agent_dir, (proj_b / '\ua616').resolve())
		self.assertIsNone(pp_b.path('custom_slot'))

	def test_live_five_projects_integration_across_harness_subsystems_and_cli(self):
		harness_pp = pr.project_paths('C:/work/research/provision/code/AI/harness')
		self.assertEqual(harness_pp.agent_dir.as_posix(), 'C:/work/research/provision/code/AI/harness/_/\ua616')
		self.assertEqual(harness_pp.metrics_json.as_posix(), 'C:/work/research/provision/code/AI/harness/_/\ua616/data/research-metrics.json')
		self.assertEqual(journal.resolve_journal_dir(harness_pp.root).as_posix(), 'C:/work/research/provision/code/AI/harness/_/\ua66e')

		smokeday_root = Path('C:/work/upwork/code/proposals/daily/2026/10/26/1 - smokeday.com')
		smokeday_client_code = Path('C:/work/clients/smokeday.com/m/2026-10-26/code')
		smokeday_pp = pr.project_paths(smokeday_root)
		self.assertEqual(smokeday_pp.path('client_code_dir'), smokeday_client_code)
		self.assertEqual(journal.resolve_journal_dir(smokeday_root).as_posix(), 'C:/work/upwork/code/proposals/daily/2026/10/26/1 - smokeday.com/\ua66e/1 - Анализ')
		self.assertEqual(pr.resolve_project_root(smokeday_client_code / '_my/public/Letters/my/EN/1.md'), smokeday_root.resolve())
		self.assertEqual(check_markdown_slop._infer_project_root(smokeday_client_code / '_my/public/Letters/my/EN/1.md'), smokeday_root.resolve())
		self.assertTrue(git_gate.GitRepoGate(smokeday_client_code).is_issue_tracked())
		self.assertEqual(github_issue.find_local_code_repo('smokeday-com/m', project_root=smokeday_root), smokeday_client_code.resolve())

		srv_root = Path('C:/work/git/dmitrii-fediuk/code/5.9.188.84')
		self.assertTrue(git_gate.GitRepoGate(srv_root).is_issue_tracked())
		self.assertTrue(check_stop_gate._is_tracked_workspace(srv_root))
		self.assertEqual(github_issue.find_local_code_repo('dmitrii-fediuk/5.9.188.84'), srv_root.resolve())
		self.assertEqual(
			journal.resolve_journal_dir(srv_root).as_posix(),
			'C:/work/git/dmitrii-fediuk/code/5.9.188.84/_my/daily/2026/11/07/1 - Nginx/\ua66e',
		)

		buf = io.StringIO()
		with redirect_stdout(buf):
			rc = up.main(['paths', str(smokeday_root), '--expand', '${DF_CLIENTS}smokeday.com/m/2026-10-26/code', '--check'])
		self.assertEqual(rc, 0)
		cli_out = json.loads(buf.getvalue())
		self.assertTrue(cli_out['valid'])
		self.assertEqual(cli_out['expanded'], 'C:/work/clients/smokeday.com/m/2026-10-26/code')
		self.assertTrue(check_stop_gate._is_tracked_workspace(smokeday_client_code))
		self.assertEqual(check_stop_gate._turns_dir(smokeday_client_code), smokeday_pp.turns_dir)

	def test_transitive_escapes_literal_dollar_in_env_and_relative_slot_anchoring(self):
		self.assertEqual(
			pr.expand_template('${B}/end', {'A': '$${LITERAL_VAR}', 'B': '${A}/mid'}),
			'${LITERAL_VAR}/mid/end',
		)
		weird_env = {'WEIRD_DIR': 'C:\\Users\\a${INJECT}%PCT%'}
		self.assertEqual(
			pr.expand_template('%WEIRD_DIR%/tail', {}, env=weird_env),
			'C:/Users/a${INJECT}%PCT%/tail',
		)
		self.assertEqual(
			pr.expand_template('${ENV:WEIRD_DIR}/tail', {}, env=weird_env),
			'C:/Users/a${INJECT}%PCT%/tail',
		)
		proj = self.root / 'rel_slot_proj'
		self.put(
			'rel_slot_proj/.agents/paths.json',
			json.dumps({
				'version': 1,
				'paths': {
					'sub_tool': '${CUSTOM_SUB}/tool.exe',
					'custom_sub': '${DATA_DIR}/sub',
					'agent_dir': '_rel_agent',
				},
				'tools': {'runner': '${CUSTOM_SUB}/runner.exe'},
			}),
		)
		pp = pr.project_paths(proj)
		expected_data = (proj.resolve() / '_rel_agent/data').as_posix()
		self.assertEqual(pp.var('DATA_DIR'), expected_data)
		self.assertEqual(pp.path('sub_tool'), (proj.resolve() / '_rel_agent/data/sub/tool.exe'))
		self.assertEqual(pp.tools['runner'], f'{expected_data}/sub/runner.exe')

	def test_mid_process_overlay_creation_and_edit_invalidate_reverse_links_and_stay_fast(self):
		import time
		disc = (self.root / 'disc_proj').resolve()
		disc.mkdir(parents=True)
		ext_one = (self.root / 'ext_one').resolve()
		ext_two = (self.root / 'ext_two').resolve()
		ext_one.mkdir()
		ext_two.mkdir()
		raw_reg = deepcopy(pr.load_registry().raw)
		raw_reg['project_overlays']['discovery_roots'] = [disc.as_posix()]
		raw_reg['project_overlays']['discovery_globs'] = []
		reg_file = self.put('custom-paths.json', json.dumps(raw_reg))
		reg = pr.load_registry(reg_file)
		self.assertEqual(pr.resolve_project_root(ext_one, registry=reg), ext_one)
		self.put('disc_proj/.agents/paths.json', json.dumps({'version': 1, 'linked_roots': [ext_one.as_posix()]}))
		self.assertEqual(pr.resolve_project_root(ext_one, registry=reg), disc)
		self.put('disc_proj/.agents/paths.json', json.dumps({'version': 1, 'linked_roots': [ext_two.as_posix()]}))
		self.assertEqual(pr.resolve_project_root(ext_two, registry=reg), disc)

		perf_proj = self.root / 'perf_proj'
		(perf_proj / '\ua616').mkdir(parents=True)
		storage.data_dir_for(perf_proj)
		t0 = time.perf_counter()
		for _ in range(200):
			storage.data_dir_for(perf_proj)
		elapsed = time.perf_counter() - t0
		self.assertLess(elapsed, 2.0, f'200 warm data_dir_for calls took {elapsed:.3f}s')

	def test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization(self):
		from unittest.mock import patch
		from agent_tools import completion, context as ctx_mod, text_claims, text_diagnostics, text_workflow, workflow
		dual = self.root / 'dual_proj'
		(dual / 'code').mkdir(parents=True)
		(dual / '_/\ua616/KB/Evidence').mkdir(parents=True)
		self.put('dual_proj/_/\ua616/KB/Overview.md', '# Dual Overview  \n')
		self.put('dual_proj/_/\ua616/KB/Evidence/secret.md', '# Excluded Evidence  \n')
		target_ctx, content_ctx, selected_ctx = ctx_mod.generate(dual / 'code')
		self.assertEqual(target_ctx, (dual / '_/\ua66e/0/Context.md').resolve())
		self.assertEqual(selected_ctx, [(dual / '_/\ua616/KB/Overview.md').resolve()])
		self.assertNotIn('Excluded Evidence', content_ctx)

		custom = self.root / 'custom_upwork'
		ext_letters = self.root / 'ext_letters_store'
		self.put(
			'custom_upwork/.agents/paths.json',
			json.dumps({
				'version': 1,
				'profile': 'upwork',
				'variables': {'EXT_LETTERS': ext_letters.as_posix()},
				'paths': {
					'agent_dir': '_custom_agent',
					'letters_dir': '${EXT_LETTERS}/Letters',
				},
				'linked_roots': ['${EXT_LETTERS}'],
			}),
		)
		self.put('ext_letters_store/Letters/my/EN/1/final.md', 'Hello from linked root.  \n')
		self.put('custom_upwork/.md', '# Custom Project  \n')
		self.put('custom_upwork/_custom_agent/KB/Notes.md', '# Custom KB  \nSingle sentence note.  \n')
		self.put('custom_upwork/_custom_agent/project.json', json.dumps({'job_id': '~0123456789abcdef', 'initialized': True, 'request_date': '2026-11-19', 'snapshot': '_custom_agent/KB/Evidence/snap.json'}))
		custom_manifest = {
			'version': 1,
			'output': '${CONTEXT_OUTPUT}',
			'sections': [
				{'title': 'KB', 'globs': ['${KB_DIR}/**/*.md'], 'exclude': ['${EVIDENCE_DIR}/**']},
				{'title': 'Letters', 'letters': [{'root': '${LETTERS_DIR}/my', 'author': 'Consultant', 'languages': ['EN']}]},
			],
		}
		c_target, c_text, _ = ctx_mod.generate(custom, custom_manifest)
		self.assertEqual(c_target, (custom / '\ua66e/0/Context.md').resolve())
		self.assertIn('Hello from linked root.', c_text)
		self.assertIn('Single sentence note.', c_text)

		st = workflow.status(custom)
		self.assertEqual(Path(st['agent_kb']), (custom / '_custom_agent/KB').resolve())
		self.assertEqual(st['kb_hashes'], {'_custom_agent/KB/Notes.md': workflow.file_hash(custom / '_custom_agent/KB/Notes.md')})

		self.put('custom_upwork/article.md', '# Heading\n\nInitial text.  \n')
		ws = text_workflow.ClientTextWorkspace(custom)
		self.assertEqual(ws.folder, (custom / '_custom_agent/data/texts').resolve())
		op = ws.begin({'kind': 'article', 'mode': 'propose', 'changes': 'prose', 'goal': 'Test R+ text workspace', 'requests': ['Req'], 'target': 'article.md'})
		self.assertTrue((custom / '_custom_agent/data/texts/operations' / op['id'] / 'operation.json').is_file())
		reg_res = text_claims.save_registry(custom, {'schema_version': 3, 'facts': []})
		self.assertEqual(reg_res['registry'], '_custom_agent/KB/TextClaims.json')

		proj_file = self.put('dual_proj/AGENTS.md', '# Projected\n')
		proj_sha = workflow.file_hash(proj_file)
		self.put('dual_proj/_/\ua616/data/native-config.json', json.dumps({str(proj_file.resolve()): proj_sha}))
		diag = text_diagnostics.diagnose_sources(dual)
		rec_items = [s for s in diag['sources'] if 'projection-receipt' == s['kind']]
		self.assertTrue(any((item['exists'] and Path(item['path']).resolve() == (dual / '_/\ua616/data/native-config.json').resolve() for item in rec_items)))

		fake_turn = {
			'turn_id': 'turn-1',
			'start_step': 1,
			'final_step': 2,
			'completion_step': 2,
			'owned': True,
			'completed': False,
			'aborted': False,
			'requests': [{'id': 'req-1', 'text': 'Привет'}],
			'response': '',
		}
		fake_native = {
			'platform': 'antigravity',
			'native_backend': str((self.root / 'fake_backend').resolve()),
			'conversation_id': '11111111-2222-3333-4444-555555555555',
			'source_file': str((self.root / 'fake_trace.jsonl').resolve()),
			'primary': True,
			'active_turn_id': 'turn-1',
			'turns': [fake_turn],
		}
		with patch('agent_tools.completion._native', return_value=fake_native):
			b1 = completion.begin(dual / '_')
			b2 = completion.begin(dual / 'code')
			self.assertEqual(b1['turn_key'], b2['turn_key'])

		ext_turns = self.root / 'external_turns_store'
		ext_proj = self.root / 'ext_turns_proj'
		self.put('ext_turns_proj/.agents/paths.json', json.dumps({'version': 1, 'paths': {'turns_dir': ext_turns.as_posix()}}))
		state_path = ext_turns / 'k1.json'
		state_val = {'key': 'k1', 'status': 'open', 'prepared': None, 'delivery': None, 'requests': fake_turn['requests']}
		conf = completion._conflict(ext_proj, state_path, state_val, fake_native, fake_turn, 'mismatch', 'test external turns conflict')
		self.assertEqual(conf['status'], 'conflict')
		self.assertTrue(Path(conf['evidence']).is_file())

		ws_fake = self.root / 'fake_upwork_ws'
		ws_fake.mkdir(parents=True)
		ws_data = self.root / 'fake_ws_data'
		gh_ev = self.root / 'fake_gh_ev'
		ws_reg_raw = deepcopy(pr.load_registry().raw)
		ws_reg_raw['harness_stores']['github_evidence_dir'] = gh_ev.as_posix()
		ws_reg_raw['workspace_overrides'] = {ws_fake.as_posix(): {'data_dir': ws_data.as_posix()}}
		ws_reg_file = self.put('ws-paths.json', json.dumps(ws_reg_raw))
		with patch.dict(os.environ, {'HARNESS_PATHS_FILE': str(ws_reg_file)}):
			pr.clear_registry_cache()
			saved_ev = github_issue._persist_issue_evidence(
				[],
				'dmitry-ai/harness',
				{'number': 96, 'html_url': 'https://github.com/dmitry-ai/harness/issues/96', 'title': 'Test', 'state': 'open', 'body': 'Body'},
				project_root=ws_fake,
			)
			self.assertFalse((ws_fake / '\ua616').exists())
			self.assertTrue(Path(saved_ev).resolve().is_relative_to(gh_ev.resolve()))


if '__main__' == __name__:
	unittest.main()
