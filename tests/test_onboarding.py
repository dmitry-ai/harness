"""Behavioral regressions for preservation, provenance, concurrency and native discovery."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from email.message import Message
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.request import Request

from test_agent_tools import TemporaryCase
from agent_tools import journal
from agent_tools.context import generate
from agent_tools.knowledge import render_analysis, validate_analysis
from agent_tools.links import validate_file
from agent_tools.snapshot import snapshot_draft
from agent_tools import upwork_project as up
from agent_tools.upwork_data import extract_candidate_domains, format_kb_project_md
from agent_tools.upwork_extract import RPC, SafeRedirect, attachment_path, decode_page, download_attachment, select_tab


def source(job_id='~021234567890'):
    return {'job_id': job_id, 'title': 'Client task',
            'description': 'CURRENT_DESCRIPTION_NOT_A_SUMMARY\n```text\noriginal code\n```\n',
            'buyer': {'location': {'country': 'Portugal'}}, 'candidate_domains': ['reference.example'],
            'work_history': [], 'open_jobs': [], 'related_descriptions': {}, 'client_names': [],
            'coverage': {'history_records': 0, 'history_complete': False},
            'observed_at': '2026-10-15T00:00:00+03:00'}


def claim(ident, addresses=(), method=False):
    result = {'id': ident, 'essence': 'Client-specific proposed explanation',
              'for': [{'argument': 'The description explicitly states this concern.',
                       'source': 'https://example.org/source#concern', 'quote': 'The concern'}],
              'against': [{'argument': 'The source also gives an alternative.',
                           'source': 'https://example.org/source#alternative', 'quote': 'Alternative'}],
              'assessment_basis': 'Expert estimate based on the stated evidence; not calibrated.',
              'addresses': list(addresses)}
    result['score_percent' if method else 'probability_percent'] = 60
    if method:
        result['criterion'] = 'Technical suitability under the stated conditions'
    return result


def analysis():
    return {'identity': [], 'concerns': [claim('H-CONCERN-1')], 'misconceptions': [],
            'causes': [claim('H-CAUSE-1', ['H-CONCERN-1'])],
            'methods': [claim('M-1', ['H-CAUSE-1'], method=True)],
            'notes': {'identity': 'Not established.', 'misconceptions': 'No misconception established.'}}


class InitializationTests(TemporaryCase):
    def init(self, data=None, **kwargs):
        data = source() if data is None else data
        return up.initialize_upwork_project(data['job_id'], domain_or_topic='Topic',
            date_str='2026-10-15', daily_root=self.root / 'daily', extracted_data=data,
            register_antigravity=False, **kwargs)

    def test_native_manifests_and_full_initial_port(self):
        result = self.init()
        root = Path(result['project_dir'])
        self.assertEqual((root / 'ꘖ/KB/Project.md').read_bytes(), (root / 'KB/Project.md').read_bytes())
        self.assertIn(source()['description'], (root / 'ꘖ/KB/Projects.md').read_text(encoding='utf-8'))
        for kind in ('rules', 'skills', 'agents'):
            cfg = json.loads((root / f'.agents/{kind}.json').read_text(encoding='utf-8'))
            self.assertEqual(Path(cfg['entries'][0]['path']), up.PRIMARY_AGENTS_DIR / kind)
            if kind == 'rules':
                self.assertIn({'path': 'rules'}, cfg['entries'])
        self.assertFalse(any(p.is_symlink() or p.is_junction() for p in (root / '.agents').rglob('*')))
        website = (root / 'ꘖ/KB/Website.md').read_text(encoding='utf-8')
        self.assertNotIn('`подтверждено`', website)
        self.assertIn('reference.example', website)
        self.assertNotIn('Эти проекты относятся к тому же сайту', (root / 'KB/Project.md').read_text(encoding='utf-8'))

    def test_repeat_preserves_every_curated_file_and_configuration(self):
        root = Path(self.init()['project_dir'])
        files = [root / '.md', root / 'KB/Project.md', *(root / 'ꘖ/KB').glob('*.md')]
        for path in files:
            path.write_bytes(path.read_bytes() + b'\nCURATED_CONTENT\n')
        before = {p: p.read_bytes() for p in files}
        cfg = root / '.agents/context.json'
        value = json.loads(cfg.read_text(encoding='utf-8'))
        value['custom'] = 'keep'
        cfg.write_text(json.dumps(value), encoding='utf-8')
        before[cfg] = cfg.read_bytes()
        updated = {**source(), 'description': 'A new capture must not erase previous research'}
        self.init(updated)
        self.assertEqual({p: p.read_bytes() for p in before}, before)
        (root / 'KB/Project.md').unlink()
        self.init(updated)
        self.assertFalse((root / 'KB/Project.md').exists())

    def test_existing_neighbor_material_is_untouched(self):
        root = self.root / 'project'
        note = self.put('project/.agents/private/work.txt', 'user material')
        config = self.put('project/.agents/context.json', '{"version":1,"sections":[{"title":"Custom","files":["custom.md"]}],"output":"custom-context.md"}')
        before = config.read_bytes()
        up.configure_project(root)
        up.configure_project(root)
        self.assertEqual(note.read_text(), 'user material')
        self.assertEqual(config.read_bytes(), before)

    def test_registry_is_stable_across_dates_and_labels(self):
        daily = self.root / 'daily'
        first = up.resolve_or_create_project_dir('~02123', 'First', '2026-10-15', daily)
        second = up.resolve_or_create_project_dir('~02123', 'Other', '2026-10-16', daily)
        self.assertEqual(first, second)

    def test_concurrent_numbers_and_same_job_are_exclusive(self):
        daily = self.root / 'daily'
        def create(index):
            return up.resolve_or_create_project_dir(f'~02{index:08d}', f'Topic {index}', '2026-10-15', daily)
        with ThreadPoolExecutor(max_workers=8) as pool:
            paths = list(pool.map(create, range(16)))
        self.assertEqual(len({p.name.split(' - ')[0] for p in paths}), 16)
        with ThreadPoolExecutor(max_workers=4) as pool:
            repeated = list(pool.map(lambda _: create(1), range(8)))
        self.assertEqual(len(set(repeated)), 1)

    def test_invalid_names_dates_and_capture_do_not_create_projects(self):
        for label in ('https://example.com', '../outside', 'bad:name', 'trail. '):
            with self.assertRaises(ValueError):
                up.resolve_or_create_project_dir('~02123', label, '2026-10-15', self.root / 'unused')
        with self.assertRaises(ValueError):
            up.resolve_or_create_project_dir('~02123', 'Topic', '2026-99-99', self.root / 'unused')
        with self.assertRaises(ValueError):
            self.init({**source(), 'description': ''})
        with self.assertRaises(ValueError):
            up.initialize_upwork_project(source()['job_id'], extracted_data=[])
        self.assertFalse((self.root / 'unused').exists())
        self.assertFalse((self.root / 'daily').exists())

    def test_cli_init_reuses_capture_without_browser(self):
        capture = self.put('capture/source.json', json.dumps(source()))
        result = self.cli('upwork_project', 'init', source()['job_id'], '--from-json', capture,
                          '--domain', 'Topic', '--date', '2026-10-15', '--daily-root', self.root / 'daily', '--no-register')
        self.assertEqual(result.returncode, 0, result.stderr)
        root = Path(json.loads(result.stdout)['project_dir'])
        self.assertTrue((root / 'ꙮ/0/Context.md').is_file())

    def test_attachment_evidence_retained_with_hash(self):
        asset = self.put('capture/attachments/proof.txt', 'primary evidence')
        data = {**source(), 'saved_attachments': [{'path': str(asset), 'filename': asset.name,
                                                 'sha256': hashlib.sha256(asset.read_bytes()).hexdigest()}]}
        root = Path(self.init(data)['project_dir'])
        copied = list((root / 'ꘖ/KB/Evidence/Attachments').rglob('proof.txt'))
        self.assertEqual(len(copied), 1)
        self.assertEqual(copied[0].read_bytes(), asset.read_bytes())
        self.assertIn('proof.txt', (root / 'ꘖ/KB/Evidence.md').read_text(encoding='utf-8'))


class CapturedProjectTests(TemporaryCase):
    @unittest.skipUnless(os.environ.get('UPWORK_CAPTURE_DIR'), 'Optional real Upwork captures are not configured')
    def test_real_captures_preserve_description_port_and_curated_work(self):
        capture_root = Path(os.environ['UPWORK_CAPTURE_DIR'])
        captures = [json.loads(path.read_text(encoding='utf-8')) for path in sorted(capture_root.glob('*/source.json'))]
        # Production staging is disposable; permanent intake receipts are reusable fixtures.
        for manifest in sorted(capture_root.glob('**/Evidence/Intake/*.json')):
            receipt = json.loads(manifest.read_text(encoding='utf-8'))
            project = manifest.parents[4]
            entries = {entry['original_relative_provenance']: entry for entry in receipt['entries']}
            data = json.loads((project / entries['source.json']['durable_file']).read_text(encoding='utf-8'))
            for asset in data.get('saved_attachments') or []:
                relative = 'attachments/' + Path(asset['path']).name
                asset['path'] = str(project / entries[relative]['durable_file'])
            captures.append(data)
        self.assertTrue(captures, 'No captures or permanent intake receipts found')
        for data in captures:
            with self.subTest(job_id=data['job_id']):
                kwargs = dict(url_or_id=data['job_id'], extracted_data=data, date_str='2026-10-15',
                              daily_root=self.root / 'daily', register_antigravity=False)
                root = Path(up.initialize_upwork_project(**kwargs)['project_dir'])
                self.assertEqual((root / 'KB/Project.md').read_bytes(), (root / 'ꘖ/KB/Project.md').read_bytes())
                self.assertIn(data['description'], (root / 'ꘖ/KB/Projects.md').read_text(encoding='utf-8'))
                paths = [root / '.md', root / 'KB/Project.md', root / '.agents/context.json',
                         *(root / 'ꘖ/KB').glob('*.md')]
                for file in paths:
                    if file.suffix == '.json':
                        config = json.loads(file.read_text(encoding='utf-8'))
                        config['custom'] = 'CURATED_IN_REAL_CAPTURE_TEST'
                        file.write_text(json.dumps(config), encoding='utf-8')
                    else:
                        file.write_bytes(file.read_bytes() + b'\nCURATED_IN_REAL_CAPTURE_TEST\n')
                expected = {file: file.read_bytes() for file in paths}
                up.initialize_upwork_project(**kwargs)
                self.assertEqual({file: file.read_bytes() for file in paths}, expected)


class IsolationTests(TemporaryCase):
    def test_pending_journal_cannot_be_recovered_into_another(self):
        (self.root / 'ꘖ').mkdir()
        a, b = self.root / 'a', self.root / 'b'
        with patch.object(journal, '_publish', side_effect=OSError('power failure')):
            with self.assertRaises(RuntimeError):
                journal.record_step(a, 'A question', 'A answer')
        receipt = journal.state_dir(a) / '1.json'
        token = json.loads(receipt.read_text(encoding='utf-8'))['token']
        self.assertEqual(journal.record_step(b, 'B question', 'B answer'), 1)
        with self.assertRaises((FileNotFoundError, ValueError)):
            journal.recover_step(b, 1, token)
        self.assertTrue(receipt.exists())
        journal.recover_step(a, 1, token)
        self.assertEqual((a / 'res/1.md').read_text(), 'A answer')
        self.assertEqual((b / 'res/1.md').read_text(), 'B answer')

    def test_two_drafts_in_one_turn_have_distinct_archives(self):
        (self.root / 'ꘖ').mkdir()
        a, b = self.put('a/draft.md', 'first'), self.put('b/draft.md', 'second')
        sa, sb = snapshot_draft(a, 'one_turn'), snapshot_draft(b, 'one_turn')
        self.assertNotEqual(sa, sb)
        self.assertEqual(sa.read_bytes(), b'first')
        self.assertEqual(sb.read_bytes(), b'second')

    def test_incomplete_journal_does_not_replace_context(self):
        config = self.put('context.json', json.dumps({'version': 1, 'output': 'out.md',
            'sections': [{'title': 'Journal', 'journals': ['chat']}]}))
        old = self.put('out.md', 'previous complete context')
        self.put('chat/req/1.md', 'pending')
        with self.assertRaisesRegex(ValueError, 'Incomplete journal'):
            generate(self.root, config)
        self.assertEqual(old.read_text(), 'previous complete context')


class AttachmentTests(TemporaryCase):
    def test_access_denied_and_unloaded_pages_are_not_job_captures(self):
        for page in ({'title': 'Access denied'}, {'body': 'You do not have permission to view this job'}):
            with self.assertRaises(PermissionError):
                decode_page(page, '~02123')
        with self.assertRaisesRegex(ValueError, 'may be unloaded'):
            decode_page({}, '~02123')
        with self.assertRaisesRegex(ValueError, 'does not match'):
            decode_page({'nuxt': '[]'}, '~02123')

    def test_cookie_domain_and_path_boundaries(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self, limit):
                return b'proof'
        cookies = [{'name': name, 'value': 'FAKE', 'domain': domain, 'path': path}
                   for name, domain, path in [('allowed', '.upwork.com', '/jobs'),
                                              ('path_mismatch', '.upwork.com', '/job'),
                                              ('host_mismatch', 'other.upwork.com', '/'),
                                              ('root', 'www.upwork.com', '/')]]
        with patch('urllib.request.build_opener') as opener:
            opener.return_value.open.return_value = Response()
            download_attachment({'fileName': 'proof.txt', 'uri': '/jobs/proof'}, self.root, cookies)
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.get_header('Cookie'), 'allowed=FAKE; root=FAKE')

    def test_paths_cannot_escape_or_use_windows_special_names(self):
        for name in ('../secret', '..\\secret', 'C:\\secret', 'a/b', 'NUL', 'COM1.txt', 'trailing.', '..'):
            with self.assertRaises(ValueError):
                attachment_path(self.root / 'assets', name)
        self.assertEqual(attachment_path(self.root, 'normal.txt'), self.root / 'normal.txt')

    def test_unrelated_initial_host_rejected_before_network(self):
        with patch('urllib.request.build_opener') as opener:
            with self.assertRaises(ValueError):
                download_attachment({'fileName': 'a.txt', 'uri': 'https://upwork.com.example.org/a'}, self.root,
                                    [{'name': 'FAKE', 'value': 'ONLY_TEST'}])
            opener.assert_not_called()

    def test_redirect_cannot_keep_credentials_on_another_host(self):
        req = Request('https://www.upwork.com/a', headers={'Cookie': 'FAKE=1', 'Authorization': 'TEST'})
        result = SafeRedirect().redirect_request(req, None, 302, 'Found', Message(), 'https://upwork.com.example.org/a')
        self.assertFalse(result.has_header('Cookie'))
        self.assertFalse(result.has_header('Authorization'))
        with self.assertRaises(ValueError):
            SafeRedirect().redirect_request(req, None, 302, 'Found', Message(), 'http://www.upwork.com/a')

    def test_tab_selection_requires_exact_job_or_explicit_id(self):
        a = {'type': 'page', 'id': 'a', 'url': 'https://www.upwork.com/jobs/~02123'}
        b = {**a, 'id': 'b'}
        self.assertEqual(select_tab([a], '~02123'), a)
        with self.assertRaises(ValueError):
            select_tab([a, b], '~02123')
        slug = {**a, 'url': 'https://www.upwork.com/jobs/Example-title_~02123?ref=test'}
        self.assertEqual(select_tab([slug], '~02123'), slug)
        for tabs in ([a, b], [{**a, 'url': 'https://upwork.com.evil.org/jobs/~02123'}], [a]):
            with self.assertRaises(ValueError):
                select_tab(tabs, '~02999')
        self.assertEqual(select_tab([a, b], '~02123', 'b'), b)

    def test_docx_and_text_attachments_saved_in_source_and_both_kbs(self):
        import zipfile
        from agent_tools.knowledge import sync_project_attachments_and_kb
        from agent_tools.workflow import attachment_issues

        docx_path = self.root / 'capture/attachments/Expectations.docx'
        docx_path.parent.mkdir(parents=True, exist_ok=True)
        doc_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body>'
            '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Full Funnel Tracking</w:t></w:r></w:p>'
            '<w:p>'
            '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
            '<w:r><w:instrText xml:space="preserve"> HYPERLINK "https://www.loom.com/share/abcd1234ef567890abcd1234ef567890" </w:instrText></w:r>'
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            '<w:r><w:t>Watch Loom Video</w:t></w:r>'
            '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
            '</w:p>'
            '<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>'
            '<w:r><w:rPr><w:b/></w:rPr><w:t>Step 1: </w:t></w:r>'
            '<w:r><w:t>Verify GTM container. Ensure GA4 events fire accurately.</w:t></w:r>'
            '</w:p>'
            '</w:body></w:document>'
        )
        with zipfile.ZipFile(docx_path, 'w') as zf:
            zf.writestr('word/document.xml', doc_xml)
        img_path = self.root / 'capture/attachments/checkout-error.png'
        img_path.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR')

        data = {
            **source(),
            'saved_attachments': [
                {'path': str(docx_path), 'filename': docx_path.name, 'sha256': hashlib.sha256(docx_path.read_bytes()).hexdigest()},
                {'path': str(img_path), 'filename': img_path.name, 'sha256': hashlib.sha256(img_path.read_bytes()).hexdigest()},
            ],
        }
        with patch('agent_tools.upwork_data.extract_loom_video', return_value={}):
            root = Path(up.initialize_upwork_project(
                data['job_id'], domain_or_topic='Topic', date_str='2026-10-15',
                daily_root=self.root / 'daily', extracted_data=data, register_antigravity=False,
            )['project_dir'])

        # §2.1: Every attachment is saved in root source/ folder
        self.assertEqual((root / 'source/Expectations.docx').read_bytes(), docx_path.read_bytes())
        self.assertEqual((root / 'source/checkout-error.png').read_bytes(), img_path.read_bytes())

        # §2.2: Full formatted Markdown of DOCX is in both KBs (byte-identical Project.md + Projects.md + Evidence.md)
        manual_kb = (root / 'KB/Project.md').read_text(encoding='utf-8')
        agent_kb = (root / 'ꘖ/KB/Project.md').read_text(encoding='utf-8')
        projects_kb = (root / 'ꘖ/KB/Projects.md').read_text(encoding='utf-8')
        evidence_kb = (root / 'ꘖ/KB/Evidence.md').read_text(encoding='utf-8')
        self.assertEqual(manual_kb, agent_kb)
        for text in (manual_kb, projects_kb, evidence_kb):
            self.assertIn('# Full Funnel Tracking', text)
            self.assertIn('[Watch Loom Video](https://www.loom.com/share/abcd1234ef567890abcd1234ef567890)', text)
            self.assertIn('- Step 1: Verify GTM container.', text)

        # Before supplying video transcript and image analysis, attachment_issues flags §§2.3 and 2.4
        issues_before = {item['code'] for item in attachment_issues(root)}
        self.assertIn('attachment.video_incomplete', issues_before)
        self.assertIn('attachment.image_incomplete', issues_before)

        # §§2.3 & 2.4: Syncing video transcript and image transcription updates both KBs and clears all attachment issues
        media_descriptions = {
            'https://www.loom.com/share/abcd1234ef567890abcd1234ef567890': (
                '# Видео:\n'
                'https://www.loom.com/share/abcd1234ef567890abcd1234ef567890\n\n'
                '# Ключевые моменты устного комментария (дополнения к тексту документа):\n'
                '- **Контекст:** Клиент показывает настройки контейнера GTM.\n\n'
                '# Полная расшифровка аудиозаписи:\n'
                '- **[00:00]** Hello, here is our current GTM setup and what needs fixing.'
            ),
            'checkout-error.png': (
                '# 1. Дословный текст на изображении\n'
                '- «Payment failed: invalid merchant configuration»\n'
                '- Кнопка «Try Again»\n\n'
                '# 2. Описание элементов интерфейса (UI)\n'
                '- Модальное окно ошибки чекаута с красным баннером «Error».\n\n'
                '# 3. Соотношение со словами клиента\n'
                '## 3.1. Подтверждения слов клиента\n'
                '### 1\n'
                '- **Суть:** Скриншот подтверждает сбой оплаты в чекауте.\n'
                '- **Доводы за:** Текст «Payment failed: invalid merchant configuration» прямо указывает на ошибку конфигурации.\n'
                '- **Доводы против:** Скриншот не показывает серверный лог шлюза.\n'
                '- **Оценка:** `95%`\n\n'
                '## 3.2. Противоречия словам клиента\n'
                '### 1\n'
                '- **Суть:** Ошибка возникает на шаге инициализации, а не после 3DS.\n'
                '- **Доводы за:** Поле карты ещё не активно на экране.\n'
                '- **Доводы против:** Клиент мог сделать скриншот после сброса формы.\n'
                '- **Оценка:** `70%`'
            ),
        }
        sync_project_attachments_and_kb(root, media_descriptions=media_descriptions)
        self.assertEqual((root / 'KB/Project.md').read_bytes(), (root / 'ꘖ/KB/Project.md').read_bytes())
        self.assertEqual(attachment_issues(root), [])


class RPCTests(unittest.IsolatedAsyncioTestCase):
    async def test_events_and_unrelated_responses_do_not_complete_call(self):
        class WebSocket:
            def __init__(self):
                self.sent = []
                self.messages = iter([{'method': 'Runtime.event'}, {'id': 99, 'result': {'wrong': True}},
                                      {'id': 1, 'result': {'expected': True}}])
            async def send(self, data):
                self.sent.append(json.loads(data))
            async def recv(self):
                return json.dumps(next(self.messages))
        websocket = WebSocket()
        result = await RPC(websocket).call('Runtime.test')
        self.assertEqual(result, {'expected': True})
        self.assertEqual(websocket.sent[0]['id'], 1)

    async def test_unresponsive_browser_has_bounded_diagnostic(self):
        class WebSocket:
            async def send(self, data):
                pass
            async def recv(self):
                await asyncio.Future()
        with self.assertRaisesRegex(TimeoutError, 'Runtime.test did not respond'):
            await RPC(WebSocket(), timeout=0.01).call('Runtime.test')


class EvidenceTests(TemporaryCase):
    def test_domain_mentions_include_vendors_and_keep_full_hostnames(self):
        self.assertEqual(extract_candidate_domains(['https://www.stape.io x.example.co.uk and sub.client.example', 'stape.io']),
                         ['stape.io', 'x.example.co.uk', 'sub.client.example'])

    def test_embedded_fences_do_not_end_the_manual_description(self):
        value = source()
        value['description'] = 'Original text\n~~~\nLiteral source\n~~~'
        manual = format_kb_project_md(value)
        self.assertIn('~~~~markdown', manual)
        self.assertIn('Literal source\n~~~\n~~~~', manual)

    def test_malformed_analysis_has_actionable_errors(self):
        cases = [[], {**analysis(), 'notes': []}, {**analysis(), 'concerns': [None]},
                 {**analysis(), 'causes': [{**claim('H-2'), 'addresses': 'H-CONCERN-1'}]},
                 {**analysis(), 'concerns': [{**claim('H-1'), 'for': [None]}]}]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_analysis(value)

    def test_windows_file_uris_and_absolute_paths(self):
        target = self.put('with space/target.md', '## F-1\nEvidence')
        for uri in (target.as_uri(), target.as_posix()):
            path = self.put('links.md', f'[Evidence](<{uri}#f-1>)')
            self.assertEqual(validate_file(path, local_anchors=True), [])

    def test_analysis_links_causes_to_concerns_and_methods_to_causes(self):
        value = analysis()
        validate_analysis(value)
        output = render_analysis(value)
        self.assertIn('[H-CAUSE-1](#h-cause-1)', output)
        file = self.put('analysis.md', output)
        self.assertEqual(validate_file(file, local_anchors=True), [])
        value['methods'][0]['addresses'] = ['NOT-A-CLAIM']
        with self.assertRaises(ValueError):
            validate_analysis(value)

    def test_missing_counterevidence_probability_or_documentation_anchor_is_rejected(self):
        for mutate in (lambda v: v['causes'][0].update(against=[]),
                       lambda v: v['causes'][0].update(probability_percent=None),
                       lambda v: v['methods'][0].pop('criterion'),
                       lambda v: v['concerns'][0]['for'][0].update(documentation=True, source='https://example.org/no-anchor')):
            value = analysis()
            mutate(value)
            with self.assertRaises(ValueError):
                validate_analysis(value)

    def test_cross_file_markdown_anchors_and_missing_file(self):
        self.put('target.md', '# H-1\n\n# Repeated\n# Repeated\n')
        file = self.put('source.md', '[one](target.md#h-1) [second](target.md#repeated-1)')
        self.assertEqual(validate_file(file, local_anchors=True), [])
        file.write_text('[bad](absent.md#anything) [wrong](target.md#absent)', encoding='utf-8')
        errors = validate_file(file, local_anchors=True)
        self.assertEqual(len(errors), 2)

    def test_json_pointer_is_checked(self):
        self.put('source.json', '{"description":"exact"}')
        document = self.put('doc.md', '[valid](source.json#/description)')
        self.assertEqual(validate_file(document), [])
        document.write_text('[invalid](source.json#/missing)', encoding='utf-8')
        self.assertTrue(validate_file(document))


class RegistrationTests(TemporaryCase):
    def test_existing_native_file_uri_is_matched_without_replacing_settings(self):
        root = self.root / '2026/10/15/1 - Topic'
        root.mkdir(parents=True)
        original = {'id': 'existing', 'name': 'My title',
                    'projectResources': {'resources': [{'folderUri': root.as_uri()}]},
                    'settings': {'keep': True}}
        record = self.put('native-projects/existing.json', json.dumps(original))
        before = record.read_bytes()
        folders = self.put('folders.json', '{"folders":[],"projectFolderMap":{}}')
        result = up.register_antigravity_project(root, 'Topic', projects_dir=record.parent,
                                                 folders_json_path=folders)
        self.assertEqual(result['project_id'], 'existing')
        self.assertEqual(record.read_bytes(), before)
        self.assertEqual(result['folder_path'], 'Upwork / Proposals / 2026 / 10 / 15')
        self.assertEqual(json.loads(folders.read_text())['projectFolderMap']['existing'], result['folder_id'])

    def test_missing_or_wrong_folders_store_does_not_publish_ungrouped_project(self):
        root = self.root / '2026/10/15/1 - Topic'
        root.mkdir(parents=True)
        projects = self.root / 'native-projects'
        for filename in ('missing.json', 'wrong.json'):
            if filename == 'wrong.json':
                self.put(filename, '{"folders":[],"assignments":{}}')
            with self.assertRaises((FileNotFoundError, ValueError)):
                up.register_antigravity_project(root, 'Topic', projects_dir=projects,
                                                folders_json_path=self.root / filename)
            self.assertEqual(list(projects.glob('*.json')), [])

    def test_branch_is_reused_by_parent_and_date_with_other_assignments_preserved(self):
        data = {'folders': [{'id': 'work', 'name': 'upwork', 'parentId': None},
                            {'id': 'other-15', 'name': '15', 'parentId': 'work'}],
                'projectFolderMap': {'manual-project': 'other-15'}, 'collapsedFolders': ['keep']}
        folders = self.put('folders.json', json.dumps(data))
        root = self.root / '2026/10/14/1 - Topic'
        root.mkdir(parents=True)
        kwargs = dict(projects_dir=self.root / 'native', folders_json_path=folders)
        result = up.register_antigravity_project(root, 'Topic', **kwargs)
        before = folders.read_bytes()
        self.assertEqual(up.register_antigravity_project(root, 'Topic', **kwargs), result)
        self.assertEqual(folders.read_bytes(), before)
        actual = json.loads(before)
        self.assertEqual(actual['projectFolderMap']['manual-project'], 'other-15')
        self.assertEqual(actual['collapsedFolders'], ['keep'])
        self.assertNotIn('assignments', actual)
        node = next(x for x in actual['folders'] if x['id'] == result['folder_id'])
        self.assertEqual(node['name'], '14')
        chain = []
        while node:
            chain.insert(0, node['name'])
            node = next((x for x in actual['folders'] if x['id'] == node['parentId']), None)
        self.assertEqual(chain, ['upwork', 'Proposals', '2026', '10', '14'])

    def test_global_install_preserves_other_customizations_and_is_idempotent(self):
        original = {'inherits': [{'path': 'other.json'}], 'entries': [{'path': 'my-skills'}]}
        config = self.put('global/skills.json', json.dumps(original)).parent
        up.install_global_customizations(config)
        before = (config / 'skills.json').read_bytes()
        up.install_global_customizations(config)
        self.assertEqual((config / 'skills.json').read_bytes(), before)
        value = json.loads(before)
        self.assertEqual(value['inherits'], original['inherits'])
        self.assertIn(original['entries'][0], value['entries'])

    def test_parallel_registration_retains_all_assignments(self):
        folders = self.put('folders.json', '{"folders":[],"projectFolderMap":{}}')
        projects = self.root / 'native-projects'
        roots = [self.root / f'2026/10/15/{i} - Topic' for i in range(1, 9)]
        for root in roots:
            root.mkdir(parents=True)
        def register(root):
            return up.register_antigravity_project(root, 'Topic', projects_dir=projects, folders_json_path=folders)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(register, roots))
        actual = json.loads(folders.read_text(encoding='utf-8'))
        self.assertEqual(set(actual['projectFolderMap']), {x['project_id'] for x in results})
        same = register(roots[0])
        self.assertEqual(same['project_id'], results[0]['project_id'])


