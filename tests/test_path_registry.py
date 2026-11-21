# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Separate OS user home from instance USERPROFILE and auto-detect active Antigravity instance":
# https://github.com/dmitry-ai/harness/issues/115
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
# https://github.com/dmitry-ai/harness/issues/113
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement versioned 20-entry journal bucketing and journal-only upgrade engine":
# https://github.com/dmitry-ai/harness/issues/108
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace V2 verbal directory names with Ⰿ/♕/♙ symbols and add Antigravity hook runner":
# https://github.com/dmitry-ai/harness/issues/103
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add versioned V1 and V2 path registry profiles and relocated native profile migration":
# https://github.com/dmitry-ai/harness/issues/100
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch
for _d in (Path(__file__).resolve().parent, Path(__file__).resolve().parents[1] / 'scripts'):
	if str(_d) not in sys.path:
		sys.path.insert(0, str(_d))
from test_agent_tools import TemporaryCase
from agent_tools import admission, context as ctx_mod, git_gate, github_issue, journal, path_registry as pr, runtime, source_grounding, storage, upwork_project as up
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
		addons_root = 'C:/work/research/provision/code/AI/products/Google/Antigravity/Addons'
		expected_projects = {
			'C:/work/research/provision/code/AI/harness': 'v2_software',
			'C:/work/clients/smokeday.com': 'v2',
			addons_root: 'dual_repo' if (Path(addons_root) / '_').is_dir() else 'v2_software',
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
		self.assertEqual(harness_pp.profile, 'v2_software')
		self.assertEqual(harness_pp.fs_version, 2)
		self.assertEqual(harness_pp.agent_dir.as_posix(), 'C:/work/research/provision/code/AI/harness/\ua616')
		self.assertEqual(harness_pp.metrics_json.as_posix(), 'C:/work/research/provision/code/AI/harness/\ua616/data/research-metrics.json')
		self.assertEqual(journal.resolve_journal_dir(harness_pp.root).as_posix(), 'C:/work/research/provision/code/AI/harness/\ua66e')
		self.assertEqual(
			tuple((p.name for p in journal.journal_pair_dirs(journal.resolve_journal_dir(harness_pp.root)))),
			('\u227b', '\u227a'),
		)
		expected_harness_code = Path('C:/work/research/provision/code/AI/harness/\u2c0f/\u227b/\u2655/\u26ef') if Path('C:/work/research/provision/code/AI/harness/\u2c0f').is_dir() else Path('C:/work/research/provision/code/AI/harness/Artifacts/\u227b/Deliverables/\u26ef')
		self.assertEqual(
			harness_pp.code_repos,
			(expected_harness_code.resolve(),),
		)
		smokeday_root = Path('C:/work/clients/smokeday.com')
		smokeday_legacy_su = Path('C:/work/upwork/code/proposals/daily/2026/10/26/1 - smokeday.com')
		smokeday_legacy_sc = Path('C:/work/clients/smokeday.com/m/2026-10-26/code')
		smokeday_client_code = smokeday_root / '\u2c0f/\u227b/\u2655/\u26ef/\U0001d416/smokeday.com/2026-10-26/\u26ef'
		smokeday_server_code = smokeday_root / '\u2c0f/\u227b/\u2655/\u26ef/\U0001d412'
		smokeday_core_mod = smokeday_client_code / 'vendor/smokeday/core'
		smokeday_pp = pr.project_paths(smokeday_root)
		self.assertEqual(smokeday_pp.profile, 'v2')
		self.assertEqual(smokeday_pp.fs_version, 2)
		self.assertEqual(smokeday_pp.journal_version, 3)
		self.assertEqual(smokeday_pp.path('idea_dir'), (smokeday_root / '.idea').resolve())
		self.assertEqual(smokeday_pp.path('server_deliverables_dir'), smokeday_server_code.resolve())
		self.assertEqual(smokeday_pp.path('website_deliverables_dir'), (smokeday_root / '\u2c0f/\u227b/\u2655/\u26ef/\U0001d416').resolve())
		self.assertEqual(smokeday_pp.path('client_code_dir'), smokeday_client_code.resolve())
		self.assertEqual(pr.canonicalize_root_dir(smokeday_legacy_su), smokeday_root.resolve())
		self.assertEqual(pr.canonicalize_root_dir(smokeday_legacy_sc), smokeday_root.resolve())
		self.assertEqual(pr.canonicalize_root_dir(smokeday_client_code), smokeday_root.resolve())
		self.assertEqual(pr.canonicalize_root_dir(smokeday_server_code), smokeday_root.resolve())
		self.assertEqual(pr.canonicalize_root_dir(smokeday_core_mod), smokeday_root.resolve())
		self.assertEqual(up.resolve_or_create_project_dir('~022114446200656909202', 'smokeday.com', '2026-10-26'), smokeday_root.resolve())
		self.assertEqual(journal.resolve_journal_dir(smokeday_root), (smokeday_root / '\ua66e').resolve())
		self.assertTrue(journal.same_journal_identity(smokeday_legacy_su / '\ua66e/1 - \u0410\u043d\u0430\u043b\u0438\u0437', smokeday_root / '\ua66e'))
		self.assertTrue(journal.same_journal_identity(smokeday_legacy_su / '\ua66e', smokeday_root / '\ua66e'))
		self.assertIn(309, journal.get_existing_step_ids(smokeday_root / '\ua66e'))
		self.assertEqual(pr.resolve_project_root(smokeday_root / '\u2c0f/\u227b/\u2655/\U0001f582/Letters/2026/11/07/result/draft.md'), smokeday_root.resolve())
		self.assertEqual(check_markdown_slop._infer_project_root(smokeday_root / '\u2c0f/\u227b/\u2655/\U0001f582/Letters/2026/11/07/result/draft.md'), smokeday_root.resolve())
		self.assertTrue(git_gate.GitRepoGate(smokeday_client_code).is_issue_tracked())
		self.assertTrue(git_gate.GitRepoGate(smokeday_server_code).is_issue_tracked())
		self.assertTrue(git_gate.GitRepoGate(smokeday_core_mod).is_issue_tracked())
		self.assertFalse(git_gate.GitRepoGate(smokeday_root).is_issue_tracked())
		self.assertEqual(github_issue.find_local_code_repo('smokeday-com/m'), smokeday_client_code.resolve())
		self.assertEqual(github_issue.find_local_code_repo('smokeday-com/s'), smokeday_server_code.resolve())
		self.assertEqual(github_issue.find_local_code_repo('smokeday-com/core'), smokeday_core_mod.resolve())
		self.assertEqual(github_issue.find_local_code_repo('smokeday-com/meta'), smokeday_root.resolve())
		srv_root = Path('C:/work/git/dmitrii-fediuk/code/5.9.188.84')
		self.assertTrue(git_gate.GitRepoGate(srv_root).is_issue_tracked())
		self.assertTrue(check_stop_gate._is_tracked_workspace(srv_root))
		self.assertEqual(github_issue.find_local_code_repo('dmitrii-fediuk/5.9.188.84'), srv_root.resolve())
		self.assertRegex(
			journal.resolve_journal_dir(srv_root).as_posix(),
			'^C:/work/git/dmitrii-fediuk/code/5\\.9\\.188\\.84/_my/daily/\\d{4}/\\d{2}/\\d{2}/\\d+ - .+/\ua66e$',
		)
		buf = io.StringIO()
		with redirect_stdout(buf):
			rc = up.main(['paths', str(smokeday_root), '--expand', '${MAGENTO_CODE_DIR}', '--check'])
		self.assertEqual(rc, 0)
		cli_out = json.loads(buf.getvalue())
		self.assertTrue(cli_out['valid'])
		self.assertEqual(cli_out['expanded'], smokeday_client_code.as_posix())
		self.assertTrue(check_stop_gate._is_tracked_workspace(smokeday_client_code))
		self.assertTrue(check_stop_gate._is_tracked_workspace(smokeday_server_code))
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
		from agent_tools import completion, text_claims, text_diagnostics, text_workflow, workflow
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
			'requests': [{'id': 'req-1', 'text': '\u041f\u0440\u0438\u0432\u0435\u0442'}],
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
	def test_v2_filesystem_auto_detection_journals_context_provenance_and_migration(self):
		os_demo = Path('C:/work/clients/smokeday.com--new')
		if os_demo.is_dir():
			os_pp = pr.project_paths(os_demo)
			self.assertEqual(os_pp.profile, 'v2')
			self.assertEqual(os_pp.fs_version, 2)
			self.assertEqual(os_pp.manual_kb_dir, (os_demo / '\U0001f56e').resolve())
			self.assertEqual(os_pp.context_output, (os_demo / '\u2c0f/\u227b/\u2659/Context/output/Context.md').resolve())
			self.assertEqual(os_pp.path('journal_req_dir'), (os_demo / '\ua66e/\u227b').resolve())
			self.assertEqual(os_pp.path('journal_res_dir'), (os_demo / '\ua66e/\u227a').resolve())
			nested_sub = os_demo / '\u2c0f/\u227a/\U0001f582/Nexcess/\ua66e'
			if nested_sub.exists():
				self.assertEqual(pr.resolve_project_root(nested_sub), os_demo.resolve())
		v2_proj = self.root / 'v2_proj'
		(v2_proj / '\U0001f56e').mkdir(parents=True)
		(v2_proj / '\u2c0f/\u227b/\u2655/\u26ef/.git').mkdir(parents=True)
		(v2_proj / '\ua616/KB/Evidence').mkdir(parents=True)
		self.put('v2_proj/readme.md', '# V2 Software Project  \n')
		self.put('v2_proj/\ua616/KB/Spec.md', '# Spec  \nVerified specification sentence.  \n')
		self.put('v2_proj/\ua616/KB/Evidence/raw.md', '# Raw  \nExcluded from Context.md.  \n')
		v2_pp = pr.project_paths(v2_proj)
		self.assertEqual(v2_pp.profile, 'v2_software')
		self.assertEqual(v2_pp.fs_version, 2)
		self.assertEqual(v2_pp.path('idea_dir'), (v2_proj / '.idea').resolve())
		self.assertEqual(v2_pp.path('server_deliverables_dir'), (v2_proj / '\u2c0f/\u227b/\u2655/\u26ef/\U0001d412').resolve())
		self.assertEqual(v2_pp.path('website_deliverables_dir'), (v2_proj / '\u2c0f/\u227b/\u2655/\u26ef/\U0001d416').resolve())
		self.assertIn('/\u2c3f/\u227b/\u2655/', v2_pp.deliverable_segments)
		self.assertTrue(git_gate.GitRepoGate(v2_proj / '\u2c0f/\u227b/\u2655/\u26ef').is_issue_tracked())
		v2_multi = self.root / 'v2_multi'
		(v2_multi / '\U0001f56e').mkdir(parents=True)
		(v2_multi / '.git').mkdir(parents=True)
		v2_srv = v2_multi / '\u2c0f/\u227b/\u2655/\u26ef/\U0001d412'
		v2_web = v2_multi / '\u2c0f/\u227b/\u2655/\u26ef/\U0001d416/example.com/2026-10-26/\u26ef'
		v2_mod = v2_web / 'vendor/example/core'
		v2_db = v2_multi / '\u2c0f/\u227b/\u2655/\u26ef/\U0001d416/example.com/2026-10-26/db'
		for repo_p in (v2_srv, v2_web, v2_mod):
			(repo_p / '.git').mkdir(parents=True)
		v2_db.mkdir(parents=True)
		self.assertEqual(pr.project_paths(v2_multi).profile, 'v2')
		self.assertEqual(pr.canonicalize_root_dir(v2_srv), v2_multi.resolve())
		self.assertEqual(pr.canonicalize_root_dir(v2_web), v2_multi.resolve())
		self.assertEqual(pr.canonicalize_root_dir(v2_mod), v2_multi.resolve())
		self.assertEqual(pr.canonicalize_root_dir(v2_db), v2_db.resolve())
		self.assertTrue(git_gate.GitRepoGate(v2_srv).is_issue_tracked())
		self.assertTrue(git_gate.GitRepoGate(v2_web).is_issue_tracked())
		self.assertTrue(git_gate.GitRepoGate(v2_mod).is_issue_tracked())
		self.assertFalse(git_gate.GitRepoGate(v2_multi).is_issue_tracked())
		(v2_proj / '\ua616/data/turns').mkdir(parents=True, exist_ok=True)
		(v2_proj / '\ua616/data/turns/t1.json').write_text(json.dumps({'status': 'open', 'budget_check': {'graceful_checkpoint_required': True, 'continuation_saved': False}}), encoding='utf-8')
		self.assertIsNotNone(check_markdown_slop._check_turn_budget_gate(v2_proj, v2_proj / '\u2c0f/\u227b/\u2655/\U0001f582/Letters/1.md'))
		self.assertIsNone(check_markdown_slop._check_turn_budget_gate(v2_proj, v2_proj / '\u2c0f/\u227b/\u2655/\u26ef/rules/00-scope.md'))
		j_dir = journal.resolve_journal_dir(v2_proj)
		self.assertEqual(j_dir, (v2_proj / '\ua66e').resolve())
		self.assertEqual(v2_pp.journal_version, 3)
		self.assertEqual(tuple((p.name for p in journal.journal_pair_dirs(j_dir))), ('\u227b', '\u227a'))
		rec = journal.record_step(j_dir, 'First V2 request', 'First V2 response.  \n')
		self.assertTrue((j_dir / '\u227b/1\u201320/1.md').is_file())
		self.assertTrue((j_dir / '\u227a/1\u201320/1.md').is_file())
		self.assertEqual(rec, 1)
		(j_dir / 'req').mkdir()
		(j_dir / 'req/1.md').write_text('x\n', encoding='utf-8')
		with self.assertRaisesRegex(ValueError, 'Conflicting V1'):
			journal.journal_pair_dirs(j_dir)
		(j_dir / 'req/1.md').unlink()
		(j_dir / 'req').rmdir()
		ctx_out, ctx_body, _ = ctx_mod.generate(v2_proj)
		self.assertEqual(ctx_out, (v2_proj / '\u2c0f/\u227b/\u2659/Context/output/Context.md').resolve())
		self.assertIn('Verified specification sentence.', ctx_body)
		self.assertNotIn('Excluded from Context.md.', ctx_body)
		p_res = self.put('v2_proj/\ua66e/\u227a/2.md', 'Model reply  \n')
		p_req = self.put('v2_proj/\ua66e/\u227b/2.md', 'User prompt  \n')
		p_book = self.put('v2_proj/\U0001f56e/Project.md', '# Project  \n')
		p_log = self.put('v2_proj/\u2c0f/\u227a/Logs/Magento/\u2630/system.log', 'ERR 1  \n')
		p_sub_res = self.put('v2_proj/\u2c0f/\u227a/\U0001f582/Nexcess/\ua66e/\u227a/1.md', 'Sub reply  \n')
		p_sub_code = self.put('v2_proj/\u2c0f/\u227a/Logs/Magento/\u26ef/parse.py', 'x = 1\n')
		self.assertEqual(source_grounding.classify_provenance_tier(p_res, v2_proj), 'tier_2')
		self.assertEqual(source_grounding.classify_provenance_tier(p_req, v2_proj), 'tier_0')
		self.assertEqual(source_grounding.classify_provenance_tier(p_book, v2_proj), 'tier_0')
		self.assertEqual(source_grounding.classify_provenance_tier(p_log, v2_proj), 'tier_0')
		self.assertNotEqual(source_grounding.classify_provenance_tier(p_sub_res, v2_proj), 'tier_0')
		self.assertNotEqual(source_grounding.classify_provenance_tier(p_sub_code, v2_proj), 'tier_0')
		mig_proj = self.root / 'mig_proj'
		(mig_proj / '\U0001f56e').mkdir(parents=True)
		(mig_proj / '\ua66e/\u227b').mkdir(parents=True)
		(mig_proj / '\ua66e/\u227a').mkdir(parents=True)
		old_j = mig_proj / '_/\ua66e'
		old_id = admission.binding(old_j, ['Migrated request'], 'Migrated response  \n', 'turn-5', ['req-5'])
		proof_payload = {'schema_version': 1, 'kind': 'publication_admission', 'binding': old_id, 'integrity': []}
		proof_bytes = admission._bytes(proof_payload)
		proof_sha = hashlib.sha256(proof_bytes).hexdigest()
		proof_dir = mig_proj / '\ua616/data/publication-admissions'
		proof_dir.mkdir(parents=True)
		(proof_dir / f'{proof_sha}.json').write_bytes(proof_bytes)
		new_id = admission.binding(mig_proj / '\ua66e', ['Migrated request'], 'Migrated response  \n', 'turn-5', ['req-5'])
		ver = admission.verify(
			{'schema_version': 1, 'file': str((mig_proj / f'_/\ua616/data/publication-admissions/{proof_sha}.json').resolve()), 'sha256': proof_sha},
			new_id,
		)
		self.assertEqual(ver['status'], 'verified')
		journal.record_step(mig_proj / '\ua66e', 'Cross-root req 1', 'Cross-root res 1  \n')
		fake_daily = self.root / 'fake_daily'
		fake_state = fake_daily / '\ua616/data'
		fake_state.mkdir(parents=True)
		reloc_su = fake_daily / '2026/10/26/1 - ex.com'
		reloc_sc = self.root / 'fake_clients/ex.com/m/2026-10-26/code'
		(fake_state / 'projects.json').write_text(
			json.dumps({'~01reloc': '2026/10/26/1 - ex.com', '~01missing': '2026/10/26/2 - gone.com'}),
			encoding='utf-8',
		)
		reloc_reg_raw = deepcopy(pr.load_registry().raw)
		reloc_reg_raw['relocations'][reloc_su.as_posix()] = mig_proj.as_posix()
		reloc_reg_raw['relocations'][reloc_sc.as_posix()] = reloc_su.as_posix()
		reloc_reg_file = self.put('reloc-paths.json', json.dumps(reloc_reg_raw))
		with patch.dict(os.environ, {'HARNESS_PATHS_FILE': str(reloc_reg_file)}):
			pr.clear_registry_cache()
			self.assertEqual(pr.canonicalize_root_dir(reloc_su), mig_proj.resolve())
			self.assertEqual(pr.canonicalize_root_dir(reloc_sc), mig_proj.resolve())
			self.assertTrue(journal.same_journal_identity(reloc_su / '\ua66e/1 - \u0410\u043d\u0430\u043b\u0438\u0437', mig_proj / '\ua66e'))
			self.assertEqual(
				journal.resolve_migrated_step_file(reloc_su / '\ua66e/1 - \u0410\u043d\u0430\u043b\u0438\u0437/res/1.md'),
				(mig_proj / '\ua66e/\u227a/1\u201320/1.md').resolve(),
			)
			su_id = admission.binding(reloc_su / '\ua66e/1 - \u0410\u043d\u0430\u043b\u0438\u0437', ['Migrated request'], 'Migrated response  \n', 'turn-6', ['req-6'])
			su_proof_bytes = admission._bytes({'schema_version': 1, 'kind': 'publication_admission', 'binding': su_id, 'integrity': []})
			su_sha = hashlib.sha256(su_proof_bytes).hexdigest()
			(proof_dir / f'{su_sha}.json').write_bytes(su_proof_bytes)
			mig_id6 = admission.binding(mig_proj / '\ua66e', ['Migrated request'], 'Migrated response  \n', 'turn-6', ['req-6'])
			self.assertEqual(
				admission.verify({'schema_version': 1, 'file': str((reloc_su / f'\ua616/data/publication-admissions/{su_sha}.json').resolve()), 'sha256': su_sha}, mig_id6)['status'],
				'verified',
			)
			self.assertEqual(up.resolve_or_create_project_dir('~01reloc', 'ex.com', '2026-10-26', daily_root=fake_daily), mig_proj.resolve())
			with self.assertRaisesRegex(ValueError, 'missing or external'):
				up.resolve_or_create_project_dir('~01missing', 'gone.com', '2026-10-26', daily_root=fake_daily)
		pr.clear_registry_cache()
		v1_job = self.root / 'v1_job'
		v1_agents = v1_job / '.agents'
		(v1_agents / 'rules').mkdir(parents=True)
		stale_code = Path('C:/work/research/provision/code/AI/harness/code')
		for kind in ('rules', 'skills', 'agents'):
			entries = [{'path': (stale_code / kind).as_posix()}]
			if 'rules' == kind:
				entries.append({'path': 'rules'})
			(v1_agents / f'{kind}.json').write_text(json.dumps({'entries': entries}), encoding='utf-8')
		self.assertFalse(up.check_configuration(v1_job)['valid'])
		up.configure_project(v1_job)
		self.assertTrue(up.check_configuration(v1_job)['valid'])
	def test_v1_journal_only_upgrade_preserves_v1_project_layout_and_historical_receipts(self):
		v1_upw = self.root / 'v1_upwork_legacy'
		self.put('v1_upwork_legacy/\ua616/project.json', json.dumps({'job_id': '~012345'}))
		self.put('v1_upwork_legacy/KB/Project.md', '# Project  \n')
		self.put('v1_upwork_legacy/.md', '# Overview  \n')
		self.put('v1_upwork_legacy/.agents/paths.json', '{\n\t"version": 1,\n\t"profile": "upwork",\n\t"paths": {\n\t\t"journal_dir": "${JOURNAL_ROOT_DIR}/1 - \u0410\u043d\u0430\u043b\u0438\u0437"\n\t}\n}')
		self.put('v1_upwork_legacy/\ua66e/0/Context.md', '# Context  \n')
		old_j = v1_upw / '\ua66e/1 - \u0410\u043d\u0430\u043b\u0438\u0437'
		steps = journal.record_answer(old_j, ['Legacy V1 request'], 'Legacy V1 response  \n', 'turn-v1', ['req-v1-1'])
		self.assertEqual(steps, [1])
		self.assertEqual(pr.project_paths(v1_upw).fs_version, 1)
		self.assertEqual(pr.project_paths(v1_upw).journal_version, 1)
		self.assertEqual(journal.resolve_journal_dir(v1_upw), old_j.resolve())
		upg = journal.ensure_project_journal_upgraded(v1_upw)
		self.assertTrue(upg['upgraded'])
		self.assertEqual(upg['from_version'], 1)
		self.assertEqual(upg['to_version'], 3)
		self.assertTrue(upg['state_migrated'])
		self.assertTrue(upg['overlay_updated'])
		pp_after = pr.project_paths(v1_upw)
		self.assertEqual(pp_after.fs_version, 1)
		self.assertEqual(pp_after.profile, 'upwork')
		self.assertEqual(pp_after.journal_version, 3)
		self.assertEqual(pp_after.manual_kb_dir, (v1_upw / 'KB').resolve())
		self.assertEqual(pp_after.journal_dir, (v1_upw / '\ua66e').resolve())
		self.assertFalse(old_j.exists())
		self.assertTrue((v1_upw / '\ua66e/0/Context.md').is_file())
		self.assertTrue((v1_upw / '\ua66e/\u227b/1\u201320/1.md').is_file())
		self.assertTrue((v1_upw / '\ua66e/\u227a/1\u201320/1.md').is_file())
		self.assertEqual(journal.verify_answer(v1_upw / '\ua66e', ['Legacy V1 request'], 'Legacy V1 response  \n', 'turn-v1', ['req-v1-1']), [1])
		self.assertEqual(journal.resolve_migrated_step_file(old_j / 'res/1.md'), (v1_upw / '\ua66e/\u227a/1\u201320/1.md').resolve())
		dual = self.root / 'v1_dual'
		(dual / 'code/.git').mkdir(parents=True)
		self.put('v1_dual/_/\ua616/paths.json', json.dumps({'version': 1, 'profile': 'dual_repo'}))
		self.put('v1_dual/_/\ua66e/README.md', 'Journal `_/\ua66e/{req,res}`: [q1](req/1.md) [a1](res/1.md) [q25](req/25.md) [a25](res/25.md)\n')
		self.put('v1_dual/_/\ua66e/source/att.txt', 'attachment\n')
		self.put('v1_dual/_/\ua66e/req/1.md', 'Dual req 1')
		self.put('v1_dual/_/\ua66e/res/1.md', '')
		self.put('v1_dual/_/\ua66e/req/25.md', 'Dual req 25')
		self.put('v1_dual/_/\ua66e/res/25.md', 'Dual res 25')
		self.assertEqual(pr.project_paths(dual).journal_version, 1)
		dupg = journal.ensure_project_journal_upgraded(dual)
		self.assertTrue(dupg['upgraded'])
		self.assertTrue(dupg['readme_updated'])
		dpp = pr.project_paths(dual)
		self.assertEqual(dpp.fs_version, 1)
		self.assertEqual(dpp.journal_version, 3)
		self.assertEqual((dual / '_/\ua66e/\u227a/1\u201320/1.md').read_bytes(), b'')
		self.assertEqual((dual / '_/\ua66e/\u227a/21\u201340/25.md').read_text(encoding='utf-8'), 'Dual res 25')
		self.assertTrue((dual / '_/\ua66e/source/att.txt').is_file())
		readme_txt = (dual / '_/\ua66e/README.md').read_text(encoding='utf-8')
		self.assertIn('(\u227b/1\u201320/1.md)', readme_txt)
		self.assertIn('(\u227a/21\u201340/25.md)', readme_txt)
	def test_redirected_userprofile_separates_os_user_home_preserves_sandboxes_and_auto_detects_a6(self):
		from contextlib import closing
		import sqlite3
		import subprocess
		import uuid
		from agent_tools import completion
		from test_turn_completion import wire
		os_home = (self.root / 'Users/alice').resolve()
		roaming = os_home / 'AppData/Roaming'
		a6_home = roaming / 'Antigravity-A6/home'
		for base_h in (os_home, a6_home):
			(base_h / '.gemini/config/projects').mkdir(parents=True, exist_ok=True)
			(base_h / '.gemini/antigravity/conversations').mkdir(parents=True, exist_ok=True)
		a6_env = {'APPDATA': str(roaming), 'USERPROFILE': str(a6_home), 'LOCALAPPDATA': str(os_home / 'AppData/Local')}
		reg_a6 = pr.load_registry(env=a6_env)
		self.assertEqual(reg_a6.resolved_variables['OS_USER_HOME'], os_home.as_posix())
		self.assertEqual(reg_a6.resolved_variables['USER_HOME'], os_home.as_posix())
		self.assertEqual(pr.default_platform_paths('antigravity', registry=reg_a6)['home'], a6_home.as_posix())
		nonstandard_roaming = (self.root / 'custom_sandbox/roaming_alt').resolve()
		nonstandard_home = nonstandard_roaming / 'Antigravity-A6/home'
		reg_sandbox = pr.load_registry(env={'APPDATA': str(nonstandard_roaming), 'USERPROFILE': str(nonstandard_home)})
		self.assertEqual(reg_sandbox.resolved_variables['OS_USER_HOME'], nonstandard_home.as_posix())
		self.assertEqual(reg_sandbox.resolved_variables['USER_HOME'], nonstandard_home.as_posix())
		isolated_user = (self.root / 'isolated_user').resolve()
		reg_outside = pr.load_registry(env={'APPDATA': str(roaming), 'USERPROFILE': str(isolated_user)})
		self.assertEqual(reg_outside.resolved_variables['OS_USER_HOME'], isolated_user.as_posix())
		self.assertEqual(reg_outside.resolved_variables['USER_HOME'], isolated_user.as_posix())
		proj = (self.root / 'a6_tracked_proj').resolve()
		(proj / '\ua616/data').mkdir(parents=True, exist_ok=True)
		(proj / '\ua66e').mkdir(parents=True, exist_ok=True)
		cid = str(uuid.uuid4())
		a6_backend = a6_home / '.gemini/antigravity'
		t_log = a6_backend / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
		t_log.parent.mkdir(parents=True, exist_ok=True)
		t_log.write_text(json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': 'Verify A6 auto-detection.'}) + '\n', encoding='utf-8')
		with closing(sqlite3.connect(a6_backend / 'conversation_summaries.db')) as conn:
			conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT, parent_conversation_id TEXT, workspace_uris TEXT, status TEXT, not_fully_idle INTEGER, killed INTEGER, last_user_input_step_index INTEGER, agent_name TEXT)')
			conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)', (cid, '', json.dumps([proj.as_uri()]), 'CASCADE_RUN_STATUS_RUNNING', 1, 0, 0, 'primary'))
			conn.commit()
		with closing(sqlite3.connect(a6_backend / 'conversations' / f'{cid}.db')) as conn:
			conn.execute('CREATE TABLE steps(idx INTEGER, step_type INTEGER, status INTEGER, step_format INTEGER, step_payload BLOB)')
			conn.execute('INSERT INTO steps VALUES(0, 14, 3, 0, ?)', (wire(19, wire(2, b'Verify A6 auto-detection.')),))
			conn.commit()
		with closing(sqlite3.connect(os_home / '.gemini/antigravity/conversation_summaries.db')) as conn:
			conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT)')
			conn.execute('INSERT INTO conversation_summaries VALUES(?)', (cid,))
			conn.commit()
		with patch.dict(os.environ, a6_env, clear=False):
			pr.clear_registry_cache()
			live_cfg = runtime.settings()
			self.assertEqual(live_cfg['platforms']['antigravity']['instances']['A0']['home'], os_home.as_posix())
			self.assertEqual(live_cfg['platforms']['antigravity']['instances']['A6']['home'], a6_home.as_posix())
			resolved_no_cid = runtime.resolve_antigravity_paths(config=live_cfg)
			self.assertEqual(resolved_no_cid['instance'], 'A6')
			self.assertEqual(Path(resolved_no_cid['backend_dir']).resolve(), a6_backend.resolve())
			resolved_ambig = runtime.resolve_antigravity_paths(conversation_id=cid, config=live_cfg)
			self.assertEqual(resolved_ambig['instance'], 'A6')
			begun = completion.begin(proj, cid, platform='antigravity')
			self.assertEqual(begun['status'], 'open')
			prepared = completion.prepare(proj, 'Verified A6 response without manual instance flag.  \n', cid, platform='antigravity')
			self.assertTrue(prepared['ready'])
		real_roaming = Path(os.environ.get('APPDATA', 'C:/Users/dfedi/AppData/Roaming'))
		real_a6_home = real_roaming / 'Antigravity-A6/home'
		if real_a6_home.is_dir():
			sub_env = {**os.environ, 'USERPROFILE': str(real_a6_home), 'APPDATA': str(real_roaming)}
			proc = subprocess.run([sys.executable, str(runtime.PRIMARY / 'scripts/harness.py'), 'doctor'], env=sub_env, capture_output=True, text=True, encoding='utf-8', check=False)
			self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
			doc_out = json.loads(proc.stdout)
			self.assertTrue(doc_out['valid'], doc_out)
			self.assertNotEqual(doc_out['instances']['A0']['home'], doc_out['instances']['A6']['home'])
	def test_cross_root_relocation_workflow_completion_review_and_antigravity_registration(self):
		from agent_tools import completion, metrics, research, review, text_workflow, workflow
		from agent_tools.platforms import antigravity, codex, request_binding
		old_su = self.root / 'old_proposals/2026/10/26/1 - reloc_shop'
		old_sc = self.root / 'old_clients/reloc_shop/m/2026-10-26/code/_my'
		old_txt = self.root / 'old_text_ws'
		new_txt = (self.root / 'new_text_ws').resolve()
		(new_txt / '\ua616/data').mkdir(parents=True)
		old_txt_id = 'text-' + hashlib.sha256(str(old_txt.resolve()).encode('utf-8')).hexdigest()
		self.put('new_text_ws/\ua616/data/text-project.json', json.dumps({'schema_version': 1, 'kind': 'client_text_workspace', 'project_root': str(old_txt.resolve()), 'id': old_txt_id}))
		new_m = (self.root / 'new_clients/reloc_shop').resolve()
		other_proj = (self.root / 'other_clients/other_shop').resolve()
		other_proj.mkdir(parents=True)
		(new_m / '\U0001f56e').mkdir(parents=True)
		(new_m / '\u2c0f/\u227b/\u2659/Context/output').mkdir(parents=True)
		(new_m / '\ua616/KB/Evidence/Reviews').mkdir(parents=True)
		(new_m / '\ua616/data/turns').mkdir(parents=True)
		(new_m / '\ua66e/\u227b/1\u201320').mkdir(parents=True)
		(new_m / '\ua66e/\u227a/1\u201320').mkdir(parents=True)
		self.put('new_clients/reloc_shop/readme.md', '# Relocated Shop\n')
		self.put('new_clients/reloc_shop/\U0001f56e/Project.md', '# Manual Project\n')
		ctx_file = self.put('new_clients/reloc_shop/\u2c0f/\u227b/\u2659/Context/output/Context.md', '# Context Export\n')
		proj_json = self.put('new_clients/reloc_shop/\ua616/project.json', json.dumps({'job_id': '~029999999999999999999', 'request_date': '2026-10-26'}))
		req_text = 'Analyze shop.  \n'
		res_text = 'Verified relocated shop analysis.  \n'
		req_f = self.put('new_clients/reloc_shop/\ua66e/\u227b/1\u201320/1.md', req_text)
		res_f = self.put('new_clients/reloc_shop/\ua66e/\u227a/1\u201320/1.md', res_text)
		reg_raw = deepcopy(pr.load_registry().raw)
		reg_raw['relocations'][old_su.as_posix()] = new_m.as_posix()
		reg_raw['relocations'][old_sc.as_posix()] = new_m.as_posix()
		reg_raw['relocations'][old_txt.as_posix()] = new_txt.as_posix()
		reg_file = self.put('reloc-cross-paths.json', json.dumps(reg_raw))
		with patch.dict(os.environ, {'HARNESS_PATHS_FILE': str(reg_file)}):
			pr.clear_registry_cache()
			self.assertTrue(pr.same_project_root(str(old_su), new_m))
			self.assertTrue(pr.same_project_root(old_sc, str(new_m)))
			self.assertFalse(pr.same_project_root(str(other_proj), new_m))
			self.assertFalse(pr.same_project_root('relative/path', new_m))
			self.assertFalse(pr.same_project_root(None, new_m))
			wf_payload = {
				'schema_version': 1,
				'project_root': str(old_su),
				'job_id': '~029999999999999999999',
				'legacy': False,
				'stages': {
					'capture': {'status': 'complete', 'inputs': {}, 'outputs': {'\ua616/project.json': workflow.file_hash(proj_json)}},
					'finalize': {'status': 'complete', 'inputs': {}, 'outputs': {'\ua66e/1 - Analysis/res/1.md': workflow.file_hash(res_f), '\ua66e/0/Context.md': workflow.file_hash(ctx_file)}},
				},
				'questions': {},
				'reviews': [],
				'events': [],
				'requests': [],
			}
			self.put('new_clients/reloc_shop/\ua616/data/workflow.json', json.dumps(wf_payload))
			wf_st = workflow.status(new_m)
			self.assertEqual(Path(wf_st['project']).resolve(), new_m)
			wf_engine = workflow.WorkflowStateEngine(new_m)
			self.assertTrue(wf_engine.receipt_current(wf_payload['stages']['finalize']))
			wf_engine.update({'action': 'relocation_touch'}, lambda s: None)
			saved_wf = json.loads((new_m / '\ua616/data/workflow.json').read_text(encoding='utf-8'))
			self.assertEqual(Path(saved_wf['project_root']).resolve(), new_m)
			cand_rel = '\ua616/KB/Evidence/Reviews/cand.md'
			cand_f = self.put('new_clients/reloc_shop/' + cand_rel, res_text)
			cand_bytes = cand_f.read_bytes()
			pkg_body = {
				'schema_version': review.REVIEW_SCHEMA,
				'kind': 'analysis',
				'project_root': str(old_su),
				'job_id': '~029999999999999999999',
				'parent_id': 'parent-1',
				'risk': 'routine',
				'kb_inputs': {},
				'evidence_inputs': {},
				'requests': [{'id': 'req-1', 'text': req_text}],
				'response': {'file': cand_rel, 'sha256': review.digest(cand_bytes), 'bytes': len(cand_bytes)},
				'claims': [],
			}
			pkg_body['subject_sha256'] = review.subject_digest(pkg_body)
			pkg_bytes = review.json_data(pkg_body)
			pkg_sha = review.digest(pkg_bytes)
			pkg_rel = f'\ua616/KB/Evidence/Reviews/{pkg_sha}-inputs.json'
			(new_m / pkg_rel).write_bytes(pkg_bytes)
			env_root, _, env_data, _ = review.read_package_envelope(new_m, pkg_rel, expected_kind='analysis')
			self.assertEqual(env_root, new_m)
			self.assertEqual(env_data['subject_sha256'], pkg_body['subject_sha256'])
			old_abs_pkg = str((old_su / pkg_rel).resolve())
			self.assertEqual(research.inside(new_m, old_abs_pkg), (new_m / pkg_rel).resolve())
			env_root_abs, _, _, _ = review.read_package_envelope(new_m, old_abs_pkg, expected_kind='analysis')
			self.assertEqual(env_root_abs, new_m)
			with self.assertRaises(ValueError):
				research.inside(other_proj, old_abs_pkg)
			codex_rows = [
				(1, {'type': 'response_item', 'payload': {'type': 'function_call', 'call_id': 'c1', 'arguments': f'review-input "{old_abs_pkg}"'}}),
				(2, {'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': 'c1', 'output': json.dumps({'upwork_review_input': 1, 'verified': True, 'reviewer_id': 'rev-1', 'parent_id': 'parent-1', 'project_root': str(old_su), 'package': old_abs_pkg, 'package_sha256': pkg_sha})}}),
			]
			cx_inputs = codex._review_inputs(new_m, codex_rows, 'parent-1', 'rev-1')
			self.assertEqual(len(cx_inputs), 1)
			self.assertEqual(cx_inputs[0]['package_sha256'], pkg_sha)
			rep_rel = f'\ua616/KB/Evidence/Reviews/{pkg_sha}/rep.json'
			(new_m / rep_rel).parent.mkdir(parents=True, exist_ok=True)
			(new_m / rep_rel).write_text(json.dumps({'result': 'approved', 'findings': []}), encoding='utf-8')
			wf_engine.update({'action': 'add_reloc_review'}, lambda s: s['reviews'].append({'reviewer_id': 'rev-1', 'independent': True, 'risk': 'routine', 'report': str((old_su / rep_rel).resolve())}))
			pm = metrics.project_metrics(new_m)
			self.assertEqual(len(pm['reviews']), 1)
			self.assertEqual(pm['reviews'][0]['result'], 'approved')
			self.assertEqual(request_binding.native_project_id(new_txt), old_txt_id)
			bad_txt = (self.root / 'bad_text_ws').resolve()
			(bad_txt / '\ua616/data').mkdir(parents=True)
			self.put('bad_text_ws/\ua616/data/text-project.json', json.dumps({'schema_version': 1, 'kind': 'client_text_workspace', 'project_root': str(bad_txt), 'id': 'text-forged'}))
			with self.assertRaises(ValueError):
				request_binding.native_project_id(bad_txt)
			letter_rel = '\u2c0f/\u227b/\u2655/\U0001f582/Letters/draft.md'
			letter_bytes = b'# Draft Letter\n'
			self.put('new_clients/reloc_shop/' + letter_rel, letter_bytes.decode('utf-8'))
			letter_sha = review.digest(letter_bytes)
			ws_new = text_workflow.ClientTextWorkspace(old_su)
			self.assertEqual(ws_new.root, new_m)
			op_id = 'a' * 32
			op_dir = ws_new.folder / 'operations' / op_id
			op_dir.mkdir(parents=True, exist_ok=True)
			(op_dir / 'base.bin').write_bytes(letter_bytes)
			rec_body = {'schema_version': 1, 'kind': 'baseline_reconciliation', 'root': str(old_su), 'target': letter_rel, 'document_kind': 'letter', 'operation': op_id, 'previous': {'sha256': None, 'kind': 'letter', 'receipt': None}, 'baseline': {'file': f'\ua616/data/texts/operations/{op_id}/base.bin', 'sha256': letter_sha}}
			rec_raw = review.json_data(rec_body)
			rec_rel = f'\ua616/data/texts/operations/{op_id}/{review.digest(rec_raw)}-reconciled.json'
			(new_m / rec_rel).write_bytes(rec_raw)
			(op_dir / 'operation.json').write_bytes(review.json_data({'schema_version': 1, 'id': op_id, 'root': str(old_su), 'target': letter_rel, 'kind': 'letter', 'mode': 'edit', 'changes': 'prose', 'base_sha256': letter_sha, 'base_exists': True, 'reconcile_sha256': letter_sha, 'reconciliation': rec_rel}))
			t_entry = {'sha256': letter_sha, 'kind': 'letter', 'receipt': None, 'reconciliation': rec_rel}
			ws_new.save_index({'schema_version': 1, 'targets': {letter_rel: t_entry}, 'operations': [], 'protected': []})
			snap = text_workflow.integrity_snapshot(new_m, {letter_rel: t_entry})
			snap['root'] = str(old_su)
			self.assertTrue(text_workflow.verify_integrity(snap)['valid'])
			(other_proj / pkg_rel).parent.mkdir(parents=True, exist_ok=True)
			(other_proj / pkg_rel).write_bytes(pkg_bytes)
			with self.assertRaises(ValueError):
				review.read_package_envelope(other_proj, pkg_rel, expected_kind='analysis')
			cid = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
			fake_backend = str((self.root / 'reloc_ag_backend').resolve())
			fake_source = str((self.root / 'reloc_trace.jsonl').resolve())
			turn1_raw = {'turn_id': 't-1', 'start_step': 1, 'final_step': 3, 'completion_step': 3, 'owned': True, 'completed': True, 'aborted': False}
			fake_native_base = {'platform': 'antigravity', 'native_backend': fake_backend, 'conversation_id': cid, 'source_file': fake_source, 'primary': True}
			t1_key = completion._key(fake_native_base, turn1_raw)
			token = 'native-' + t1_key
			req_ids = [f'{cid}-1']
			jdir = new_m / '\ua66e'
			id_bind = admission.binding(jdir, [req_text], res_text, token, req_ids)
			cap = admission.capture([new_m, jdir], [req_text], res_text, id_bind)
			grp_dir = journal.state_dir(jdir) / 'answer-groups'
			grp_dir.mkdir(parents=True, exist_ok=True)
			grp_file = grp_dir / f'{token}.json'
			grp_payload = {
				'version': 1,
				'journal': str(old_su / '\ua66e/1 - Analysis'),
				'turn': token,
				'status': 'complete',
				'steps': [1],
				'tokens': ['tok-1'],
				'request_ids': req_ids,
				'requests': [req_text],
				'response_sha256': hashlib.sha256(res_text.encode('utf-8')).hexdigest(),
				'admission': cap.reference,
			}
			grp_file.write_bytes(completion._json(grp_payload))
			old_grp_str = str(old_su / '\ua616/data/.journal/deadbeef0000111122223333/answer-groups' / f'{token}.json')
			old_res_str = str(old_su / '\ua66e/1 - Analysis/res/1.md')
			res_sha = hashlib.sha256(res_text.encode('utf-8')).hexdigest()
			old_req_obj = {'id': req_ids[0], 'text': req_text, 'native_step': 1, 'project_binding': {'kind': 'antigravity-workspace-uris', 'native_step': 0, 'root': str(old_su)}}
			cur_req_obj = {'id': req_ids[0], 'text': req_text, 'native_step': 1, 'project_binding': {'kind': 'antigravity-workspace-uris', 'native_step': 0, 'root': str(new_m)}}
			rec_base = {'journal_steps': [1], 'response_sha256': res_sha, 'response_file': old_res_str, 'group_file': old_grp_str, 'group_sha256': hashlib.sha256(grp_file.read_bytes()).hexdigest(), 'recorded_at': '2026-10-26T10:00:00+00:00', 'reused_complete_journal_group': False, 'admission': cap.reference}
			exec5_ok = {'verified': True, 'violations': []}
			t1_state = {
				'schema_version': 1,
				'key': t1_key,
				'project_root': str(old_su),
				'platform': 'antigravity',
				'native_backend': fake_backend,
				'conversation_id': cid,
				'native_turn_id': 't-1',
				'native_start_step': 1,
				'requests': [old_req_obj],
				'role': 'primary',
				'journal_required': True,
				'journal': str(old_su / '\ua66e/1 - Analysis'),
				'applicable_rules': {},
				'git_optional_locks_env': '0',
				'exec5_check': exec5_ok,
				'http_fetch_check': exec5_ok,
				'compaction_check': {'verified': True, 'occurred': False},
				'delegation_check': {'verified': True, 'tool_step_count': 2},
				'budget_check': {'verified': True},
				'code_lifecycle_check': {'verified': True, 'touched_repos': {}, 'issues': [], 'violations': []},
				'status': 'delivered',
				'readiness_check': {'verified': True, 'checked_at': '2026-10-26T10:00:00+00:00'},
				'prepared': dict(rec_base),
				'journal_record': dict(rec_base),
				'delivery': {**rec_base, 'verified': True, 'source_file': fake_source, 'final_step': 3, 'completion_step': 3, 'native_response_sha256': res_sha, 'completion_provenance': 'prepared', 'preparation_verified': True, 'exec5_check': exec5_ok, 'verified_at': '2026-10-26T10:00:05+00:00'},
				'recovered_after_delivery': False,
			}
			t1_path = new_m / '\ua616/data/turns' / f'{t1_key}.json'
			t1_path.write_bytes(completion._json(t1_state))
			t1_bytes_before = t1_path.read_bytes()
			turn1_live = {**turn1_raw, 'requests': [cur_req_obj], 'response': res_text}
			turn2_live = {'turn_id': 't-2', 'start_step': 4, 'final_step': None, 'completion_step': None, 'owned': True, 'completed': False, 'aborted': False, 'requests': [{'id': f'{cid}-4', 'text': 'Next request', 'native_step': 4, 'project_binding': {'kind': 'antigravity-workspace-uris', 'native_step': 0, 'root': str(new_m)}}], 'response': ''}
			fake_native = {**fake_native_base, 'active_turn_id': 't-2', 'turns': [turn1_live, turn2_live]}
			with patch('agent_tools.completion._native', return_value=fake_native):
				sync_res = completion.sync(new_m, cid, platform='antigravity')
				self.assertTrue(sync_res['valid'], sync_res)
				self.assertEqual(sync_res['turns'][0]['status'], 'delivered')
				self.assertEqual(t1_path.read_bytes(), t1_bytes_before)
				beg_res = completion.begin(new_m, cid, platform='antigravity')
				self.assertEqual(beg_res['status'], 'open')
			ag_projects = self.root / 'ag_reloc_projects'
			old_proj_rec = {'id': 'reloc-uuid-1', 'name': 'reloc_shop - U.P.2026.10.26', 'projectResources': {'resources': [{'folderUri': old_su.resolve().as_uri()}]}, 'settings': {'keepUserSetting': 42}}
			rec_file = self.put('ag_reloc_projects/reloc-uuid-1.json', json.dumps(old_proj_rec))
			folders_file = self.put('ag_reloc_folders.json', '{"folders":[],"projectFolderMap":{}}')
			reg_receipt = antigravity.register_antigravity_project(new_m, 'reloc_shop', projects_dir=ag_projects, folders_json_path=folders_file)
			self.assertEqual(reg_receipt['project_id'], 'reloc-uuid-1')
			updated_rec = json.loads(rec_file.read_text(encoding='utf-8'))
			self.assertEqual(updated_rec['settings'], {'keepUserSetting': 42})
			self.assertEqual(updated_rec['projectResources']['resources'], [{'folderUri': new_m.as_uri()}])
if '__main__' == __name__:
	unittest.main()
