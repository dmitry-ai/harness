"""Destructive cleanup regressions run only against isolated native stores."""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, redirect_stdout
from datetime import datetime, timedelta, timezone
import json
import io
from pathlib import Path
from types import SimpleNamespace
import sqlite3
import unittest
from unittest.mock import patch

from test_agent_tools import TemporaryCase
from agent_tools import cleanup, runtime, upwork_project as up
from agent_tools.platforms.antigravity import register_antigravity_project
from test_onboarding import source


class CleanupTests(TemporaryCase):
    def setUp(self):
        super().setUp()
        self.now = datetime(2026, 10, 18, 15, tzinfo=timezone.utc)
        self.config = deepcopy(runtime.settings())
        self.daily = self.root / 'daily'
        self.daily.mkdir()
        self.ag = self.root / 'ag/projects'
        self.backend = self.root / 'ag/backend'
        self.backend.mkdir(parents=True)
        self.folders = self.root / 'ag/folders.json'
        self.folders.write_text('{"folders":[],"projectFolderMap":{},"collapsedFolders":[]}', encoding='utf-8')
        self.config['workspace_root'] = str(self.root)
        self.config['daily_root'] = 'daily'
        homes = {name: str(self.root / name) for name in ('C1', 'C2')}
        self.config['platforms']['codex']['homes'] = homes
        self.config['platforms']['antigravity']['folders_json'] = str(self.folders)
        self.catalog = {'projects': {}, 'profiles': {name: {'bindings': {}} for name in homes}}
        self.connection(self.backend / 'conversation_summaries.db',
            'CREATE TABLE conversation_summaries (project_id TEXT,workspace_uris TEXT)')
        for home in homes.values():
            self.connection(Path(home) / 'state_5.sqlite',
                'CREATE TABLE threads (id TEXT, project_id TEXT,cwd TEXT,archived INTEGER)')
        self.calls = []

    def connection(self, path, sql, params=()):
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path)) as connection:
            connection.execute(sql, params)
            connection.commit()

    def project(self, number=1, age=73):
        root = self.daily / f'2026/10/15/{number} - topic'
        root.mkdir(parents=True)
        (root / 'ꘖ').mkdir()
        (root / 'ꘖ/project.json').write_text(json.dumps({
            'job_id': f'~02123456789{number}', 'initialized': True, 'request_date': '2026-10-15',
            'created_at': (self.now - timedelta(hours=age)).isoformat()}), encoding='utf-8')
        (root / '.md').write_text('Historical client information', encoding='utf-8')
        receipt = register_antigravity_project(root, 'topic', '2026-10-15',
            projects_dir=self.ag, folders_json_path=self.folders)
        ident = 'shared-' + str(number)
        self.catalog['projects'][ident] = {'id': ident, 'name': 'topic', 'rootPaths': [str(root)]}
        for name, profile in self.catalog['profiles'].items():
            profile['bindings'][ident] = {'desktopId': name + '-' + str(number)}
        return root, Path(receipt['project_file']), ident

    def control(self, request):
        self.calls.append(deepcopy(request))
        if request['command'] == 'shared-catalog':
            return deepcopy(self.catalog)
        self.assertEqual(request['command'], 'shared-cleanup-project')
        ident = request['sharedId']
        if request.get('preserve'):
            self.catalog['projects'][ident].pop('deleted', None)
            self.catalog['projects'][ident].pop('cleanupHold', None)
            return {'complete': True, 'status': 'preserved'}
        if request.get('deferCommit'):
            self.catalog['projects'][ident].update(deleted=True, cleanupHold=True)
            return {'complete': True, 'awaiting_commit': True, 'metadata_removed': False}
        del self.catalog['projects'][ident]
        for profile in self.catalog['profiles'].values():
            profile['bindings'].pop(ident)
        return {'complete': True, 'metadata_removed': True, 'removed_folders': ['day']}

    def run_cleanup(self, **kwargs):
        return cleanup.cleanup_projects(config=self.config, ag_directory=self.ag,
            ag_backend=self.backend, now=self.now, control=kwargs.pop('control', self.control), **kwargs)

    def make_legacy(self, number=1, *, old_uri=False):
        root, native, ident = self.project(number)
        (root / 'ꘖ/project.json').unlink()
        agents = root / '.agents'
        (agents / 'rules').mkdir(parents=True)
        for kind in ('rules', 'skills', 'agents'):
            (agents / (kind + '.json')).write_text(json.dumps({'entries': [
                {'path': str(runtime.PRIMARY / kind)}]}), encoding='utf-8')
        url = 'https://upwork.com/jobs/~02123456789' + str(number)
        (agents / 'rules/90-project.md').write_text(f'Целевая вакансия Upwork: `{url}`.\n', encoding='utf-8')
        (root / 'KB').mkdir()
        (root / 'KB/Project.md').write_text(f'# 1. Клиент\nClient\n\n# 2. Текущий проект клиента\n{url}\n', encoding='utf-8')
        if old_uri:
            value = json.loads(native.read_text(encoding='utf-8'))
            value['projectResources']['resources'][0]['folderUri'] = 'file://' + root.as_posix()
            native.write_text(json.dumps(value), encoding='utf-8')
        return root, native, ident

    def archive(self):
        return {str(p.relative_to(self.daily)): p.read_bytes() for p in self.daily.rglob('*') if p.is_file()}

    def test_preview_is_read_only_and_apply_cleans_both_platforms_preserving_entire_archive(self):
        for platform in ('antigravity', 'codex'):
            with self.subTest(platform=platform), runtime.using(platform):
                root, native, ident = self.project(number=len(self.calls) + 1)
                historical = self.daily / 'ꘖ/data/projects.json'
                historical.parent.mkdir(parents=True, exist_ok=True)
                historical.write_text('{"old-client":"historical/path"}', encoding='utf-8')
                before = self.archive()
                native_before, folders_before = native.read_bytes(), self.folders.read_bytes()
                preview = self.run_cleanup()
                self.assertTrue(preview['complete'], preview)
                self.assertEqual(preview['platform'], platform)
                self.assertEqual(preview['counts']['eligible'], 1)
                self.assertEqual(native.read_bytes(), native_before)
                self.assertEqual(self.folders.read_bytes(), folders_before)
                self.assertEqual(self.archive(), before)
                result = self.run_cleanup(apply=True)
                self.assertTrue(result['complete'], result)
                self.assertEqual(result['counts']['removed'], 1)
                self.assertFalse(native.exists())
                self.assertNotIn(ident, self.catalog['projects'])
                self.assertEqual(self.archive(), before)
                self.assertTrue(all(p['status'] == 'already-absent' for p in self.run_cleanup(apply=True)['projects']))

    def test_strict_72_hour_boundary_and_recent_projects_are_preserved(self):
        paths = [self.project(i, age) for i, age in enumerate((71, 72, 72.001), 1)]
        result = self.run_cleanup(apply=True)
        self.assertEqual(result['counts']['recent'], 2)
        self.assertEqual(result['counts']['removed'], 1)
        self.assertTrue(paths[0][1].exists())
        self.assertTrue(paths[1][1].exists())
        self.assertFalse(paths[2][1].exists())

    def test_any_conversation_blocks_both_registrations_including_archived_or_child_cwd(self):
        for number, kind in enumerate(('ag-id', 'ag-cwd', 'C1', 'C2', 'child-cwd'), 1):
            root, native, ident = self.project(number)
            if kind.startswith('ag'):
                self.connection(self.backend / 'conversation_summaries.db',
                    'INSERT INTO conversation_summaries VALUES (?,?)',
                    (native.stem if kind == 'ag-id' else 'other', json.dumps([root.as_uri()]) if kind == 'ag-cwd' else '[]'))
            else:
                profile = kind if kind in ('C1', 'C2') else 'C2'
                self.connection(Path(self.config['platforms']['codex']['homes'][profile]) / 'state_5.sqlite',
                    'INSERT INTO threads VALUES (?,?,?,?)',
                    (str(number), f'{profile}-{number}' if kind != 'child-cwd' else 'other',
                     str(root / 'result') if kind == 'child-cwd' else str(self.root), 1))
        result = self.run_cleanup(apply=True)
        self.assertTrue(result['complete'], result)
        self.assertEqual(result['counts']['preserved'], 5)
        self.assertEqual(len(list(self.ag.glob('*.json'))), 5)
        self.assertFalse(any(c['command'] == 'shared-cleanup-project' for c in self.calls))

    def test_new_conversation_after_preview_is_rechecked_before_any_delete(self):
        root, native, _ = self.project()
        original = cleanup.conversations
        calls = 0
        def changed(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.connection(self.backend / 'conversation_summaries.db',
                    'INSERT INTO conversation_summaries VALUES (?,?)', (native.stem, '[]'))
            return original(*args)
        with patch.object(cleanup, 'conversations', side_effect=changed):
            result = self.run_cleanup(apply=True)
        self.assertEqual(result['counts']['preserved'], 1)
        self.assertTrue(native.exists())

    def test_legacy_age_uses_birthtime_or_end_of_request_day_without_guessing_midnight_creation(self):
        state = {'request_date': '2026-10-15'}
        born = self.now - timedelta(hours=71)
        fake = SimpleNamespace(stat=lambda: SimpleNamespace(st_birthtime=born.timestamp()))
        created, basis = cleanup._age(fake, state, self.config)
        self.assertEqual(created, born)
        self.assertEqual(basis, 'legacy-directory-birthtime')
        without_birth = SimpleNamespace(stat=lambda: SimpleNamespace())
        created, basis = cleanup._age(without_birth, state, self.config)
        self.assertEqual(created.isoformat(), '2026-10-16T00:00:00+03:00')
        self.assertEqual(basis, 'legacy-request-day-upper-bound')

    def test_legacy_init_without_marker_is_discovered_and_old_file_uri_matches_native_registration(self):
        root, native, _ = self.make_legacy(old_uri=True)
        before = self.archive()
        # The temporary directory is young; test at a future instant so the
        # real filesystem birth-time branch passes the same strict age check.
        self.now = datetime.now(timezone.utc) + timedelta(days=4)
        preview = self.run_cleanup()
        self.assertEqual(preview['counts']['eligible'], 1, preview)
        self.assertEqual(preview['projects'][0]['initialization_basis'], 'legacy-manifests-rule-and-kb')
        self.assertEqual(preview['projects'][0]['native_projects']['antigravity'], [native.stem])
        result = self.run_cleanup(apply=True)
        self.assertTrue(result['complete'], result)
        self.assertEqual(result['counts']['removed'], 1)
        self.assertFalse(native.exists())
        self.assertEqual(self.archive(), before)
        self.assertFalse((root / 'ꘖ/project.json').exists())

    def test_file_uri_with_drive_in_authority_is_the_same_local_workspace(self):
        root, _, _ = self.project()
        for uri in ('file://' + root.as_posix(), root.as_uri(), 'file://' + root.as_posix().replace(':', '%3A', 1)):
            self.assertEqual(cleanup.path_key(uri), cleanup.path_key(root))

    def test_legacy_native_id_conversation_preserves_project_with_unrelated_cwd(self):
        root, native, _ = self.make_legacy(old_uri=True)
        self.now = datetime.now(timezone.utc) + timedelta(days=4)
        self.connection(self.backend / 'conversation_summaries.db',
            'INSERT INTO conversation_summaries VALUES (?,?)', (native.stem, '[]'))
        result = self.run_cleanup(apply=True)
        self.assertEqual(result['counts']['preserved'], 1, result)
        self.assertTrue(native.exists())

    def test_legacy_conflicting_job_or_unowned_manifests_never_authorize_deletion(self):
        root, native, _ = self.make_legacy()
        self.now = datetime.now(timezone.utc) + timedelta(days=4)
        kb = root / 'KB/Project.md'
        kb.write_text('# 2. Текущий проект клиента\nhttps://upwork.com/jobs/~099999\n', encoding='utf-8')
        result = self.run_cleanup(apply=True)
        self.assertFalse(result['complete'])
        self.assertEqual(len(result['issues']), 1)
        self.assertTrue(native.exists())

    def test_legacy_discovery_failure_with_conversations_is_preserved_without_an_issue(self):
        for platform in ('antigravity', 'codex'):
            with self.subTest(platform=platform), runtime.using(platform):
                root, native, ident = self.make_legacy(number=len(self.catalog['projects']) + 1)
                (root / '.agents/rules/90-project.md').write_text('Идентификатор / домен проекта: topic.\n', encoding='utf-8')
                if platform == 'antigravity':
                    self.connection(self.backend / 'conversation_summaries.db',
                        'INSERT INTO conversation_summaries VALUES (?,?)', (native.stem, '[]'))
                else:
                    self.connection(Path(self.config['platforms']['codex']['homes']['C2']) / 'state_5.sqlite',
                        'INSERT INTO threads VALUES (?,?,?,?)', ('archived-child', 'unrelated', str(root / 'result'), 1))
                before = self.archive()
                native_before, folders_before = native.read_bytes(), self.folders.read_bytes()
                result = self.run_cleanup(apply=True)
                self.assertTrue(result['complete'], result)
                self.assertEqual(result['issues'], [])
                self.assertEqual(result['discovery']['unresolved_entries'], 0)
                self.assertEqual(result['discovery']['verified_projects'], 0)
                self.assertEqual(result['discovery']['excluded_with_conversations'], len(self.catalog['projects']))
                self.assertEqual(result['counts']['preserved'], len(self.catalog['projects']))
                self.assertEqual(native.read_bytes(), native_before)
                self.assertEqual(self.folders.read_bytes(), folders_before)
                self.assertEqual(self.archive(), before)
                self.assertIn(ident, self.catalog['projects'])
                self.assertFalse(any(c['command'] == 'shared-cleanup-project' for c in self.calls))

    def test_legacy_discovery_failure_without_readable_history_stays_unresolved(self):
        root, native, _ = self.make_legacy()
        (root / '.agents/rules/90-project.md').write_text('Идентификатор / домен проекта: topic.\n', encoding='utf-8')
        (self.backend / 'conversation_summaries.db').unlink()
        result = self.run_cleanup(apply=True)
        self.assertFalse(result['complete'], result)
        self.assertEqual(result['discovery']['unresolved_entries'], 1)
        self.assertEqual(result['discovery']['excluded_with_conversations'], 0)
        self.assertEqual(result['projects'], [])
        self.assertTrue(native.exists())

    def test_legacy_historical_ids_are_compared_in_full_instead_of_their_numeric_prefix(self):
        root, native, _ = self.make_legacy()
        self.now = datetime.now(timezone.utc) + timedelta(days=4)
        first = '~01d46772b31197f41a'
        second = '~01d9f93da4952d012b'
        (root / '.agents/rules/90-project.md').write_text(f'Вакансия: https://upwork.com/jobs/{first}\n', encoding='utf-8')
        for current in (second, first):
            (root / 'KB/Project.md').write_text(f'# 2. Текущий проект клиента\nhttps://upwork.com/jobs/{current}\n', encoding='utf-8')
            result = self.run_cleanup(apply=True)
            self.assertFalse(result['complete'], result)
            self.assertEqual(result['projects'], [])
            self.assertEqual(len(result['issues']), 1)
            self.assertTrue(native.exists())
        manifest = root / '.agents/skills.json'
        manifest.write_text('{"entries":[{"path":"C:/unrelated/skills"}]}', encoding='utf-8')
        result = self.run_cleanup(apply=True)
        self.assertEqual(result['projects'], [])
        self.assertTrue(native.exists())
        self.assertFalse(any(c['command'] == 'shared-cleanup-project' for c in self.calls))

    def test_missing_history_or_invalid_schema_blocks_cleanup(self):
        root, native, _ = self.project()
        database = Path(self.config['platforms']['codex']['homes']['C1']) / 'state_5.sqlite'
        database.unlink()
        result = self.run_cleanup(apply=True)
        self.assertFalse(result['complete'])
        self.assertEqual(result['counts']['blocked'], 1)
        self.assertTrue(native.exists())

    def test_initializing_catalog_is_a_reported_block_without_deleting_anything(self):
        _, native, _ = self.project()
        result = self.run_cleanup(apply=True, control=lambda request: None)
        self.assertFalse(result['complete'])
        self.assertIn('initializing', result['issues'][0]['error'])
        self.assertTrue(native.exists())

    def test_native_unlink_failure_keeps_folders_and_retries_the_exact_ids(self):
        _, native, _ = self.project()
        before = self.folders.read_bytes()
        unlink = Path.unlink
        def denied(path, *args, **kwargs):
            if path == native:
                raise PermissionError('Native project busy')
            return unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', denied):
            result = self.run_cleanup(apply=True)
        self.assertFalse(result['complete'])
        self.assertTrue(native.exists())
        self.assertEqual(self.folders.read_bytes(), before)
        self.assertTrue((self.ag / 'ꘖ/data/cleanup-pending.json').exists())
        result = self.run_cleanup(apply=True)
        self.assertTrue(result['complete'], result)
        self.assertFalse(native.exists())
        self.assertFalse((self.ag / 'ꘖ/data/cleanup-pending.json').exists())

    def test_folders_publication_failure_after_unlink_recovers_without_native_file(self):
        _, native, _ = self.project()
        before = self.folders.read_bytes()
        replace = cleanup.replace_bytes
        def failed(path, payload):
            if path == self.folders:
                raise OSError('Folders write interrupted')
            return replace(path, payload)
        with patch.object(cleanup, 'replace_bytes', side_effect=failed):
            result = self.run_cleanup(apply=True)
        self.assertFalse(result['complete'])
        self.assertFalse(native.exists())
        self.assertEqual(self.folders.read_bytes(), before)
        result = self.run_cleanup(apply=True)
        self.assertTrue(result['complete'], result)
        self.assertEqual(result['counts']['removed'], 1)
        self.assertEqual(json.loads(self.folders.read_text(encoding='utf-8'))['folders'], [])
        self.assertFalse((self.ag / 'ꘖ/data/cleanup-pending.json').exists())

    def test_new_chat_restores_a_partially_held_codex_project(self):
        _, native, ident = self.project()
        self.catalog['projects'][ident].update(deleted=True, cleanupHold=True)
        self.connection(self.backend / 'conversation_summaries.db',
            'INSERT INTO conversation_summaries VALUES (?,?)', (native.stem, '[]'))
        def restore(request):
            if request.get('preserve'):
                self.catalog['projects'][ident].pop('deleted')
                self.catalog['projects'][ident].pop('cleanupHold')
                return {'complete': True, 'status': 'preserved'}
            return self.control(request)
        result = self.run_cleanup(apply=True, control=restore)
        self.assertEqual(result['counts']['preserved'], 1)
        self.assertTrue(result['projects'][0]['recovery']['complete'])
        self.assertNotIn('cleanupHold', self.catalog['projects'][ident])
        self.assertTrue(native.exists())

    def test_chat_after_native_unlink_restores_both_registrations_and_folder_assignment(self):
        _, native, ident = self.project()
        before = self.folders.read_bytes()
        original = cleanup.conversations
        def changed(*args):
            if not native.exists():
                self.connection(self.backend / 'conversation_summaries.db',
                    'INSERT INTO conversation_summaries VALUES (?,?)', (native.stem, '[]'))
            return original(*args)
        with patch.object(cleanup, 'conversations', side_effect=changed):
            result = self.run_cleanup(apply=True)
        self.assertTrue(result['complete'], result)
        self.assertEqual(result['counts']['preserved'], 1)
        self.assertTrue(native.exists())
        self.assertIn(ident, self.catalog['projects'])
        self.assertNotIn('cleanupHold', self.catalog['projects'][ident])
        self.assertEqual(json.loads(self.folders.read_bytes()), json.loads(before))
        self.assertFalse((self.ag / 'ꘖ/data/cleanup-pending.json').exists())

    def test_changed_native_payload_during_final_check_is_never_unlinked(self):
        _, native, _ = self.project()
        original = cleanup.conversations
        count = 0
        def changed(*args):
            nonlocal count
            count += 1
            if count == 4:
                value = json.loads(native.read_text(encoding='utf-8'))
                value['name'] = 'Manually renamed'
                native.write_text(json.dumps(value), encoding='utf-8')
            return original(*args)
        with patch.object(cleanup, 'conversations', side_effect=changed):
            result = self.run_cleanup(apply=True)
        self.assertFalse(result['complete'])
        self.assertTrue(native.exists())
        self.assertEqual(json.loads(native.read_text(encoding='utf-8'))['name'], 'Manually renamed')

    def test_pending_sibling_restores_full_folder_ancestry_after_other_project_pruned_it(self):
        _, first, ident = self.project()
        self.project(2)
        def pending(request):
            if request.get('commit') and request['sharedId'] == ident:
                return {'complete': False, 'status': 'pending'}
            return self.control(request)
        result = self.run_cleanup(apply=True, control=pending)
        self.assertEqual(result['counts']['pending'], 1)
        self.assertEqual(result['counts']['removed'], 1)
        self.assertEqual(json.loads(self.folders.read_bytes())['folders'], [])
        self.connection(self.backend / 'conversation_summaries.db',
            'INSERT INTO conversation_summaries VALUES (?,?)', (first.stem, '[]'))
        result = self.run_cleanup(apply=True)
        self.assertTrue(result['complete'], result)
        self.assertTrue(first.exists())
        value = json.loads(self.folders.read_bytes())
        ids = {n['id'] for n in value['folders']}
        self.assertEqual(len(ids), 5)
        self.assertTrue(all(folder in ids for folder in value['projectFolderMap'].values()))

    def test_pending_codex_keeps_antigravity_and_archive_and_continues_other_projects(self):
        first, native, _ = self.project()
        self.project(2)
        def pending(request):
            if request['command'] == 'shared-cleanup-project' and request['sharedId'] == 'shared-1':
                return {'complete': False, 'offline_profiles': ['C1']}
            return self.control(request)
        before = self.archive()
        result = self.run_cleanup(apply=True, control=pending)
        self.assertFalse(result['complete'])
        self.assertEqual(result['counts']['pending'], 1)
        self.assertEqual(result['counts']['removed'], 1)
        self.assertTrue(native.exists())
        self.assertEqual(self.archive(), before)

    def test_multi_root_projects_and_non_init_projects_are_preserved(self):
        root, native, _ = self.project()
        value = json.loads(native.read_text(encoding='utf-8'))
        value['projectResources']['resources'].append({'folderUri': self.root.as_uri()})
        native.write_text(json.dumps(value), encoding='utf-8')
        manual = self.daily / '2026/10/15/2 - manual'
        manual.mkdir()
        (manual / '.md').write_text('not auto-created', encoding='utf-8')
        result = self.run_cleanup(apply=True)
        self.assertEqual(result['counts']['blocked'], 1)
        self.assertEqual(len(result['projects']), 1)
        self.assertTrue(native.exists())

    def test_only_newly_emptied_folder_ancestors_are_pruned(self):
        value = {'folders': [{'id': 'parent', 'parentId': None}, {'id': 'day', 'parentId': 'parent'},
                             {'id': 'sibling', 'parentId': 'parent'}, {'id': 'unrelated', 'parentId': None}],
                 'projectFolderMap': {'deleted': 'day', 'kept': 'sibling'}, 'collapsedFolders': ['day', 'sibling']}
        self.assertEqual(cleanup.prune_folders(value, ['deleted']), ['day'])
        self.assertEqual({f['id'] for f in value['folders']}, {'parent', 'sibling', 'unrelated'})
        self.assertEqual(value['collapsedFolders'], ['sibling'])
        self.assertEqual(set(cleanup.prune_folders(value, ['kept'])), {'sibling', 'parent'})
        self.assertEqual(value['folders'], [{'id': 'unrelated', 'parentId': None}])

    def test_init_persists_creation_time_and_repeat_never_resets_it(self):
        root = Path(up.initialize_upwork_project(source()['job_id'], 'Topic', '2026-10-15',
            daily_root=self.daily, extracted_data=source(), register_native=False)['project_dir'])
        state = json.loads((root / 'ꘖ/project.json').read_text(encoding='utf-8'))
        self.assertEqual(state['created_by'], 'upwork-init')
        self.assertIsNotNone(datetime.fromisoformat(state['created_at']).tzinfo)
        up.initialize_upwork_project(source()['job_id'], 'Topic', '2026-10-15',
            daily_root=self.daily, extracted_data=source(), register_native=False)
        self.assertEqual(json.loads((root / 'ꘖ/project.json').read_text(encoding='utf-8'))['created_at'], state['created_at'])


class CleanupReportTests(TemporaryCase):
    def test_exact_answer_and_filename_use_the_same_istanbul_time_across_utc_midnight(self):
        body = 'Очистка завершена.\n\n[История](<C:/work/upwork/code/proposals/daily>)\n'
        with patch.object(cleanup, 'settings', return_value={'workspace_root': str(self.root)}):
            result = cleanup.record_cleanup_answer(body,
                now=datetime(2026, 10, 17, 21, 49, tzinfo=timezone.utc))
        path = self.root / 'AI/log/cleanup/2026/10/18--00-49.md'
        self.assertEqual(Path(result['path']), path)
        self.assertEqual(result['timestamp'], '2026-10-18 00:49 UTC+3')
        self.assertEqual(path.read_bytes(), ('2026-10-18 00:49 UTC+3\n\n' + body).encode('utf-8'))
        self.assertEqual(result['answer'].encode('utf-8'), path.read_bytes())

    def test_repeated_and_concurrent_answers_never_overwrite_logs_in_the_same_minute(self):
        now = datetime(2026, 10, 17, 21, 49, tzinfo=timezone.utc)
        root = self.root / 'logs'
        first = cleanup.record_cleanup_answer('Первый ответ', now=now, log_root=root)
        with ThreadPoolExecutor(max_workers=2) as pool:
            others = list(pool.map(lambda text: cleanup.record_cleanup_answer(text, now=now, log_root=root),
                                   ['Второй ответ', 'Третий ответ']))
        results = [first, *others]
        self.assertEqual({Path(r['path']).name for r in results},
                         {'18--00-49.md', '18--00-49--2.md', '18--00-49--3.md'})
        self.assertEqual(len({r['path'] for r in results}), 3)
        for result in results:
            self.assertEqual(Path(result['path']).read_bytes(), result['answer'].encode('utf-8'))
        self.assertTrue(Path(first['path']).read_text(encoding='utf-8').endswith('Первый ответ'))

    def test_cli_logs_actual_stdin_answer_from_either_platform_without_running_cleanup(self):
        for platform in ('antigravity', 'codex'):
            with self.subTest(platform=platform):
                body = 'Режим: предварительный просмотр.\nПодходящих проектов нет.\n'
                output = io.StringIO()
                with (patch.object(cleanup, 'settings', return_value={'workspace_root': str(self.root)}),
                      patch.object(cleanup, 'cleanup_projects', side_effect=AssertionError('Logging must not run cleanup')),
                      patch('sys.stdin', io.StringIO(body)), redirect_stdout(output)):
                    code = up.main(['cleanup-report', '--answer', '-', '--platform', platform])
                result = json.loads(output.getvalue())
                self.assertEqual(code, 0, result)
                self.assertRegex(result['answer'], r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC\+3\n\n')
                self.assertTrue(result['answer'].endswith(body))
                self.assertEqual(Path(result['path']).read_bytes(), result['answer'].encode('utf-8'))
                self.assertTrue(Path(result['path']).is_relative_to(self.root / 'AI/log/cleanup'))

    def test_empty_answer_or_naive_timestamp_does_not_create_a_log(self):
        root = self.root / 'logs'
        with self.assertRaises(ValueError):
            cleanup.record_cleanup_answer('  ', log_root=root)
        with self.assertRaises(ValueError):
            cleanup.record_cleanup_answer('Отчёт', now=datetime(2026, 10, 18), log_root=root)
        self.assertFalse(root.exists())


if __name__ == '__main__':
    unittest.main()
