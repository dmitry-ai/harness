"""Real-filesystem regressions for evidence commit, scope and crash-safe staging drain."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from test_agent_tools import TemporaryCase
from agent_tools import intake
from agent_tools import upwork_project as up


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def json_data(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


class IntakeTests(TemporaryCase):
    def setUp(self):
        super().setUp()
        self.incoming = self.root / 'incoming'
        self.daily = self.root / 'daily'
        self.capture = self.incoming / '021234567890-abcdef12'
        self.project = self.daily / '2026/10/17/1 - Example'
        self.evidence = self.project / 'ꘖ/KB/Evidence'
        self.capture.mkdir(parents=True)
        self.evidence.mkdir(parents=True)
        self.source = {'job_id': '~021234567890', 'title': 'Task', 'description': 'Exact source\n',
                       'coverage': {'history_complete': False}, 'saved_attachments': []}

    def capture_file(self, name, payload):
        path = self.capture / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path

    def initialize(self, attachment=False):
        assets = []
        if attachment:
            payload = b'Original attachment bytes\r\n'
            path = self.capture_file('attachments/proof.pdf', payload)
            self.source['saved_attachments'] = [{'path': str(path), 'filename': 'proof.pdf', 'sha256': digest(payload)}]
            target = self.evidence / 'Attachments' / digest(payload) / path.name
            target.parent.mkdir(parents=True)
            target.write_bytes(payload)
            assets.append({'file': target.relative_to(self.project / 'ꘖ/KB').as_posix(), 'sha256': digest(payload)})
        self.capture_file('source.json', json_data(self.source))
        canonical = {k: v for k, v in self.source.items() if k not in ('saved_attachments', 'cookies')}
        payload = json_data({**canonical, 'asset_evidence': assets})
        snapshot = self.evidence / (digest(payload) + '.json')
        snapshot.write_bytes(payload)
        state = self.project / 'ꘖ/project.json'
        state.write_bytes(json_data({'initialized': True, 'job_id': self.source['job_id'],
                                     'snapshot': snapshot.relative_to(self.project).as_posix()}))
        registry = self.daily / 'ꘖ/data/projects.json'
        registry.parent.mkdir(parents=True)
        registry.write_bytes(json_data({self.source['job_id']: self.project.relative_to(self.daily).as_posix()}))
        return snapshot

    def commit(self, apply=True, capture=None):
        return intake.commit_capture(capture or self.capture, incoming_root=self.incoming,
                                     daily_root=self.daily, apply=apply)

    def manifest(self):
        return self.evidence / 'Intake' / (self.capture.name + '.json')

    def files(self, directory):
        return {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob('*') if p.is_file()}

    def test_dry_run_has_no_writes_and_identifies_durable_targets(self):
        self.initialize()
        self.capture_file('home.html', b'<html>Observed</html>')
        before = self.files(self.root)
        result = self.commit(apply=False)
        self.assertEqual(result['status'], 'planned', result)
        self.assertEqual(result['files'], 2)
        self.assertFalse(result['drained'])
        self.assertEqual(self.files(self.root), before)

    def test_all_unique_bytes_retained_deduped_and_reachable_without_executable_js(self):
        self.initialize(attachment=True)
        self.capture_file('site.json', b'{"identity":"Observed site"}\r\n')
        self.capture_file('request.txt', b'/upwork-init exact request')
        self.capture_file('home.html', b'same observed web bytes')
        self.capture_file('runtime.mjs', b'same observed web bytes')
        originals = self.files(self.capture)
        result = self.commit()
        self.assertEqual(result['status'], 'drained', result)
        self.assertFalse(self.capture.exists())
        receipt = json.loads(self.manifest().read_text(encoding='utf-8'))
        self.assertTrue(receipt['original_paths_are_provenance_only'])
        self.assertEqual(receipt['status'], 'drained')
        entries = {x['original_relative_provenance']: x for x in receipt['entries']}
        self.assertEqual(set(entries), set(originals))
        for name, payload in originals.items():
            self.assertEqual((self.project / entries[name]['durable_file']).read_bytes(), payload)
            self.assertEqual(entries[name]['sha256'], digest(payload))
        self.assertEqual(entries['home.html']['durable_file'], entries['runtime.mjs']['durable_file'])
        self.assertIn('/Attachments/', entries['attachments/proof.pdf']['durable_file'])
        objects = list((self.evidence / 'Intake/objects').iterdir())
        self.assertEqual(len(objects), 4)
        self.assertFalse(any(p.suffix in ('.js', '.mjs', '.html') for p in objects))
        index = (self.project / 'ꘖ/KB/Intake.md').read_text(encoding='utf-8')
        for name in originals:
            self.assertIn(name, index)
            self.assertIn(entries[name]['durable_file'].removeprefix('ꘖ/KB/'), index)
        self.assertEqual(self.commit()['status'], 'drained')
        self.assertEqual(len(list((self.evidence / 'Intake/objects').iterdir())), 4)

    def test_copy_failure_preserves_all_staging_and_retry_reuses_objects(self):
        self.initialize()
        self.capture_file('home.html', b'primary HTML')
        before = self.files(self.capture)
        actual = intake.create_bytes
        written = []
        def fail_second(path, payload):
            if path.parent.name == 'objects':
                written.append(path)
                if len(written) == 2:
                    raise OSError('disk full')
            actual(path, payload)
        with patch.object(intake, 'create_bytes', side_effect=fail_second):
            result = self.commit()
        self.assertEqual(result['status'], 'retained', result)
        self.assertEqual(self.files(self.capture), before)
        self.assertFalse(self.manifest().exists())
        self.assertEqual(self.commit()['status'], 'drained')
        self.assertEqual(len(list((self.evidence / 'Intake/objects').iterdir())), 2)

    def test_process_death_after_partial_delete_recovers_using_permanent_receipt(self):
        self.initialize()
        self.capture_file('home.html', b'primary HTML')
        self.capture_file('site.json', b'{"site":"example.test"}')
        actual = Path.unlink
        deleted = []
        def crash_after_first(path, *args, **kwargs):
            if path.name.startswith('.intake-retired-'):
                deleted.append(path)
                actual(path, *args, **kwargs)
                raise SystemExit('simulated process death')
            return actual(path, *args, **kwargs)
        with patch.object(Path, 'unlink', crash_after_first):
            with self.assertRaises(SystemExit):
                self.commit()
        self.assertEqual(len(deleted), 1)
        self.assertEqual(json.loads(self.manifest().read_text())['status'], 'prepared')
        result = self.commit()
        self.assertEqual(result['status'], 'drained', result)
        self.assertFalse(self.capture.exists())

    def test_changed_durable_object_prevents_any_retirement(self):
        self.initialize()
        with patch.object(intake, '_index', side_effect=OSError('index write failed')):
            self.assertEqual(self.commit()['status'], 'retained')
        receipt = json.loads(self.manifest().read_text())
        target = self.project / receipt['entries'][0]['durable_file']
        target.write_bytes(b'changed permanent object')
        before = self.files(self.capture)
        result = self.commit()
        self.assertEqual(result['status'], 'retained', result)
        self.assertIn('missing or changed', result['reason'])
        self.assertEqual(self.files(self.capture), before)

    def test_concurrent_edit_after_copy_is_preserved_and_not_silently_replanned(self):
        self.initialize()
        page = self.capture_file('home.html', b'old observation')
        actual = intake._index
        def concurrent(project):
            actual(project)
            page.write_bytes(b'new concurrent observation')
        with patch.object(intake, '_index', side_effect=concurrent):
            result = self.commit()
        self.assertEqual(result['status'], 'retained', result)
        self.assertEqual(page.read_bytes(), b'new concurrent observation')
        self.assertTrue((self.capture / 'source.json').is_file())
        self.assertEqual(self.commit()['status'], 'retained')

    def test_concurrent_replacement_during_retirement_keeps_both_versions(self):
        self.initialize()
        page = self.capture_file('home.html', b'old observation')
        actual = intake.os.rename
        replaced = []
        def concurrent(source, target):
            actual(source, target)
            if Path(source) == page:
                replaced.append(page)
                page.write_bytes(b'new concurrent observation')
        with patch.object(intake.os, 'rename', side_effect=concurrent):
            result = self.commit()
        self.assertEqual(result['status'], 'retained', result)
        self.assertTrue(replaced)
        self.assertEqual(page.read_bytes(), b'new concurrent observation')
        self.assertEqual(intake._retired(self.capture, 'home.html').read_bytes(), b'old observation')
        self.assertTrue((self.capture / 'source.json').is_file())

    def test_missing_or_mismatched_snapshot_never_publishes_or_deletes(self):
        snapshot = self.initialize()
        snapshot.unlink()
        result = self.commit()
        self.assertEqual(result['status'], 'retained', result)
        self.assertTrue((self.capture / 'source.json').is_file())
        self.assertFalse(self.manifest().exists())
        snapshot.write_bytes(json_data({'job_id': self.source['job_id'], 'description': 'different'}))
        self.assertIn('differs', self.commit()['reason'])
        self.assertFalse(self.manifest().exists())

    def test_changed_attachment_and_incomplete_initialization_are_preserved(self):
        self.initialize(attachment=True)
        self.capture_file('attachments/proof.pdf', b'changed attachment')
        self.assertEqual(self.commit()['status'], 'retained')
        state_file = self.project / 'ꘖ/project.json'
        state = json.loads(state_file.read_text())
        state['initialized'] = False
        state_file.write_bytes(json_data(state))
        self.assertIn('incomplete', self.commit()['reason'])
        self.assertTrue(self.capture.exists())

    def test_unknown_manual_material_and_empty_directories_are_preserved(self):
        self.initialize()
        manual = self.capture_file('manual.md', b'User note')
        before = self.files(self.capture)
        self.assertIn('Unknown/manual', self.commit()['reason'])
        self.assertEqual(self.files(self.capture), before)
        manual.unlink()
        (self.capture / 'manual').mkdir()
        self.assertIn('Unknown/manual', self.commit()['reason'])
        self.assertTrue((self.capture / 'manual').is_dir())

    def test_legacy_download_query_filename_is_archived_as_inert_evidence(self):
        self.initialize()
        self.capture_file('products.json_limit=250', b'{"products":[]}')
        result = self.commit()
        self.assertEqual(result['status'], 'drained', result)
        receipt = json.loads(self.manifest().read_text())
        entry = next(x for x in receipt['entries'] if x['original_relative_provenance'] == 'products.json_limit=250')
        self.assertTrue(entry['durable_file'].endswith('.txt'))
        self.assertEqual((self.project / entry['durable_file']).read_bytes(), b'{"products":[]}')

    def test_malformed_or_transport_credential_capture_is_preserved(self):
        self.initialize()
        self.capture_file('source.json', b'[]')
        self.assertEqual(self.commit()['status'], 'retained')
        self.source['cookies'] = [{'value': 'do-not-archive'}]
        self.capture_file('source.json', json_data(self.source))
        self.assertIn('transport credentials', self.commit()['reason'])
        self.assertFalse(self.manifest().exists())

    def test_manual_intake_index_is_never_overwritten(self):
        self.initialize()
        note = self.project / 'ꘖ/KB/Intake.md'
        note.write_bytes(b'# User authored note\n')
        self.assertIn('Manual KB/Intake.md', self.commit()['reason'])
        self.assertEqual(note.read_bytes(), b'# User authored note\n')
        self.assertTrue((self.capture / 'source.json').exists())

    def test_scope_name_and_directory_job_mismatch_are_preserved(self):
        self.initialize()
        outside = self.root / self.capture.name
        outside.mkdir()
        proof = outside / 'source.json'
        proof.write_bytes(json_data(self.source))
        self.assertIn('immediate', self.commit(capture=outside)['reason'])
        self.assertTrue(proof.exists())
        self.source['job_id'] = '~029876543210'
        self.capture_file('source.json', json_data(self.source))
        self.assertIn('IDs differ', self.commit()['reason'])
        manual = self.incoming / 'manual'
        manual.mkdir()
        self.assertIn('Unknown/manual', self.commit(capture=manual)['reason'])

    def test_symlinked_material_cannot_import_or_delete_outside_target(self):
        self.initialize()
        proof = self.root / 'outside.html'
        proof.write_bytes(b'outside material')
        try:
            (self.capture / 'home.html').symlink_to(proof)
        except OSError as exc:
            self.skipTest(f'Symlink creation is unavailable: {exc}')
        self.assertIn('Linked path', self.commit()['reason'])
        self.assertEqual(proof.read_bytes(), b'outside material')
        self.assertTrue((self.capture / 'source.json').exists())

    def test_two_concurrent_drainers_commit_once_and_remain_idempotent(self):
        self.initialize(attachment=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.commit(), range(2)))
        self.assertEqual([x['status'] for x in results], ['drained', 'drained'], results)
        self.assertEqual(len(list((self.evidence / 'Intake/objects').iterdir())), 1)

    def test_user_note_in_previously_generated_index_is_preserved_on_retry(self):
        self.initialize()
        self.assertEqual(self.commit()['status'], 'drained')
        index = self.project / 'ꘖ/KB/Intake.md'
        index.write_bytes(index.read_bytes() + b'\nMY MANUAL NOTE\n')
        previous = index.read_bytes()
        self.assertEqual(self.commit()['status'], 'retained')
        self.assertEqual(index.read_bytes(), previous)

    def test_cli_dry_run_then_apply_and_managed_init_integration(self):
        self.initialize()
        with patch.object(intake, 'INCOMING', self.incoming), redirect_stdout(io.StringIO()) as output:
            code = up.main(['intake-drain', str(self.capture), '--daily-root', str(self.daily)])
        self.assertEqual(code, 0, output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['captures'][0]['status'], 'planned')
        self.assertTrue(self.capture.exists())
        # A normal CLI init has already saved its snapshot before drain runs.
        result = {'project_dir': str(self.project), 'registration': None}
        with patch.object(intake, 'INCOMING', self.incoming), \
                patch.object(up, 'initialize_upwork_project', return_value=result), \
                redirect_stdout(io.StringIO()) as output:
            code = up.main(['init', self.source['job_id'], '--from-json', str(self.capture / 'source.json'),
                            '--domain', 'Example', '--daily-root', str(self.daily), '--no-register'])
        self.assertEqual(code, 0, output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['intake']['status'], 'drained')
        self.assertFalse(self.capture.exists())


if __name__ == '__main__':
    unittest.main()
