"""Cross-application registration uses isolated native stores and mocked UI transport."""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import patch

from test_agent_tools import TemporaryCase
from test_onboarding import source
from agent_tools import registration, runtime, upwork_project as up
from agent_tools.platforms import antigravity, codex


class RegistrationTests(TemporaryCase):
    def setUp(self):
        super().setUp()
        self.project = Path(up.initialize_upwork_project(source()['job_id'], 'Topic', '2026-10-15',
            daily_root=self.root / 'daily', extracted_data=source(), register_native=False)['project_dir'])
        self.config = deepcopy(runtime.settings())
        self.config['registration'] = {'targets': ['antigravity', 'codex']}
        self.patch = patch.object(registration, 'settings', return_value=self.config)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.native_projects = self.root / 'ag/projects'
        self.folders = self.root / 'ag/folders.json'
        self.folders.parent.mkdir(parents=True)
        self.folders.write_text('{"folders":[],"projectFolderMap":{}}', encoding='utf-8')
        self.calls = []

    def ag(self, root, label, day):
        self.calls.append('antigravity')
        return antigravity.register_antigravity_project(root, label, day,
            projects_dir=self.native_projects, folders_json_path=self.folders)

    def cx(self, root, label, day):
        self.calls.append('codex')
        _, _, _, expected = registration._expected(root, label, day)
        return {**expected, 'surface': 'codex-ui', 'shared_id': 'shared', 'folder_id': 'folder',
                'profile': 'C2', 'profiles': {'C1': {'project_id': 'c1', 'ready': True},
                                           'C2': {'project_id': 'c2', 'ready': True}},
                'complete': True, 'status': 'registered'}

    def run_registration(self, platform='antigravity', **kwargs):
        return registration.register_projects(self.project, platform=platform,
            registrars={'antigravity': self.ag, 'codex': self.cx}, **kwargs)

    def saved(self):
        return json.loads((self.project / 'ꘖ/data/registrations.json').read_text(encoding='utf-8'))

    def test_both_entry_platforms_register_both_with_active_flat_compatibility(self):
        for platform in ('antigravity', 'codex'):
            self.calls.clear()
            result = self.run_registration(platform)
            self.assertEqual(self.calls[0], platform)
            self.assertEqual(set(self.calls), {'antigravity', 'codex'})
            self.assertTrue(result['complete'])
            self.assertTrue(result['all_registered'])
            self.assertEqual(result['project_name'], 'Topic - U.P.2026.10.15')
            self.assertEqual(result['folder_path'], 'Upwork / Proposals / 2026 / 10 / 15')
            self.assertEqual(result['root_paths'], [str(self.project)])
            self.assertEqual(set(result['registrations']), {'antigravity', 'codex'})
            self.assertTrue(all(record['complete'] for record in self.saved().values()))

    def test_repeat_preserves_native_ids_and_manual_native_fields(self):
        first = self.run_registration()
        record = Path(first['project_file'])
        native = json.loads(record.read_text(encoding='utf-8'))
        native['settings']['custom'] = 'user setting'
        record.write_text(json.dumps(native), encoding='utf-8')
        second = self.run_registration()
        self.assertEqual(first['project_id'], second['project_id'])
        self.assertEqual(second['registrations']['codex']['shared_id'], 'shared')
        self.assertEqual(len(list(self.native_projects.glob('*.json'))), 1)
        self.assertEqual(json.loads(record.read_text())['settings']['custom'], 'user setting')
        self.assertEqual(second['attempts'], 2)
        self.assertEqual(len(second['attempt_history']), 2)

    def test_secondary_failure_keeps_current_ready_and_previous_success(self):
        self.run_registration()
        def offline(*args):
            raise RuntimeError('Secondary UI is offline')
        result = registration.register_projects(self.project, platform='antigravity',
            registrars={'antigravity': self.ag, 'codex': offline})
        self.assertTrue(result['complete'])
        self.assertFalse(result['all_registered'])
        secondary = result['registrations']['codex']
        self.assertEqual(secondary['status'], 'error')
        self.assertNotIn('profiles', secondary)
        self.assertTrue(secondary['last_success']['profiles']['C2']['ready'])
        self.assertEqual(secondary['intent']['root_paths'], [str(self.project)])
        self.assertEqual(self.saved()['codex']['error']['message'], 'Secondary UI is offline')

    def test_pending_secondary_does_not_gate_active_and_pending_active_does(self):
        def pending(*args):
            result = self.cx(*args)
            result['complete'] = False
            result['profiles']['C2']['ready'] = False
            return result
        for active, complete in [('antigravity', True), ('codex', False)]:
            result = registration.register_projects(self.project, platform=active,
                registrars={'antigravity': self.ag, 'codex': pending})
            self.assertEqual(result['complete'], complete)
            self.assertFalse(result['all_registered'])
            self.assertEqual(result['registrations']['codex']['status'], 'pending')

    def test_manual_native_name_conflict_preserves_name_and_records_expected_actual(self):
        result = self.run_registration()
        record = Path(result['project_file'])
        native = json.loads(record.read_text(encoding='utf-8'))
        native['name'] = 'User renamed this project'
        record.write_text(json.dumps(native), encoding='utf-8')
        before = record.read_bytes()
        result = self.run_registration()
        self.assertFalse(result['complete'])
        self.assertEqual(result['status'], 'conflict')
        self.assertEqual(result['expected']['project_name'], 'Topic - U.P.2026.10.15')
        self.assertEqual(result['actual']['project_name'], 'User renamed this project')
        self.assertEqual(record.read_bytes(), before)
        self.assertEqual(result['last_success']['project_name'], 'Topic - U.P.2026.10.15')

    def test_wrong_roots_or_folder_are_not_reported_as_registered(self):
        for field, value in [('root_paths', [str(self.root)]), ('folder_path', 'Elsewhere')]:
            def wrong(*args):
                result = self.cx(*args)
                result[field] = value
                return result
            result = registration.register_projects(self.project, platform='codex',
                registrars={'antigravity': self.ag, 'codex': wrong})
            self.assertFalse(result['complete'])
            self.assertEqual(result['status'], 'conflict')
            self.assertTrue(result['registrations']['antigravity']['complete'])

    def test_intent_is_saved_before_native_call_and_interrupted_attempt_remains(self):
        def interrupted(*args):
            saved = self.saved()['codex']
            self.assertEqual(saved['status'], 'attempting')
            self.assertEqual(saved['intent']['project_name'], 'Topic - U.P.2026.10.15')
            raise KeyboardInterrupt('Process stopped')
        with self.assertRaises(KeyboardInterrupt):
            registration.register_projects(self.project, platform='codex',
                registrars={'antigravity': self.ag, 'codex': interrupted})
        self.assertEqual(self.saved()['codex']['attempt']['status'], 'attempting')
        initial = self.saved()['codex']['attempt']['id']
        result = self.run_registration('codex')
        saved_attempt = next(item for item in result['attempt_history'] if item['id'] == initial)
        self.assertEqual(saved_attempt['intent']['root_paths'], [str(self.project)])
        self.assertNotIn('finished_at', saved_attempt)

    def test_single_adapter_entry_point_preserves_failure_semantics_and_receipt(self):
        with patch.object(codex, 'register', side_effect=RuntimeError('Unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'Unavailable'):
                registration.register_project(self.project, platform='codex')
        self.assertEqual(set(self.saved()), {'codex'})
        self.assertEqual(self.saved()['codex']['status'], 'error')

    def test_legacy_success_and_direct_save_keep_native_identity_after_failure(self):
        legacy = self.ag(self.project, 'Topic', '2026-10-15')
        path = self.project / 'ꘖ/data/registrations.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'antigravity': legacy}), encoding='utf-8')
        failed = registration.save_registration(self.project, 'antigravity',
            {'status': 'error', 'complete': False, 'error': {'message': 'Offline'}})
        self.assertFalse(failed['complete'])
        self.assertNotIn('project_id', failed)
        self.assertEqual(failed['last_success']['project_id'], legacy['project_id'])
        self.assertEqual(self.saved()['antigravity'], failed)

    def test_single_success_only_calls_the_selected_adapter(self):
        with patch.object(codex, 'register', side_effect=self.cx), patch.object(antigravity, 'register',
                side_effect=AssertionError('Another application must not be called')):
            result = registration.register_project(self.project, platform='codex')
        self.assertTrue(result['complete'])
        self.assertEqual(set(self.saved()), {'codex'})
        self.assertEqual(result['profiles']['C2']['project_id'], 'c2')

    def test_shared_id_without_selected_profile_native_id_is_not_success(self):
        def missing_profile(*args):
            result = self.cx(*args)
            del result['profiles']['C2']['project_id']
            return result
        result = registration.register_projects(self.project, platform='codex',
            registrars={'antigravity': self.ag, 'codex': missing_profile})
        self.assertFalse(result['complete'])
        self.assertEqual(result['status'], 'conflict')

    def test_slow_previous_success_does_not_erase_a_newer_failed_attempt(self):
        began, release = threading.Event(), threading.Event()
        def slow(*args):
            began.set()
            if not release.wait(timeout=5):
                raise TimeoutError('Test registration was not released')
            return self.cx(*args)
        def failed(*args):
            raise RuntimeError('Newer attempt failed')
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(registration.register_projects, self.project, platform='codex',
                targets=['codex'], registrars={'codex': slow})
            self.assertTrue(began.wait(timeout=5))
            try:
                second = registration.register_projects(self.project, platform='codex',
                    targets=['codex'], registrars={'codex': failed})
            finally:
                release.set()
            self.assertTrue(first.result(timeout=5)['complete'])
        self.assertFalse(second['complete'])
        saved = self.saved()['codex']
        self.assertEqual(saved['error']['message'], 'Newer attempt failed')
        self.assertEqual(saved['last_success']['shared_id'], 'shared')
        self.assertEqual(saved['attempts'], 2)
        self.assertEqual(len(saved['attempt_history']), 2)


class RegistrationProfileTests(TemporaryCase):
    def setUp(self):
        super().setUp()
        self.config = deepcopy(runtime.settings())
        self.config['platforms']['codex'].update(registration_profile='C2', homes={
            'C1': str(self.root / 'C1'), 'C2': str(self.root / 'C2')})
        self.patch = patch.object(runtime, 'settings', return_value=self.config)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_registration_only_fallback_does_not_relax_native_evidence_profile(self):
        self.assertEqual(runtime.registration_profile_name(), 'C2')
        with self.assertRaises(ValueError):
            runtime.profile_name()
        with runtime.using('antigravity', 'C1'):
            self.assertEqual(runtime.registration_profile_name(), 'C1')
        with patch.dict(os.environ, {'CODEX_HOME': str(self.root / 'C1')}):
            self.assertEqual(runtime.registration_profile_name(), 'C1')
        with patch.dict(os.environ, {'UPWORK_CODEX_PROFILE': 'C1'}):
            self.assertEqual(runtime.registration_profile_name(), 'C1')

    def test_explicit_unknown_profile_or_unrecognized_home_never_uses_fallback(self):
        with patch.dict(os.environ, {'CODEX_HOME': str(self.root / 'unknown')}):
            with self.assertRaises(ValueError):
                runtime.registration_profile_name()
        with self.assertRaises(ValueError):
            runtime.registration_profile_name('unknown')
        self.config['platforms']['codex']['registration_profile'] = 'unknown'
        with self.assertRaises(ValueError):
            runtime.registration_profile_name()

    def test_codex_adapter_uses_fallback_and_rejects_wrong_native_name_without_rename(self):
        self.root.mkdir(exist_ok=True)
        expected = registration._expected(self.root, 'Topic', '2026-10-15')[3]
        receipt = {**expected, 'shared_id': 'shared', 'folder_id': 'folder', 'complete': False,
                   'profiles': {'C2': {'project_id': 'c2', 'ready': False}}}
        with patch.object(codex.subprocess, 'run', return_value=SimpleNamespace(returncode=0,
                stdout=json.dumps(receipt), stderr='')) as invoke:
            result = codex.register(self.root, 'Topic', '2026-10-15')
            request = json.loads(invoke.call_args.kwargs['input'])
            self.assertEqual(request['profile'], 'C2')
            self.assertEqual(request['command'], 'shared-ensure-project')
            self.assertEqual(request['project']['trustPolicy'], 'upwork-daily')
            self.assertFalse(result['complete'])
        receipt['profiles']['C2']['registration_block'] = {'status': 'untrusted', 'error': 'Explicit untrusted'}
        with patch.object(codex.subprocess, 'run', return_value=SimpleNamespace(returncode=0,
                stdout=json.dumps(receipt), stderr='')):
            blocked = codex.register(self.root, 'Topic', '2026-10-15')
            self.assertFalse(blocked['complete'])
            self.assertEqual(blocked['status'], 'untrusted')
        receipt['project_name'] = 'Manual name'
        with patch.object(codex.subprocess, 'run', return_value=SimpleNamespace(returncode=0,
                stdout=json.dumps(receipt), stderr='')) as invoke:
            with self.assertRaises(registration.RegistrationConflict):
                codex.register(self.root, 'Topic', '2026-10-15')
            self.assertEqual(invoke.call_count, 1)


if __name__ == '__main__':
    unittest.main()
