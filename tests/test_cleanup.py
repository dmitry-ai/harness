"""Destructive cleanup regressions run only against isolated native stores."""

from copy import deepcopy
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
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


if __name__ == '__main__':
    unittest.main()
