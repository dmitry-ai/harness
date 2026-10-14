"""Offline regressions and real subprocess/filesystem/Git integration tests."""

from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from agent_tools import journal
from agent_tools.context import assemble, generate, resolve_letter_file, discover_letters
from agent_tools.git_gate import check_commit, commit
from agent_tools.links import Page, check_network, references, validate_content
from agent_tools.snapshot import snapshot_draft
from agent_tools.statements import validate_statements


class TemporaryCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode('utf-8'))
        return path

    def cli(self, name, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / (name + '.py')), *map(str, args)],
                              cwd=self.root, capture_output=True, encoding='utf-8')


class JournalTests(TemporaryCase):
    def test_exact_bytes_and_no_keyword_authorization(self):
        req, res = '  вопрос\r\n\r\n', '[Источник](https://www.example.org/a/?q=%20)\n'
        journal_dir = self.root / 'chat'
        step = journal.record_step(journal_dir, req, res)
        self.assertEqual((journal_dir / 'req/1.md').read_bytes(), req.encode())
        self.assertEqual((journal_dir / 'res/1.md').read_bytes(), res.encode())
        self.assertFalse((journal_dir / '.journal').exists())
        self.assertFalse((journal.state_dir(journal_dir) / '1.json').exists())
        self.assertTrue((journal.state_dir(journal_dir) / 'writer.lock').exists())
        self.assertEqual(journal.step_errors(journal_dir, step), [])

    def test_existing_same_request_is_not_ownership(self):
        self.put('req/7.md', 'same')
        self.put('res/9.md', 'orphan')
        self.assertEqual(journal.record_step(self.root, 'same', 'new'), 10)
        self.assertFalse((self.root / 'res/7.md').exists())

    def test_explicit_occupied_slot_and_overwrite_rejected(self):
        self.put('req/2.md', 'original')
        with self.assertRaises(FileExistsError):
            journal.record_step(self.root, 'replace', 'response', target_step=2)
        with self.assertRaises(ValueError):
            journal.record_step(self.root, 'replace', 'response', target_step=2, allow_overwrite=True)
        self.assertEqual((self.root / 'req/2.md').read_text(), 'original')

    def test_empty_payload_has_no_side_effect(self):
        with self.assertRaises(ValueError):
            journal.record_step(self.root / 'unused', 'req', '  ')
        self.assertFalse((self.root / 'unused').exists())

    def test_failed_second_write_recovers_with_token(self):
        actual = journal.create_bytes
        def failing(path, data):
            if path.parent.name == 'res':
                raise OSError('simulated disk error')
            actual(path, data)
        with patch.object(journal, 'create_bytes', side_effect=failing):
            with self.assertRaises(RuntimeError):
                journal.record_step(self.root, 'request', 'response')
        receipt = journal.state_dir(self.root) / '1.json'
        state = json.loads(receipt.read_text())
        self.assertTrue(journal.step_errors(self.root, 1))
        with self.assertRaises(ValueError):
            journal.recover_step(self.root, 1, 'someone-else')
        journal.recover_step(self.root, 1, state['token'])
        self.assertFalse(receipt.exists())
        self.assertEqual(journal.step_errors(self.root, 1), [])

    def test_recovery_does_not_overwrite_conflict(self):
        actual = journal.create_bytes
        def failing(path, data):
            if path.parent.name == 'res':
                raise OSError('simulated disk error')
            actual(path, data)
        with patch.object(journal, 'create_bytes', side_effect=failing):
            with self.assertRaises(RuntimeError):
                journal.record_step(self.root, 'req', 'res')
        receipt = journal.state_dir(self.root) / '1.json'
        state = json.loads(receipt.read_text())
        self.put('res/1.md', 'human correction')
        with self.assertRaises(FileExistsError):
            journal.recover_step(self.root, 1, state['token'])
        self.assertTrue(receipt.exists())
        self.assertTrue(journal.step_errors(self.root, 1))

    def test_process_crash_releases_lock_and_reservation_is_recoverable(self):
        code = '''import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from agent_tools import journal
original = journal.create_bytes
def crash(path, data):
    if path.parent.name == 'res':
        os._exit(43)
    original(path, data)
journal.create_bytes = crash
journal.record_step(Path(sys.argv[2]), 'request', 'response')
'''
        result = subprocess.run([sys.executable, '-c', code, str(SCRIPTS), str(self.root)])
        self.assertEqual(result.returncode, 43)
        receipt = journal.state_dir(self.root) / '1.json'
        state = json.loads(receipt.read_text())
        self.assertEqual(journal.record_step(self.root, 'next', 'answer'), 2)
        journal.recover_step(self.root, 1, state['token'])
        self.assertFalse(receipt.exists())
        self.assertEqual(journal.step_errors(self.root, 1), [])

    def test_concurrent_real_processes_same_request_get_distinct_pairs(self):
        def run(index):
            return self.cli('record_step', '--dir', self.root, '--req', 'identical request', '--res', f'response {index}')
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(run, range(12)))
        for result in results:
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(journal.get_existing_step_ids(self.root), set(range(1, 13)))
        self.assertEqual({p.read_text() for p in (self.root / 'res').glob('*.md')},
                         {f'response {i}' for i in range(12)})
        self.assertEqual(list(journal.state_dir(self.root).glob('*.json')), [])
        for step in range(1, 13):
            self.assertEqual(journal.step_errors(self.root, step), [])

    def test_validation_checks_orphan_res_and_never_scans_neighbor_drafts(self):
        self.put('req/1.md', 'question')
        self.put('res/1.md', 'answer')
        self.put('Contracts/a/draft.md', '[bad](http://[invalid)')
        self.assertEqual(self.cli('validate_step', '--dir', self.root, '--step', 1).returncode, 0)
        self.put('res/2.md', 'orphan')
        self.assertNotEqual(self.cli('validate_step', '--dir', self.root, '--all').returncode, 0)

    def test_no_target_is_not_success(self):
        for name in ('validate_step', 'validate_links', 'validate_anchors', 'safe_commit'):
            self.assertNotEqual(self.cli(name).returncode, 0)


class LinkTests(unittest.TestCase):
    def test_real_http_redirect_anchor_and_404(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == '/redirect':
                    self.send_response(302)
                    self.send_header('Location', '/page')
                    self.end_headers()
                elif self.path == '/page':
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write('<div id="§x"></div>'.encode('utf-8'))
                else:
                    self.send_error(404)
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f'http://127.0.0.1:{server.server_port}'
            results = check_network([base + '/redirect#%C2%A7x', base + '/missing#a'], anchors=True)
            self.assertEqual(results[0]['status'], 'found-in-source')
            self.assertEqual(results[0]['final_url'], base + '/page')
            self.assertEqual(results[1]['status'], 'fetch-error')
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    def test_markdown_reference_links_balanced_parentheses_and_html(self):
        text = '[nested](https://example.org/a_(b))\n[reference][x]\n\n[x]: https://example.org/ref\n\n<a href="https://example.org/html?a=1&amp;b=2">x</a>'
        urls, _ = references(text)
        self.assertEqual(urls, ['https://example.org/a_(b)', 'https://example.org/ref', 'https://example.org/html?a=1&b=2'])

    def test_code_samples_are_not_document_links(self):
        urls, _ = references('```md\n[example](https://example.org/code)\n```\n`https://example.org/inline`\n[actual](https://example.org/actual)')
        self.assertEqual(urls, ['https://example.org/actual'])

    def test_preserves_valid_urls_and_markdown(self):
        text = '[**example.org**/](https://www.example.org/a/?sig=x%2Fy&utm_key=part-of-signature#x)\nhttps://[::1]:8080/\n'
        self.assertEqual(validate_content(text), [])

    def test_invalid_port_is_diagnostic_not_crash(self):
        self.assertTrue(validate_content('https://example.org:wrong/'))

    def test_local_anchors_decode_and_are_case_sensitive(self):
        text = "<a name='§I.1'></a>\n[section](#%C2%A7I.1)"
        self.assertEqual(validate_content(text, local_anchors=True), [])
        self.assertTrue(validate_content(text.replace('#%C2%A7I.1', '#%C2%A7i.1'), local_anchors=True))

    def test_unique_urls_is_explicit_policy(self):
        text = '[x](https://example.org)\n[y](https://example.org)'
        self.assertEqual(validate_content(text), [])
        self.assertTrue(validate_content(text, unique_urls=True))

    def test_same_id_and_name_on_one_anchor_are_not_duplicates(self):
        self.assertEqual(validate_content('<a id="x" name="x"></a>\n[link](#x)', local_anchors=True), [])

    def test_failed_cached_fetch_reports_each_anchor(self):
        calls = []
        def fetch(url, timeout):
            calls.append(url)
            raise OSError('offline')
        results = check_network(['https://example.org#x', 'https://example.org#y'], anchors=True, fetcher=fetch)
        self.assertEqual(len(calls), 1)
        self.assertEqual([r['status'] for r in results], ['fetch-error', 'fetch-error'])

    def test_anchor_html_parser_handles_spacing_entities_and_case(self):
        def fetch(url, timeout):
            return Page(url, 200, 'text/html', '<div id = "A&amp;B"></div><a name=legacy></a>')
        urls = ['https://example.org#A%26B', 'https://example.org#legacy', 'https://example.org#a%26b']
        results = check_network(urls, anchors=True, fetcher=fetch)
        self.assertEqual([r['status'] for r in results], ['found-in-source', 'found-in-source', 'not-found-in-source'])


class SnapshotTests(TemporaryCase):
    def test_current_bytes_preserved_once_per_turn(self):
        (self.root / '.agents').mkdir()
        draft = self.put('Letters/draft.md', 'user change\r\n')
        saved = snapshot_draft(draft, 'turn_1')
        self.assertTrue(saved.is_relative_to(self.root / '.agents/data/.draft-snapshots'))
        self.assertFalse((draft.parent / '.draft-snapshots').exists())
        self.put('Letters/draft.md', 'agent revision')
        self.assertEqual(snapshot_draft(draft, 'turn_1'), saved)
        self.assertEqual(saved.read_bytes(), b'user change\r\n')
        self.assertEqual((draft.parent / 'draft.prev.md').read_bytes(), b'user change\r\n')
        second = snapshot_draft(draft, 'turn_2')
        self.assertEqual(second.read_bytes(), b'agent revision')
        self.assertEqual(saved.read_bytes(), b'user change\r\n')

    def test_changed_previous_copy_is_not_silently_replaced(self):
        draft = self.put('draft.md', 'before')
        snapshot_draft(draft, 'turn')
        self.put('draft.prev.md', 'external edit')
        with self.assertRaises(ValueError):
            snapshot_draft(draft, 'turn')


class ContextTests(TemporaryCase):
    def test_empty_final_never_falls_back_to_draft(self):
        draft = self.put('letter/result/EN/draft.md', 'draft')
        self.put('letter/result/EN/final.md', '  ')
        for path in (draft, self.root / 'letter'):
            with self.assertRaises(ValueError):
                resolve_letter_file(path)

    def test_final_without_draft_and_new_year_nested_letters(self):
        final = self.put('letters/2027/01/02/1/result/EN/final.md', 'final')
        self.put('letters/2027/01/02/1/result/EN/draft.md', 'draft')
        second = self.put('letters/2027/01/02/2/.md', 'second')
        self.assertEqual(discover_letters(self.root / 'letters'), [final, second])

    def test_sources_and_fences_preserved_in_configured_order(self):
        original = '# Title\n```python\nprint(1)\n```\n'
        self.put('kb.md', original)
        self.put('letters/2030/01/02/.md', 'client reply')
        manifest = {'version': 1, 'sections': [
            {'title': 'KB', 'files': ['kb.md']},
            {'title': 'Correspondence', 'letters': [{'root': 'letters', 'author': 'Client'}]}]}
        content, sources = assemble(self.root, manifest)
        self.assertIn(original, content)
        self.assertIn('````markdown', content)
        self.assertIn('Author: Client', content)
        self.assertLess(content.index('# KB'), content.index('# Correspondence'))
        self.assertEqual(len(sources), 2)

    def test_missing_input_fails_and_dry_run_writes_nothing(self):
        config = self.put('context.json', json.dumps({'version': 1, 'output': 'out.md', 'sections': [
            {'title': 'KB', 'files': ['kb.md']}]}))
        with self.assertRaises(FileNotFoundError):
            generate(self.root, config)
        self.put('kb.md', 'source')
        generate(self.root, config, dry_run=True)
        self.assertFalse((self.root / 'out.md').exists())
        generate(self.root, config)
        self.assertTrue((self.root / 'out.md').exists())
        self.assertFalse((self.root / '.out.md.lock').exists())
        self.assertTrue((self.root / '.agents/data/context.lock').exists())

    def test_output_cannot_overwrite_input_or_escape_root(self):
        config = self.put('context.json', json.dumps({'version': 1, 'output': 'kb.md', 'sections': [
            {'title': 'KB', 'files': ['kb.md']}]}))
        self.put('kb.md', 'original')
        for output in (None, Path('../escape.md'), config):
            with self.assertRaises(ValueError):
                generate(self.root, config, output)
        self.assertEqual((self.root / 'kb.md').read_text(), 'original')


class GitTests(TemporaryCase):
    def git(self, *args):
        result = subprocess.run(['git', '-C', str(self.root), *args], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def setUp(self):
        super().setUp()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Local Test')
        self.git('config', 'user.email', 'local-test@example.invalid')
        self.git('config', 'core.autocrlf', 'false')
        self.put('a space.md', 'before\n')
        self.put('b.md', 'other\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'initial fixture')

    def test_unrelated_staged_change_is_rejected(self):
        self.put('a space.md', 'after\n')
        self.put('b.md', 'unrelated\n')
        self.git('add', '.')
        with self.assertRaises(ValueError):
            check_commit(self.root, ['a space.md'])

    def test_unstaged_change_rejected_and_explicit_commit_works(self):
        self.put('a space.md', 'staged\n')
        self.git('add', '--', 'a space.md')
        self.put('a space.md', 'later user change\n')
        with self.assertRaises(ValueError):
            check_commit(self.root, ['a space.md'])
        self.git('add', '--', 'a space.md')
        before = self.git('rev-parse', 'HEAD')
        commit(self.root, ['a space.md'], 'review only')
        self.assertEqual(self.git('rev-parse', 'HEAD'), before)
        commit(self.root, ['a space.md'], 'explicit commit', execute=True)
        self.assertEqual(self.git('show', 'HEAD:a space.md'), b'later user change\n')
        self.assertEqual(self.git('show', 'HEAD:b.md'), b'other\n')


class StatementTests(TemporaryCase):
    def test_missing_test_not_masked_by_words_in_statement(self):
        self.put('1/.md', 'Methodology: Chrome CDP; curl checked response headers.\n[x](https://example.org)')
        self.assertTrue(validate_statements(self.root))
        self.put('1/Test.md', 'Actual test record')
        self.assertEqual(validate_statements(self.root), [])


if __name__ == '__main__':
    unittest.main()
