# 2026-11-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
from contextlib import closing, redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid
from test_agent_tools import SCRIPTS, TemporaryCase
from test_onboarding import source
import check_stop_gate
from agent_tools import cleanup, configuration, journal_watch, metrics, native_profiles as native, registration, runtime, text_diagnostics, upwork_project as up, workflow
from agent_tools.platforms import adapter, antigravity, codex
class RuntimeInstancesTests(TemporaryCase):
	def setUp(self):
		super().setUp()
		self.primary = self.root / 'harness/code'
		(self.primary / 'rules').mkdir(parents=True)
		(self.primary / 'skills/upwork-init').mkdir(parents=True)
		(self.primary / 'agents').mkdir(parents=True)
		(self.primary / 'platforms').mkdir(parents=True)
		self.write_file(self.primary / 'rules/00-scope.md', '---\ntrigger: always_on\n---\n# Scope\nUse canonical sources.  \n')
		self.write_file(self.primary / 'platforms/codex.md', '# Codex\nUse runtime.json.  \n')
		self.write_file(self.primary / 'platforms/antigravity.md', '# Antigravity\nUse runtime.json.  \n')
		self.write_file(self.primary / 'agents/worker.md', '# Worker\nRead evidence.  \n')
		self.write_file(self.primary / 'skills/upwork-init/SKILL.md', '---\nname: upwork-init\ndescription: Init workflow.\n---\nBody.\n')
		self.daily = self.root / 'workspace/proposals/daily'
		self.daily.mkdir(parents=True)
		self.folders = self.root / 'folders.json'
		self.folders.write_text('{"folders":[],"projectFolderMap":{},"collapsedFolders":[]}', encoding='utf-8')
		self.ag_homes = {name: self.root / f'ag/{name}' for name in ('A0', 'A6', 'A7')}
		self.cx_homes = {name: self.root / f'cx/{name}' for name in ('C1', 'C2')}
		for home in self.ag_homes.values():
			(home / '.gemini/config/projects').mkdir(parents=True)
			(home / '.gemini/antigravity').mkdir(parents=True)
		for home in self.cx_homes.values():
			home.mkdir(parents=True)
		self.config = deepcopy(runtime.settings())
		self.config['workspace_root'] = str(self.root / 'workspace')
		self.config['daily_root'] = 'proposals/daily'
		self.config['platforms']['antigravity']['folders_json'] = str(self.folders)
		self.config['platforms']['antigravity']['instances'] = {
			'A0': {'enabled': True, 'primary': True, 'label': 'A0', 'home': str(self.ag_homes['A0']), 'user_data_dir': str(self.root / 'udd/A0')},
			'A6': {'enabled': True, 'primary': False, 'label': 'A6', 'home': str(self.ag_homes['A6']), 'user_data_dir': str(self.root / 'udd/A6')},
			'A7': {'enabled': False, 'primary': False, 'label': 'A7', 'home': str(self.ag_homes['A7'])},
		}
		self.config['platforms']['codex']['instances'] = {
			'C1': {'enabled': False, 'label': 'C1', 'disabled_reason': 'Subscription lapsed', 'home': str(self.cx_homes['C1'])},
			'C2': {'enabled': False, 'default_registration': True, 'label': 'C2', 'disabled_reason': 'Subscription lapsed', 'home': str(self.cx_homes['C2'])},
		}
		self.write_file(self.primary / 'runtime.json', json.dumps(self.config))
	def write_file(self, path, text):
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(text, encoding='utf-8')
		return path
	def sql(self, path, statement, params=()):
		path.parent.mkdir(parents=True, exist_ok=True)
		with closing(sqlite3.connect(path)) as conn:
			conn.execute(statement, params)
			conn.commit()
	def test_live_runtime_declares_environments_instances_enabled_states_and_system_paths(self):
		live = runtime.settings()
		self.assertEqual(set(live['platforms']), {'antigravity', 'codex'})
		self.assertEqual(list(runtime.platform_instances('antigravity', config=live, include_disabled=False)), ['A0', 'A6'])
		self.assertEqual(list(runtime.platform_instances('codex', config=live, include_disabled=False)), [])
		self.assertEqual(list(runtime.platform_instances('codex', config=live, include_disabled=True)), ['C1', 'C2'])
		self.assertTrue(runtime.platform_active('antigravity', config=live))
		self.assertFalse(runtime.platform_active('codex', config=live))
		a6_paths = runtime.instance_paths('A6', config=live)
		self.assertEqual(a6_paths['backend_dir'], 'C:/Users/dfedi/AppData/Roaming/Antigravity-A6/home/.gemini/antigravity')
		self.assertEqual(a6_paths['logs_dir'], 'C:/Users/dfedi/AppData/Roaming/Antigravity-A6/logs')
		c2_paths = runtime.instance_paths('C2', config=live)
		self.assertEqual(c2_paths['sessions_dir'], 'C:/Users/dfedi/AppData/Roaming/Codex-Profile2/sessions')
		self.assertEqual(c2_paths['config_toml'], 'C:/Users/dfedi/AppData/Roaming/Codex-Profile2/config.toml')
	def test_runtime_validation_rejects_invalid_instances_and_dual_homes(self):
		bad = deepcopy(self.config)
		bad['platforms']['antigravity']['enabled'] = 'yes'
		p = self.write_file(self.root / 'bad1.json', json.dumps(bad))
		with self.assertRaisesRegex(ValueError, 'enabled must be a boolean'):
			runtime.settings(p)
		bad2 = deepcopy(self.config)
		bad2['platforms']['codex']['instances']['C1']['enabled'] = 0
		p2 = self.write_file(self.root / 'bad2.json', json.dumps(bad2))
		with self.assertRaisesRegex(ValueError, 'enabled must be a boolean'):
			runtime.settings(p2)
		bad3 = deepcopy(self.config)
		bad3['platforms']['codex']['instances']['C3'] = {'enabled': True}
		p3 = self.write_file(self.root / 'bad3.json', json.dumps(bad3))
		with self.assertRaisesRegex(ValueError, 'requires home or system_paths'):
			runtime.settings(p3)
		bad4 = deepcopy(self.config)
		bad4['platforms']['codex']['homes'] = {'C1': str(self.cx_homes['C1'])}
		p4 = self.write_file(self.root / 'bad4.json', json.dumps(bad4))
		with self.assertRaisesRegex(ValueError, 'cannot define both'):
			runtime.settings(p4)
	def test_platform_enabled_false_disables_all_instances_of_environment(self):
		cfg = deepcopy(self.config)
		cfg['platforms']['codex']['enabled'] = False
		cfg['platforms']['codex']['instances']['C2']['enabled'] = True
		self.assertFalse(runtime.platform_active('codex', config=cfg))
		self.assertEqual(runtime.platform_instances('codex', config=cfg, include_disabled=False), {})
		self.assertFalse(runtime.instance_entry('C2', config=cfg)['enabled'])
		with self.assertRaisesRegex(ValueError, 'no enabled instances'):
			runtime.registration_profile_name(config=cfg)
	def test_disabled_codex_is_skipped_in_registration_workflow_cleanup_install_and_diagnostics(self):
		project = Path(up.initialize_upwork_project(source()['job_id'], 'Topic', '2026-10-15', daily_root=self.daily, extracted_data=source(), register_native=False)['project_dir'])
		with patch.object(registration, 'settings', return_value=self.config), patch.object(runtime, 'settings', return_value=self.config):
			reg = registration.register_projects(project, platform='antigravity', registrars={'antigravity': lambda r, l, d: antigravity.register_antigravity_project(r, l, d, projects_dir=self.ag_homes['A0'] / '.gemini/config/projects', folders_json_path=self.folders), 'codex': lambda *a: (_ for _ in ()).throw(AssertionError('Disabled codex must not run'))})
			self.assertTrue(reg['complete'])
			self.assertTrue(reg['all_registered'])
			self.assertEqual(reg['targets'], ['antigravity'])
			status = workflow.registration_status(project)
			self.assertEqual(status['pending_targets'], [])
			self.assertTrue(status['all_registered'])
		installed = native.install_native_profiles(primary=self.primary)
		self.assertTrue(installed['valid'], installed)
		self.assertEqual(set(installed['profiles']), {'A0', 'A6'})
		self.assertEqual(installed['skipped_disabled'], ['A7', 'C1', 'C2'])
		self.assertFalse((self.ag_homes['A7'] / '.gemini/config/rules.json').exists())
		self.assertFalse((self.cx_homes['C1'] / 'AGENTS.md').exists())
		with patch.object(configuration, 'settings', return_value=self.config), patch.object(configuration, 'profile_name', side_effect=ValueError('none')):
			instr = configuration.global_codex_instructions()
			self.assertIn('disabled', instr['profile'])
			self.assertEqual(instr['developer_instructions'], '')
		diag = text_diagnostics.diagnose_sources(project, platform='codex', config=self.config, primary=self.primary)
		self.assertFalse(any((s.get('configured_profile') for s in diag['sources'])))
	def test_cleanup_skips_disabled_codex_and_checks_all_enabled_antigravity_instances(self):
		self.config['platforms']['antigravity']['instances']['A7']['enabled'] = True
		self.write_file(self.primary / 'runtime.json', json.dumps(self.config))
		for iid in ('A0', 'A6', 'A7'):
			self.sql(self.ag_homes[iid] / '.gemini/antigravity/conversation_summaries.db', 'CREATE TABLE conversation_summaries (project_id TEXT, workspace_uris TEXT)')
		old_proj = self.daily / '2026/10/10/1 - EmptyTopic'
		old_proj.mkdir(parents=True)
		(old_proj / 'ꘖ').mkdir()
		(old_proj / 'ꘖ/project.json').write_text(json.dumps({'job_id': '~021111111111', 'initialized': True, 'request_date': '2026-10-10', 'created_at': '2026-10-10T10:00:00+00:00'}), encoding='utf-8')
		(old_proj / '.md').write_text('Empty old project', encoding='utf-8')
		kept_proj = self.daily / '2026/10/10/2 - ActiveInA7'
		kept_proj.mkdir(parents=True)
		(kept_proj / 'ꘖ').mkdir()
		(kept_proj / 'ꘖ/project.json').write_text(json.dumps({'job_id': '~022222222222', 'initialized': True, 'request_date': '2026-10-10', 'created_at': '2026-10-10T10:00:00+00:00'}), encoding='utf-8')
		(kept_proj / '.md').write_text('Active only in A7', encoding='utf-8')
		with patch.object(antigravity, 'platform_instances', side_effect=lambda p, **kw: runtime.platform_instances(p, config=self.config, **kw)), patch.object(antigravity, 'platform_settings', return_value=self.config['platforms']['antigravity']), patch.object(runtime, 'settings', return_value=self.config):
			reg_empty = antigravity.register(old_proj, 'EmptyTopic', '2026-10-10')
			reg_kept = antigravity.register(kept_proj, 'ActiveInA7', '2026-10-10')
		self.assertEqual(set(reg_empty['instances']), {'A0', 'A6', 'A7'})
		self.assertEqual(len({v['project_id'] for v in reg_empty['instances'].values()}), 1)
		self.sql(self.ag_homes['A7'] / '.gemini/antigravity/conversation_summaries.db', 'INSERT INTO conversation_summaries VALUES (?,?)', (reg_kept['project_id'], '[]'))
		res = cleanup.cleanup_projects(apply=True, daily_root=self.daily, config=self.config, control=lambda req: (_ for _ in ()).throw(AssertionError('Disabled Codex must not invoke shared_control')))
		self.assertTrue(res['complete'], res)
		self.assertEqual(res['active_instances'], {'antigravity': ['A0', 'A6', 'A7'], 'codex': []})
		self.assertEqual(res['skipped_disabled_instances'], {'codex': ['C1', 'C2']})
		self.assertEqual(res['counts']['removed'], 1)
		self.assertEqual(res['counts']['preserved'], 1)
		for iid in ('A0', 'A6', 'A7'):
			self.assertFalse(Path(reg_empty['instances'][iid]['project_file']).exists())
			self.assertTrue(Path(reg_kept['instances'][iid]['project_file']).exists())
	def test_single_enabled_codex_instance_works_with_shared_catalog_superset(self):
		self.config['platforms']['codex']['instances']['C2']['enabled'] = True
		self.sql(self.cx_homes['C2'] / 'state_5.sqlite', 'CREATE TABLE threads (id TEXT, project_id TEXT, cwd TEXT, archived INTEGER)')
		with patch.object(runtime, 'settings', return_value=self.config):
			self.assertEqual(runtime.registration_profile_name(), 'C2')
			self.assertTrue(runtime.platform_active('codex'))
		catalog = {'projects': {}, 'profiles': {'C1': {'bindings': {}}, 'C2': {'bindings': {}}}}
		self.assertEqual(cleanup.catalog_projects(catalog, self.daily / '2026/10/10/1 - Any', {'C2': self.cx_homes['C2']}), [])
	def test_future_environment_claude_code_is_supported_without_roles_or_adapters(self):
		cc_home = self.root / 'claude/home'
		(cc_home / 'projects').mkdir(parents=True)
		(cc_home / 'sessions').mkdir(parents=True)
		self.write_file(cc_home / 'settings.json', '{}')
		self.config['platforms']['claude_code'] = {
			'enabled': True,
			'label': 'Claude Code',
			'surface': 'claude-code-cli',
			'capabilities': ['handoff', 'trace_audit'],
			'instances': {
				'CC1': {
					'enabled': True,
					'label': 'Claude Code Main',
					'home': str(cc_home),
					'system_paths': {
						'home': str(cc_home),
						'settings_json': str(cc_home / 'settings.json'),
						'projects_dir': str(cc_home / 'projects'),
						'sessions_dir': str(cc_home / 'sessions'),
					},
				}
			},
		}
		self.write_file(self.primary / 'runtime.json', json.dumps(self.config))
		with patch.object(runtime, 'settings', return_value=self.config), patch.object(up, 'settings', return_value=self.config), patch.object(up, 'platform_settings', side_effect=lambda p=None: self.config['platforms'][p or 'claude_code']), patch.object(Path, 'home', return_value=self.ag_homes['A0']):
			installed = native.install_native_profiles(primary=self.primary)
			self.assertTrue(installed['valid'], installed)
			inv = runtime.all_instances(config=self.config, check_exists=True)
			self.assertIn('claude_code', inv['enabled_environments'])
			self.assertTrue(inv['environments']['claude_code']['instances']['CC1']['paths_exist']['settings_json'])
			with runtime.using('claude_code'):
				doc = up.doctor(primary=self.primary)
				self.assertEqual(doc['resolved_role_defaults'], {})
				self.assertIn('CC1', doc['instances'])
			with self.assertRaisesRegex(ValueError, 'No native adapter implemented'):
				adapter('claude_code')
	def test_cross_instance_handoff_and_audit_resolve_antigravity_and_disabled_codex_traces(self):
		cid_a6 = str(uuid.uuid4())
		cid_c1 = str(uuid.uuid4())
		a6_backend = self.ag_homes['A6'] / '.gemini/antigravity'
		a6_log = a6_backend / 'brain' / cid_a6 / '.system_generated/logs/transcript_full.jsonl'
		self.write_file(a6_log, json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': 'Continue project after limit.'}) + '\n' + json.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': 'Resumed cleanly.', 'tool_calls': [{'id': 't1', 'name': 'search_web', 'args': {'query': 'dup'}}]}) + '\n' + json.dumps({'step_index': 2, 'type': 'PLANNER_RESPONSE', 'content': 'Done.', 'tool_calls': [{'id': 't2', 'name': 'search_web', 'args': {'query': 'dup'}}]}) + '\n')
		self.sql(a6_backend / 'conversations' / f'{cid_a6}.db', 'CREATE TABLE steps(idx INTEGER, step_type INTEGER, status INTEGER, metadata BLOB)')
		self.sql(a6_backend / 'conversations' / f'{cid_a6}.db', 'INSERT INTO steps VALUES (0, 14, 3, ?)', (b'',))
		self.sql(a6_backend / 'conversations' / f'{cid_a6}.db', 'CREATE TABLE gen_metadata(idx INTEGER, data BLOB, size INTEGER)')
		self.sql(a6_backend / 'conversations' / f'{cid_a6}.db', 'INSERT INTO gen_metadata VALUES (0, ?, 10)', (b'\x0a\x0a\x9a\x01\x06m_test',))
		c1_trace = self.cx_homes['C1'] / 'sessions' / f'rollout-{cid_c1}.jsonl'
		self.write_file(c1_trace, json.dumps({'type': 'session_meta', 'payload': {'id': cid_c1, 'cwd': str(self.root)}}) + '\n' + json.dumps({'type': 'token_usage_record', 'payload': {'turn_id': 't1', 'response_id': 'r1', 'usage': {'input_tokens': 10, 'cached_input_tokens': 2, 'output_tokens': 5}}}) + '\n')
		self.sql(self.cx_homes['C1'] / 'state_5.sqlite', 'CREATE TABLE threads(id TEXT PRIMARY KEY, rollout_path TEXT, agent_path TEXT)')
		self.sql(self.cx_homes['C1'] / 'state_5.sqlite', 'INSERT INTO threads VALUES (?, ?, ?)', (cid_c1, str(c1_trace), None))
		with patch.object(runtime, 'settings', return_value=self.config), patch.object(Path, 'home', return_value=self.ag_homes['A0']):
			matches_a6 = runtime.find_conversation_instance(cid_a6, config=self.config)
			self.assertEqual(len(matches_a6), 1)
			self.assertEqual(matches_a6[0]['id'], 'A6')
			self.assertEqual(Path(runtime.resolve_antigravity_backend(conversation_id=cid_a6, config=self.config)).resolve(), a6_backend.resolve())
			audit_a6 = metrics.summarize_instance(cid_a6)
			self.assertEqual(audit_a6['instance']['id'], 'A6')
			self.assertEqual(audit_a6['repeated_exact_search_queries'], 1)
			audit_c1 = metrics.summarize_instance(cid_c1)
			self.assertEqual(audit_c1['instance']['id'], 'C1')
			self.assertFalse(audit_c1['instance']['enabled'])
			self.assertEqual(audit_c1['surface'], 'codex-ui')
			self.sql(self.ag_homes['A0'] / '.gemini/antigravity/conversation_summaries.db', 'CREATE TABLE conversation_summaries(conversation_id TEXT)')
			self.sql(self.ag_homes['A0'] / '.gemini/antigravity/conversation_summaries.db', 'INSERT INTO conversation_summaries VALUES (?)', (cid_a6,))
			with self.assertRaisesRegex(ValueError, 'pass --instance'):
				runtime.resolve_antigravity_backend(conversation_id=cid_a6, config=self.config)
			self.assertEqual(Path(runtime.resolve_antigravity_backend(instance='A6', conversation_id=cid_a6, config=self.config)).resolve(), a6_backend.resolve())
	def test_cli_instances_and_metrics_commands(self):
		cid = str(uuid.uuid4())
		a6_log = self.ag_homes['A6'] / '.gemini/antigravity/brain' / cid / '.system_generated/logs/transcript_full.jsonl'
		self.write_file(a6_log, json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': 'Hi'}) + '\n' + json.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': 'Ok', 'tool_calls': []}) + '\n')
		with patch.object(runtime, 'settings', return_value=self.config), patch.object(up, 'settings', return_value=self.config), patch.object(Path, 'home', return_value=self.ag_homes['A0']):
			buf = io.StringIO()
			with redirect_stdout(buf):
				rc = up.main(['instances', '--only-enabled'])
			self.assertEqual(rc, 0)
			data = json.loads(buf.getvalue())
			self.assertEqual(list(data['environments']['codex']['instances']), [])
			self.assertEqual(list(data['environments']['antigravity']['instances']), ['A0', 'A6'])
			buf2 = io.StringIO()
			with redirect_stdout(buf2):
				rc2 = up.main(['instances', '--conversation', cid])
			self.assertEqual(rc2, 0)
			data2 = json.loads(buf2.getvalue())
			self.assertTrue(data2['found'])
			self.assertEqual(data2['matches'][0]['id'], 'A6')
			buf3 = io.StringIO()
			with redirect_stdout(buf3):
				rc3 = up.main(['metrics', '--conversation', cid, '--instance', 'A6'])
			self.assertEqual(rc3, 0)
			data3 = json.loads(buf3.getvalue())
			self.assertEqual(data3['instance']['id'], 'A6')
	def test_instance_flag_and_codex_auto_lookup_for_handoff_and_audit(self):
		project = Path(up.initialize_upwork_project(source()['job_id'], 'Topic', '2026-10-15', daily_root=self.daily, extracted_data=source(), register_native=False)['project_dir'])
		self.write_file(self.cx_homes['C2'] / 'config.toml', 'developer_instructions = "Global C2 rules"\n')
		cid_c1 = str(uuid.uuid4())
		c1_trace = self.cx_homes['C1'] / 'sessions/2026/11/02' / f'rollout-{cid_c1}.jsonl'
		self.write_file(c1_trace, json.dumps({'type': 'session_meta', 'payload': {'id': cid_c1, 'cwd': str(project), 'model': 'gpt-5'}}) + '\n' + json.dumps({'type': 'turn_context', 'payload': {'turn_id': 't1', 'cwd': str(project), 'model': 'gpt-5', 'effort': 'high'}}) + '\n' + json.dumps({'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': 't1'}}) + '\n' + json.dumps({'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': f'Work in {project}'}], 'internal_chat_message_metadata_passthrough': {'content_item_kinds': ['user.text'], 'turn_id': 't1'}}}) + '\n' + json.dumps({'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'phase': 'final_answer', 'content': [{'type': 'output_text', 'text': 'Done.'}]}}) + '\n' + json.dumps({'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': 't1', 'last_agent_message': 'Done.'}}) + '\n')
		self.sql(self.cx_homes['C1'] / 'state_5.sqlite', 'CREATE TABLE threads(id TEXT PRIMARY KEY, rollout_path TEXT, agent_path TEXT)')
		self.sql(self.cx_homes['C1'] / 'state_5.sqlite', 'INSERT INTO threads VALUES (?, ?, ?)', (cid_c1, str(c1_trace), None))
		with patch.dict(os.environ, {}, clear=True), patch.object(runtime, 'settings', return_value=self.config), patch.object(configuration, 'settings', return_value=self.config), patch.object(up, 'settings', return_value=self.config):
			buf = io.StringIO()
			with redirect_stdout(buf):
				rc = up.main(['policy-instructions', '--instance', 'C2'])
			self.assertEqual(rc, 0)
			instr = json.loads(buf.getvalue())
			self.assertEqual(instr['profile'], 'C2')
			self.assertEqual(instr['developer_instructions'], 'Global C2 rules')
			answers = codex.native_answers(project, cid_c1)
			self.assertEqual(len(answers['turns']), 1)
			self.assertTrue(answers['turns'][0]['completed'])
			meta = metrics.native_executor_metadata(project, cid_c1)
			self.assertEqual(meta['surface'], 'codex-ui')
			self.assertEqual(meta['observed']['model'], 'gpt-5')
			reqs = metrics.native_requests(project, cid_c1)
			self.assertEqual(reqs[0]['surface'], 'codex-ui')
		with patch.dict(os.environ, {'CODEX_HOME': str(self.root / 'unknown')}, clear=True), patch.object(runtime, 'settings', return_value=self.config):
			with self.assertRaisesRegex(ValueError, 'recognized CODEX_HOME'):
				codex.native_executor_metadata(project, cid_c1)
	def test_all_disabled_and_claude_code_only_environment_without_antigravity_or_codex(self):
		disabled_cfg = deepcopy(self.config)
		for plat in disabled_cfg['platforms'].values():
			for inst in plat['instances'].values():
				inst['enabled'] = False
		with patch.object(runtime, 'settings', return_value=disabled_cfg), patch.object(up, 'settings', return_value=disabled_cfg), patch.object(native, 'settings', return_value=disabled_cfg), patch.object(Path, 'home', return_value=self.root / 'other-home'):
			installed = native.install_native_profiles(primary=self.primary)
			self.assertTrue(installed['valid'], installed)
			self.assertEqual(installed['profiles'], {})
			self.assertEqual(installed['skipped_disabled'], ['A0', 'A6', 'A7', 'C1', 'C2'])
			doc = up.doctor(primary=self.primary)
			self.assertTrue(doc['valid'], doc)
			self.assertEqual(doc['enabled_environments'], [])
			self.assertEqual(doc['global_customizations']['profiles'], {})
		cc_home = self.root / 'claude/home'
		(cc_home / 'projects').mkdir(parents=True)
		(cc_home / 'sessions').mkdir(parents=True)
		self.write_file(cc_home / 'settings.json', '{}')
		cc_only = {
			'version': 2,
			'workspace_root': str(self.root / 'workspace'),
			'timezone': 'Europe/Istanbul',
			'daily_root': 'proposals/daily',
			'registration': {'targets': []},
			'platforms': {
				'claude_code': {
					'enabled': True,
					'label': 'Claude Code',
					'surface': 'claude-code-cli',
					'capabilities': ['handoff', 'trace_audit'],
					'instances': {'CC1': {'enabled': True, 'home': str(cc_home), 'system_paths': {'home': str(cc_home), 'settings_json': str(cc_home / 'settings.json')}}},
				}
			},
		}
		cc_primary = self.root / 'cc_primary'
		(cc_primary / 'rules').mkdir(parents=True)
		(cc_primary / 'skills/upwork-init').mkdir(parents=True)
		(cc_primary / 'agents').mkdir(parents=True)
		self.write_file(cc_primary / 'rules/00-scope.md', '---\ntrigger: always_on\n---\n# Scope\nUse canonical sources.  \n')
		self.write_file(cc_primary / 'skills/upwork-init/SKILL.md', '---\nname: upwork-init\ndescription: Init workflow.\n---\nBody.\n')
		self.write_file(cc_primary / 'runtime.json', json.dumps(cc_only))
		probe = subprocess.run([sys.executable, '-c', f'import sys; sys.path.insert(0, {str(SCRIPTS)!r}); from pathlib import Path; import agent_tools.runtime as rt; rt.PRIMARY = Path({str(cc_primary)!r}); from agent_tools import native_profiles as np, upwork_project as up; from agent_tools.platforms import antigravity as ag; assert rt.platform_name() == "claude_code"; assert ag.ANTIGRAVITY_FOLDERS_JSON is None; doc = up.doctor(primary=Path({str(cc_primary)!r})); inst = np.install_native_profiles(primary=Path({str(cc_primary)!r})); assert doc["valid"] and inst["valid"] and list(doc["instances"]) == ["CC1"], (doc, inst)'], capture_output=True, text=True, timeout=30)
		self.assertEqual(probe.returncode, 0, probe.stderr + probe.stdout)
		with patch.object(runtime, 'settings', return_value=cc_only):
			cln = cleanup.cleanup_projects(apply=False, daily_root=self.daily, config=cc_only)
			self.assertTrue(cln['complete'], cln)
			self.assertEqual(cln['active_instances'], {'antigravity': [], 'codex': []})
	def test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths(self):
		project = Path(up.initialize_upwork_project(source()['job_id'], 'Topic', '2026-10-15', daily_root=self.daily, extracted_data=source(), register_native=False)['project_dir'])
		parent_id = str(uuid.uuid4())
		child_id = str(uuid.uuid4())
		a6_backend = self.ag_homes['A6'] / '.gemini/antigravity'
		self.sql(a6_backend / 'conversation_summaries.db', 'CREATE TABLE conversation_summaries(conversation_id TEXT, parent_conversation_id TEXT, agent_name TEXT)')
		self.sql(a6_backend / 'conversation_summaries.db', 'INSERT INTO conversation_summaries VALUES (?, ?, ?)', (parent_id, '', 'primary'))
		self.sql(a6_backend / 'conversation_summaries.db', 'INSERT INTO conversation_summaries VALUES (?, ?, ?)', (child_id, parent_id, 'self'))
		self.sql(self.ag_homes['A0'] / '.gemini/antigravity/conversation_summaries.db', 'CREATE TABLE conversation_summaries(conversation_id TEXT, parent_conversation_id TEXT, agent_name TEXT)')
		self.sql(self.ag_homes['A0'] / '.gemini/antigravity/conversation_summaries.db', 'INSERT INTO conversation_summaries VALUES (?, ?, ?)', (child_id, parent_id, 'self'))
		pkg_rel = 'ꘖ/KB/Evidence/Reviews/pkg.json'
		self.write_file(project / pkg_rel, '{}')
		prompt = f'Review package: {pkg_rel}'
		parent_rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': '/upwork-init https://upwork.com/jobs/' + source()['job_id']}, {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'self', 'Model': 'inherit', 'Prompt': prompt}]}}]}, {'step_index': 2, 'type': 'GENERIC', 'content': f'Spawned {child_id}'}]
		review_json = json.dumps({'verdict': 'approved', 'findings': []})
		child_rows = [{'step_index': 0, 'type': 'SYSTEM_MESSAGE', 'content': prompt}, {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': review_json, 'tool_calls': []}]
		self.write_file(a6_backend / 'brain' / parent_id / '.system_generated/logs/transcript_full.jsonl', '\n'.join((json.dumps(r) for r in parent_rows)) + '\n')
		self.write_file(a6_backend / 'brain' / child_id / '.system_generated/logs/transcript_full.jsonl', '\n'.join((json.dumps(r) for r in child_rows)) + '\n')
		for cid in (parent_id, child_id):
			db_p = a6_backend / 'conversations' / f'{cid}.db'
			self.sql(db_p, 'CREATE TABLE steps(idx INTEGER, step_type INTEGER, status INTEGER, metadata BLOB)')
			self.sql(db_p, 'INSERT INTO steps VALUES (0, 14, 3, ?)', (b'',))
			self.sql(db_p, 'INSERT INTO steps VALUES (1, 15, 3, ?)', (b'',))
			self.sql(db_p, 'CREATE TABLE gen_metadata(idx INTEGER, data BLOB, size INTEGER)')
			self.sql(db_p, 'INSERT INTO gen_metadata VALUES (0, ?, 10)', (b'\x0a\x0a\x9a\x01\x06m_same',))
		with patch.object(runtime, 'settings', return_value=self.config), patch.object(antigravity, 'settings', return_value=self.config), patch.object(antigravity, 'platform_instances', side_effect=lambda p, **kw: runtime.platform_instances(p, config=self.config, **kw)), patch.object(antigravity, 'platform_settings', side_effect=lambda p=None: self.config['platforms'][p or 'antigravity']):
			proof = antigravity.native_review_proof(project, parent_id, child_id, backend=a6_backend)
			saved_proof = json.loads((project / proof['proof']).read_text(encoding='utf-8'))
			verified = antigravity.verify_native_proof(project, saved_proof)
			self.assertEqual(verified['reviewer_id'], child_id)
			bad = {**saved_proof, 'native_log': str(self.root / 'rogue/transcript_full.jsonl')}
			with self.assertRaisesRegex(ValueError, 'unconfigured or external log path'):
				antigravity.verify_native_proof(project, bad)
		custom_home = self.root / 'custom_ag_home'
		custom_backend = self.root / 'custom_ag_backend'
		custom_brain = self.root / 'custom_ag_brain'
		custom_convs = self.root / 'custom_ag_convs'
		custom_conv_db = self.root / 'custom_ag_db/summaries.db'
		custom_projects_dir = self.root / 'custom_ag_projects'
		custom_cfg = deepcopy(self.config)
		custom_cfg['platforms']['antigravity']['instances']['A9'] = {'enabled': True, 'home': str(custom_home), 'system_paths': {'home': str(custom_home), 'backend_dir': str(custom_backend), 'brain_dir': str(custom_brain), 'conversations_dir': str(custom_convs), 'conversations_db': str(custom_conv_db), 'projects_dir': str(custom_projects_dir)}}
		cid_a9 = str(uuid.uuid4())
		child_a9 = str(uuid.uuid4())
		proj_id_a9 = str(uuid.uuid4())
		a9_project = self.daily / '2026/10/10/2 - CustomPathsA9'
		self.write_file(a9_project / 'ꘖ/project.json', json.dumps({'job_id': source()['job_id']}))
		self.write_file(a9_project / '.md', 'A9 project')
		self.write_file(custom_projects_dir / f'{proj_id_a9}.json', json.dumps({'id': proj_id_a9, 'projectResources': {'resources': [{'workspaceFolderAbsoluteUri': a9_project.resolve().as_uri()}]}}))
		a9_prompt = f'/upwork-init https://upwork.com/jobs/{source()["job_id"]}'
		a9_child_prompt = f'Review package: {pkg_rel}'
		self.write_file(a9_project / pkg_rel, '{}')
		a9_parent_rows = [
			{'step_index': 0, 'type': 'USER_INPUT', 'content': a9_prompt},
			{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'name': 'read_file', 'args': {'Path': 'a.txt'}}, {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'self', 'Model': 'inherit', 'Prompt': a9_child_prompt}]}}]},
			{'step_index': 2, 'type': 'GENERIC', 'content': f'ok Spawned {child_a9}'},
			{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'content': 'Done', 'tool_calls': []},
		]
		a9_child_rows = [{'step_index': 0, 'type': 'SYSTEM_MESSAGE', 'content': a9_child_prompt}, {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': review_json, 'tool_calls': []}]
		a9_log = custom_brain / cid_a9 / '.system_generated/logs/transcript.jsonl'
		a9_child_log = custom_brain / child_a9 / '.system_generated/logs/transcript.jsonl'
		self.write_file(a9_log, '\n'.join((json.dumps(r) for r in a9_parent_rows)) + '\n')
		self.write_file(a9_child_log, '\n'.join((json.dumps(r) for r in a9_child_rows)) + '\n')
		self.sql(custom_conv_db, 'CREATE TABLE conversation_summaries(conversation_id TEXT, parent_conversation_id TEXT, agent_name TEXT, workspace_uris TEXT, project_id TEXT, status TEXT, not_fully_idle INTEGER, killed INTEGER, last_user_input_step_index INTEGER)')
		self.sql(custom_conv_db, 'INSERT INTO conversation_summaries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (cid_a9, '', 'primary', '[]', proj_id_a9, 'CASCADE_RUN_STATUS_IDLE', 0, 0, 0))
		self.sql(custom_conv_db, 'INSERT INTO conversation_summaries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (child_a9, cid_a9, 'self', '[]', proj_id_a9, 'CASCADE_RUN_STATUS_IDLE', 0, 0, -1))
		for cid_row, s_rows in ((cid_a9, [(0, 14, 5, 0, b'', b''), (1, 15, 3, 0, b'', b''), (2, 4, 3, 0, b'', b''), (3, 15, 3, 0, b'', b'')]), (child_a9, [(0, 14, 3, 0, b'', b''), (1, 15, 3, 0, b'', b'')])):
			db_a9 = custom_convs / f'{cid_row}.db'
			self.sql(db_a9, 'CREATE TABLE steps(idx INTEGER, step_type INTEGER, status INTEGER, step_format INTEGER, step_payload BLOB, metadata BLOB)')
			for row_vals in s_rows:
				self.sql(db_a9, 'INSERT INTO steps VALUES (?, ?, ?, ?, ?, ?)', row_vals)
			self.sql(db_a9, 'CREATE TABLE gen_metadata(idx INTEGER, data BLOB, size INTEGER)')
			self.sql(db_a9, 'INSERT INTO gen_metadata VALUES (0, ?, 10)', (b'\x0a\x07\x9a\x01\x04m_a9',))
		matches_a9 = runtime.find_conversation_instance(cid_a9, config=custom_cfg)
		self.assertEqual(len(matches_a9), 1)
		self.assertEqual(matches_a9[0]['id'], 'A9')
		self.assertEqual(Path(matches_a9[0]['trace_file']).resolve(), a9_log.resolve())
		trace_id = str(uuid.uuid4())
		trace_log = custom_brain / trace_id / '.system_generated/logs/transcript.jsonl'
		self.write_file(trace_log, json.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'read_file', 'args': {'Path': 'a.txt'}}]}) + '\n' + json.dumps({'step_index': 2, 'type': 'GENERIC', 'content': 'ok'}) + '\n')
		self.sql(custom_convs / f'{trace_id}.db', 'CREATE TABLE steps(idx INTEGER, status INTEGER)')
		self.sql(custom_convs / f'{trace_id}.db', 'INSERT INTO steps VALUES (2, 3)')
		with patch.object(runtime, 'settings', return_value=custom_cfg), patch.object(antigravity, 'settings', return_value=custom_cfg), patch.object(antigravity, 'platform_instances', side_effect=lambda p, **kw: runtime.platform_instances(p, config=custom_cfg, **kw)), patch.object(antigravity, 'platform_settings', side_effect=lambda p=None: custom_cfg['platforms'][p or 'antigravity']):
			reqs_a9 = antigravity.native_requests(a9_project, cid_a9)
			self.assertEqual(len(reqs_a9), 1)
			self.assertEqual(reqs_a9[0]['text'], a9_prompt)
			ans_a9 = antigravity.native_answers(a9_project, cid_a9)
			self.assertEqual(len(ans_a9['turns']), 1)
			self.assertEqual(ans_a9['turns'][0]['response'], 'Done')
			m_reqs_a9 = metrics.native_requests(a9_project, cid_a9)
			self.assertEqual(m_reqs_a9[0]['text'], a9_prompt)
			m_meta_a9 = metrics.native_executor_metadata(a9_project, cid_a9)
			self.assertEqual(m_meta_a9['observed']['model'], 'm_a9')
			meta_a9 = antigravity.native_executor_metadata(a9_project, cid_a9)
			self.assertEqual(meta_a9['observed']['model'], 'm_a9')
			tr = antigravity.native_tool_trace(a9_project, {'surface': 'antigravity-ui', 'conversation_id': trace_id, 'native_profile_home': str(custom_home), 'step_indices': [1]})
			self.assertEqual(len(tr['events']), 1)
			self.assertEqual(Path(tr['native_log']).resolve(), trace_log.resolve())
			self.assertEqual(Path(tr['native_database']).resolve(), (custom_convs / f'{trace_id}.db').resolve())
			proof_a9 = antigravity.native_review_proof(a9_project, cid_a9, child_a9, instance='A9')
			saved_a9 = json.loads((a9_project / proof_a9['proof']).read_text(encoding='utf-8'))
			saved_a9_no_inst = {k: v for k, v in saved_a9.items() if 'instance' != k}
			self.assertEqual(antigravity.verify_native_proof(a9_project, saved_a9_no_inst)['reviewer_id'], child_a9)
	def test_codex_custom_system_paths_trace_requests_metadata_and_answers(self):
		c9_home = self.root / 'custom_cx_home'
		custom_state = self.root / 'custom_cx_state'
		custom_sessions = self.root / 'custom_cx_sessions'
		c9_home.mkdir(parents=True)
		custom_state.mkdir(parents=True)
		custom_sessions.mkdir(parents=True)
		cfg = deepcopy(self.config)
		cfg['platforms']['codex']['enabled'] = True
		cfg['platforms']['codex']['instances'] = {
			'C9': {'enabled': True, 'label': 'C9', 'home': str(c9_home), 'system_paths': {'home': str(c9_home), 'state_db_glob': str(custom_state / 'state_*.sqlite'), 'sessions_dir': str(custom_sessions), 'config_toml': str(c9_home / 'config.toml')}},
		}
		project = self.daily / '2026/10/10/3 - CustomCodex'
		self.write_file(project / 'ꘖ/project.json', json.dumps({'job_id': source()['job_id']}))
		self.write_file(project / '.md', 'C9 project')
		cid_c9 = str(uuid.uuid4())
		rollout = custom_sessions / '2026/11/18' / f'rollout-{cid_c9}.jsonl'
		prompt_text = f'/upwork-init https://upwork.com/jobs/{source()["job_id"]}'
		c9_rows = [
			{'type': 'session_meta', 'payload': {'id': cid_c9, 'cwd': str(project), 'model': 'gpt-5', 'reasoning_effort': 'high'}},
			{'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': 't1'}},
			{'type': 'turn_context', 'payload': {'turn_id': 't1', 'cwd': str(project), 'model': 'gpt-5', 'effort': 'high'}},
			{'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': prompt_text}], 'internal_chat_message_metadata_passthrough': {'turn_id': 't1', 'content_item_kinds': ['user.text']}}},
			{'type': 'response_item', 'payload': {'type': 'function_call', 'call_id': 'call_1', 'name': 'shell', 'arguments': '{"cmd": "echo hi"}'}},
			{'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': 'call_1', 'output': '{"output": "hi", "metadata": {"exit_code": 0}}'}},
			{'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'phase': 'final_answer', 'content': [{'type': 'output_text', 'text': 'C9 complete'}]}},
			{'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': 't1', 'last_agent_message': 'C9 complete'}},
		]
		self.write_file(rollout, '\n'.join((json.dumps(r) for r in c9_rows)) + '\n')
		state_db = custom_state / 'state_5.sqlite'
		self.sql(state_db, 'CREATE TABLE threads(id TEXT, rollout_path TEXT, project_id TEXT, cwd TEXT, agent_path TEXT)')
		self.sql(state_db, 'INSERT INTO threads VALUES (?, ?, ?, ?, ?)', (cid_c9, str(rollout), 'cx-p1', str(project), ''))
		with patch.object(runtime, 'settings', return_value=cfg), patch.object(codex, 'platform_settings', side_effect=lambda p=None: cfg['platforms'][p or 'codex']), patch.object(codex, 'extract_platform_homes', side_effect=lambda *a, **kw: runtime.extract_platform_homes(*a, **kw)):
			reqs = codex.native_requests(project, cid_c9, instance='C9')
			self.assertEqual(reqs[0]['text'], prompt_text)
			ans = codex.native_answers(project, cid_c9)
			self.assertEqual(len(ans['turns']), 1)
			self.assertEqual(ans['turns'][0]['response'], 'C9 complete')
			meta = codex.native_executor_metadata(project, cid_c9, instance='C9')
			self.assertEqual(meta['observed'], {'model': 'gpt-5', 'effort': 'high'})
			tr = codex.native_tool_trace(project, {'surface': 'codex-ui', 'conversation_id': cid_c9, 'instance': 'C9', 'call_ids': ['call_1']})
			self.assertEqual(Path(tr['native_log']).resolve(), rollout.resolve())
			self.assertEqual(len(tr['events']), 1)
			rogue_cid = str(uuid.uuid4())
			rogue_rollout = c9_home / 'sessions' / f'rollout-{rogue_cid}.jsonl'
			self.write_file(rogue_rollout, json.dumps({'type': 'session_meta', 'payload': {'id': rogue_cid}}) + '\n')
			self.sql(state_db, 'INSERT INTO threads VALUES (?, ?, ?, ?, ?)', (rogue_cid, str(rogue_rollout), 'cx-p1', str(project), ''))
			with self.assertRaisesRegex(ValueError, 'outside the selected profile sessions'):
				codex.native_tool_trace(project, {'surface': 'codex-ui', 'conversation_id': rogue_cid, 'instance': 'C9', 'call_ids': ['call_1']})
	def test_cleanup_custom_system_paths_stop_gate_and_claude_code_only_extensibility(self):
		custom_home = self.root / 'cleanup_ag_home'
		custom_backend = self.root / 'cleanup_ag_backend'
		custom_brain = self.root / 'cleanup_ag_brain'
		custom_convs = self.root / 'cleanup_ag_convs'
		custom_conv_db = self.root / 'cleanup_ag_db/summaries.db'
		custom_projects_dir = self.root / 'cleanup_ag_projects'
		custom_home.mkdir(parents=True)
		custom_backend.mkdir(parents=True)
		custom_brain.mkdir(parents=True)
		custom_convs.mkdir(parents=True)
		custom_projects_dir.mkdir(parents=True)
		c9_home = self.root / 'cleanup_cx_home'
		custom_state = self.root / 'cleanup_cx_state'
		c9_home.mkdir(parents=True)
		custom_state.mkdir(parents=True)
		kept_proj = self.daily / '2026/10/10/4 - KeptCustom'
		self.write_file(kept_proj / 'ꘖ/project.json', json.dumps({'job_id': '~027777777777', 'initialized': True, 'request_date': '2026-10-10', 'created_at': '2026-10-10T10:00:00+00:00'}))
		self.write_file(kept_proj / '.md', 'Kept')
		pruned_proj = self.daily / '2026/10/10/5 - PrunedCustom'
		self.write_file(pruned_proj / 'ꘖ/project.json', json.dumps({'job_id': '~026666666666', 'initialized': True, 'request_date': '2026-10-10', 'created_at': '2026-10-10T10:00:00+00:00'}))
		self.write_file(pruned_proj / '.md', 'Pruned')
		self.sql(custom_conv_db, 'CREATE TABLE conversation_summaries (conversation_id TEXT, parent_conversation_id TEXT, project_id TEXT, workspace_uris TEXT)')
		cid_primary = str(uuid.uuid4())
		cid_child = str(uuid.uuid4())
		self.sql(custom_conv_db, 'INSERT INTO conversation_summaries VALUES (?, ?, ?, ?)', (cid_primary, '', 'ag-kept', json.dumps([kept_proj.resolve().as_uri()])))
		self.sql(custom_conv_db, 'INSERT INTO conversation_summaries VALUES (?, ?, ?, ?)', (cid_child, cid_primary, 'ag-kept', '[]'))
		self.sql(custom_state / 'state_5.sqlite', 'CREATE TABLE threads (id TEXT, project_id TEXT, cwd TEXT, archived INTEGER)')
		cfg = deepcopy(self.config)
		cfg['platforms']['antigravity'].pop('folders_json', None)
		cfg['platforms']['antigravity']['instances'] = {'A9': {'enabled': True, 'primary': True, 'home': str(custom_home), 'system_paths': {'home': str(custom_home), 'projects_dir': str(custom_projects_dir), 'backend_dir': str(custom_backend), 'brain_dir': str(custom_brain), 'conversations_dir': str(custom_convs), 'conversations_db': str(custom_conv_db), 'folders_json': str(self.folders)}}}
		cfg['platforms']['codex']['enabled'] = True
		cfg['platforms']['codex']['instances'] = {'C9': {'enabled': True, 'home': str(c9_home), 'system_paths': {'home': str(c9_home), 'state_db_glob': str(custom_state / 'state_*.sqlite'), 'sessions_dir': str(c9_home / 'sessions'), 'config_toml': str(c9_home / 'config.toml')}}}
		with patch.object(antigravity, 'settings', return_value=cfg), patch.object(antigravity, 'platform_instances', side_effect=lambda p, **kw: runtime.platform_instances(p, config=cfg, **kw)), patch.object(antigravity, 'platform_settings', return_value=cfg['platforms']['antigravity']), patch.object(antigravity, 'ANTIGRAVITY_FOLDERS_JSON', None):
			antigravity.register(pruned_proj, 'PrunedCustom', '2026-10-10')
		calls = []
		def fake_control(req):
			calls.append(req)
			if 'shared-catalog' == req['command']:
				return {'projects': {'cx-p': {'id': 'cx-p', 'rootPaths': [pruned_proj.as_posix()]}}, 'profiles': {'C9': {'bindings': {'cx-p': {'desktopId': 'd1'}}}}}
			return {'complete': True}
		res = cleanup.cleanup_projects(apply=True, daily_root=self.daily, config=cfg, control=fake_control)
		self.assertTrue(res['complete'], res)
		by_root = {Path(p['root']).resolve(): p['status'] for p in res['projects']}
		self.assertEqual(by_root[kept_proj.resolve()], 'preserved')
		self.assertEqual(by_root[pruned_proj.resolve()], 'removed')
		cleanup_reqs = [c for c in calls if 'shared-cleanup-project' == c['command']]
		self.assertEqual(Path(cleanup_reqs[0]['antigravity']['database']).resolve(), custom_conv_db.resolve())
		stop_primary_log = custom_brain / cid_primary / '.system_generated/logs/transcript.jsonl'
		self.write_file(stop_primary_log, json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': 'Hi'}) + '\n' + json.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': 'Reply', 'tool_calls': []}) + '\n')
		with patch.object(runtime, 'settings', return_value=cfg):
			d_primary = check_stop_gate.evaluate_stop_payload({'terminationReason': 'NO_TOOL_CALL', 'fullyIdle': True, 'cwd': str(kept_proj), 'sessionId': cid_primary})
			self.assertEqual(d_primary['decision'], 'continue')
			d_child = check_stop_gate.evaluate_stop_payload({'terminationReason': 'NO_TOOL_CALL', 'fullyIdle': True, 'cwd': str(kept_proj), 'sessionId': cid_child, 'transcriptPath': str(stop_primary_log)})
			self.assertEqual(d_child['decision'], 'allow')
		cc_primary = self.root / 'cc_harness/code'
		cc_ws = self.root / 'cc_workspace'
		cc_ws.mkdir(parents=True)
		(cc_primary / 'rules').mkdir(parents=True)
		(cc_primary / 'skills/upwork-init').mkdir(parents=True)
		(cc_primary / 'agents').mkdir(parents=True)
		(cc_primary / 'platforms').mkdir(parents=True)
		self.write_file(cc_primary / 'rules/00-scope.md', '---\ntrigger: always_on\n---\n# Scope\nUse canonical sources.  \n')
		self.write_file(cc_primary / 'skills/upwork-init/SKILL.md', '---\nname: upwork-init\ndescription: Init workflow.\n---\nBody.\n')
		cc_home = self.root / 'cc_home'
		cc_home.mkdir(parents=True)
		cc_cfg = {'version': 2, 'workspace_root': str(cc_ws), 'daily_root': 'proposals/daily', 'timezone': 'Europe/Istanbul', 'platforms': {'claude_code': {'enabled': True, 'label': 'Claude Code', 'instances': {'CC1': {'enabled': True, 'home': str(cc_home), 'system_paths': {'home': str(cc_home)}}}}}}
		self.write_file(cc_primary / 'runtime.json', json.dumps(cc_cfg))
		built = configuration.build_native(cc_ws, primary=cc_primary)
		self.assertTrue(built['valid'], built)
		self.assertFalse((cc_ws / '.codex/config.toml').exists())
		cc_proj = cc_ws / 'proposals/daily/2026/11/18/1 - ClaudeOnly'
		cc_proj.mkdir(parents=True)
		up.configure_project(cc_proj, cc_primary, 'https://upwork.com/jobs/~02', 'ClaudeOnly')
		self.assertFalse((cc_proj / '.codex/config.toml').exists())
		self.assertTrue(up.check_configuration(cc_proj, cc_primary)['valid'])
		diag = text_diagnostics.diagnose_sources(cc_proj, config=cc_cfg, primary=cc_primary)
		self.assertTrue(diag['valid'], diag)
		self.assertEqual(diag['conflicts'], [])
		with patch.object(journal_watch, 'settings', return_value=cc_cfg), patch.object(runtime, 'settings', return_value=cc_cfg):
			binding_cc = {'project_root': str(cc_proj), 'platform': 'claude_code', 'native_backend': str(cc_home), 'conversation_id': str(uuid.uuid4()), 'source_file': str(cc_proj / 'res.md'), 'from_step': 0}
			journal_watch._validate_binding(binding_cc)
			self.assertEqual(len(journal_watch._signature(binding_cc)), 1)
		with patch.object(journal_watch, 'settings', return_value=cfg), patch.object(runtime, 'settings', return_value=cfg):
			sig_a9 = journal_watch._signature({'project_root': str(kept_proj), 'platform': 'antigravity', 'instance': 'A9', 'native_backend': str(custom_backend), 'conversation_id': cid_primary, 'source_file': str(kept_proj / 'res.md'), 'from_step': 0})
			sig_paths = {Path(item[0]).resolve() for item in sig_a9}
			self.assertIn(custom_conv_db.resolve(), sig_paths)
			self.assertIn((custom_convs / f'{cid_primary}.db').resolve(), sig_paths)
	def test_cleanup_per_instance_folders_json_uninitialized_instance_and_stop_gate_a6(self):
		a8_home = self.root / 'ag/A8'
		(a8_home / '.gemini/config/projects').mkdir(parents=True)
		(a8_home / '.gemini/antigravity').mkdir(parents=True)
		cfg = deepcopy(self.config)
		cfg['platforms']['antigravity'].pop('folders_json', None)
		cfg['platforms']['antigravity']['instances'] = {
			'A8': {'enabled': True, 'primary': False, 'home': str(a8_home), 'system_paths': {'home': str(a8_home), 'config_dir': str(a8_home / '.gemini/config'), 'projects_dir': str(a8_home / '.gemini/config/projects'), 'backend_dir': str(a8_home / '.gemini/antigravity'), 'folders_json': str(self.folders)}},
			'A0': {'enabled': True, 'primary': True, 'home': str(self.ag_homes['A0']), 'system_paths': {'home': str(self.ag_homes['A0']), 'config_dir': str(self.ag_homes['A0'] / '.gemini/config'), 'projects_dir': str(self.ag_homes['A0'] / '.gemini/config/projects'), 'backend_dir': str(self.ag_homes['A0'] / '.gemini/antigravity'), 'folders_json': str(self.folders)}},
		}
		self.sql(self.ag_homes['A0'] / '.gemini/antigravity/conversation_summaries.db', 'CREATE TABLE conversation_summaries (project_id TEXT, workspace_uris TEXT)')
		cfg['platforms']['codex']['instances']['C2']['enabled'] = True
		self.sql(self.cx_homes['C2'] / 'state_5.sqlite', 'CREATE TABLE threads (id TEXT, project_id TEXT, cwd TEXT, archived INTEGER)')
		old_proj = self.daily / '2026/10/10/1 - PerInstanceFolders'
		old_proj.mkdir(parents=True)
		(old_proj / 'ꘖ').mkdir()
		(old_proj / 'ꘖ/project.json').write_text(json.dumps({'job_id': '~023333333333', 'initialized': True, 'request_date': '2026-10-10', 'created_at': '2026-10-10T10:00:00+00:00'}), encoding='utf-8')
		(old_proj / '.md').write_text('Per instance folders test', encoding='utf-8')
		with patch.object(antigravity, 'settings', return_value=cfg), patch.object(antigravity, 'platform_instances', side_effect=lambda p, **kw: runtime.platform_instances(p, config=cfg, **kw)), patch.object(antigravity, 'platform_settings', return_value=cfg['platforms']['antigravity']), patch.object(antigravity, 'ANTIGRAVITY_FOLDERS_JSON', None):
			antigravity.register(old_proj, 'PerInstanceFolders', '2026-10-10')
		calls = []
		def fake_control(req):
			calls.append(req)
			if 'shared-catalog' == req['command']:
				return {'projects': {'cx-1': {'id': 'cx-1', 'rootPaths': [old_proj.as_posix()]}}, 'profiles': {'C1': {'bindings': {}}, 'C2': {'bindings': {'cx-1': {'desktopId': 'p1'}}}}}
			return {'complete': True}
		res = cleanup.cleanup_projects(apply=True, daily_root=self.daily, config=cfg, control=fake_control)
		self.assertTrue(res['complete'], res)
		cleanup_reqs = [c for c in calls if 'shared-cleanup-project' == c['command']]
		self.assertTrue(cleanup_reqs)
		self.assertEqual(Path(cleanup_reqs[0]['antigravity']['database']).resolve(), (self.ag_homes['A0'] / '.gemini/antigravity/conversation_summaries.db').resolve())
		cid_a6 = str(uuid.uuid4())
		a6_log = self.ag_homes['A6'] / '.gemini/antigravity/brain' / cid_a6 / '.system_generated/logs/transcript_full.jsonl'
		self.write_file(a6_log, json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': 'Hi'}) + '\n' + json.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': 'Unprepared reply', 'tool_calls': []}) + '\n')
		with patch.object(runtime, 'settings', return_value=self.config), patch.object(Path, 'home', return_value=self.ag_homes['A0']):
			decision = check_stop_gate.evaluate_stop_payload({'terminationReason': 'NO_TOOL_CALL', 'fullyIdle': True, 'cwd': str(old_proj), 'sessionId': cid_a6})
			self.assertEqual(decision['decision'], 'continue')
			self.assertIn('turn-begin', decision['reason'])
if '__main__' == __name__:
	unittest.main()
