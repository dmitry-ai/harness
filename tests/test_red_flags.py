"""Project screening regressions: visible risks, evidence links and card preservation."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from test_agent_tools import TemporaryCase
from test_onboarding import analysis, claim
from agent_tools.analysis import analysis_issues, publish_analysis, render_analysis
from agent_tools.red_flags import START, END, sync_project_red_flags


class RedFlagTests(TemporaryCase):
    def setUp(self):
        super().setUp()
        # This is a synthetic version of an agency with no identifiable client site.
        self.original = b'\xef\xbb\xbf# Project\r\nhttps://upwork.com/jobs/~021234567890\r\n\r\n# Notes\r\nKeep all of my notes.\r\n'
        self.card = self.root / '.md'
        self.card.write_bytes(self.original)
        self.value = analysis()
        self.value['identity'] = [claim('H-IDENTITY-CLIENT'), claim('H-SITE-1')]
        self.value['identity'][0]['essence'] = 'The client runs an agency for outside clients.'
        self.value['identity'][1]['essence'] = 'The target site remains unidentified after the available research.'
        self.value['red_flags'] = [
            {'id': 'RF-CLIENT-INTERMEDIARY', 'status': 'confirmed',
             'summary': 'The agency hires for an end client.', 'basis_ids': ['H-IDENTITY-CLIENT']},
            {'id': 'RF-WEBSITE-UNIDENTIFIED', 'status': 'unresolved',
             'summary': 'Research did not establish the target checkout; the client must supply its URL.', 'basis_ids': ['H-SITE-1']},
        ]
        self.source = self.put('ꘖ/KB/Analysis.json', json.dumps(self.value, ensure_ascii=False))

    def test_both_risks_precede_technical_analysis_and_are_duplicated_in_card(self):
        result = publish_analysis(self.source)
        self.assertEqual(result['status'], 'published')
        report = self.source.with_suffix('.md').read_text(encoding='utf-8')
        card = self.card.read_text(encoding='utf-8-sig')
        for text in (report, card):
            self.assertLess(text.index('Red Flags'), text.index('H-IDENTITY-CLIENT'))
            self.assertIn('Оба Red Flags одновременно', text)
            self.assertIn('Клиент — посредник', text)
            self.assertIn('Сайт, над которым предстоит работать, не установлен', text)
        self.assertLess(report.index('Red Flags'), report.index('# 1.'))
        self.assertLess(card.index('Red Flags'), card.index('https://upwork'))
        self.assertIn('ꘖ/KB/Analysis.json#/identity/1', card)
        self.assertIn('#h-site-1', report)
        updated = self.card.read_bytes()
        begin, end = updated.index(START), updated.index(END) + len(END) + 4
        self.assertEqual(updated[:begin] + updated[end:], self.original)

    def test_each_risk_can_be_shown_alone_without_combination_warning(self):
        for flag in self.value['red_flags']:
            value = deepcopy(self.value)
            value['red_flags'] = [flag]
            report = render_analysis(value)
            self.assertIn('Red Flags — 1', report)
            self.assertNotIn('Оба Red Flags одновременно', report)

    def test_suspected_intermediary_is_not_reported_as_confirmed(self):
        self.value['red_flags'][0]['status'] = 'suspected'
        report = render_analysis(self.value)
        self.assertIn('Статус: гипотеза', report)
        self.assertIn('посредничество пока является гипотезой', report)
        self.assertNotIn('Статус: подтверждено', report)

    def test_no_flags_does_not_create_warning_or_change_original_card(self):
        self.value['red_flags'] = []
        self.assertNotIn('Red Flags', render_analysis(self.value))
        self.assertEqual(sync_project_red_flags(self.root, self.value)['status'], 'unchanged')
        self.assertEqual(self.card.read_bytes(), self.original)

    def test_repeated_render_preserves_new_user_notes_and_does_not_duplicate_block(self):
        publish_analysis(self.source)
        self.card.write_bytes(self.card.read_bytes() + b'Another note.\r\n')
        result = publish_analysis(self.source)
        self.assertEqual(result['project_card']['status'], 'unchanged')
        self.assertEqual(self.card.read_bytes().count(START), 1)
        self.assertTrue(self.card.read_bytes().endswith(b'Another note.\r\n'))

    def test_resolved_risks_update_both_surfaces_and_keep_original_card_history(self):
        publish_analysis(self.source)
        self.value['red_flags'] = [self.value['red_flags'][0]]
        self.source.write_text(json.dumps(self.value), encoding='utf-8')
        publish_analysis(self.source)
        card = self.card.read_text(encoding='utf-8-sig')
        self.assertNotIn('Оба Red Flags одновременно', card)
        self.assertNotIn('Сайт, над которым предстоит работать, не установлен', card)
        self.value['red_flags'] = []
        self.source.write_text(json.dumps(self.value), encoding='utf-8')
        publish_analysis(self.source)
        self.assertEqual(self.card.read_bytes(), self.original)
        self.assertNotIn('Red Flags', self.source.with_suffix('.md').read_text(encoding='utf-8'))
        self.assertIn(self.original, [p.read_bytes() for p in (self.root / 'ꘖ/data/red-flags-history').glob('*.md')])

    def test_legacy_analysis_does_not_silently_clear_existing_risks(self):
        sync_project_red_flags(self.root, self.value)
        previous = self.card.read_bytes()
        del self.value['red_flags']
        self.assertEqual(analysis_issues(self.value), [])
        self.assertEqual(sync_project_red_flags(self.root, self.value)['status'], 'unassessed')
        self.assertEqual(self.card.read_bytes(), previous)

    def test_manual_warning_edits_and_malformed_markers_are_preserved_as_conflicts(self):
        sync_project_red_flags(self.root, self.value)
        self.card.write_bytes(self.card.read_bytes().replace(b'The agency hires', b'My edited assessment'))
        changed = self.card.read_bytes()
        self.assertEqual(sync_project_red_flags(self.root, self.value)['status'], 'conflict')
        self.assertEqual(self.card.read_bytes(), changed)
        self.card.write_bytes(changed.replace(END, b''))
        malformed = self.card.read_bytes()
        self.assertEqual(sync_project_red_flags(self.root, self.value)['status'], 'conflict')
        self.assertEqual(self.card.read_bytes(), malformed)

    def test_unknown_duplicate_and_unsupported_basis_cannot_be_published(self):
        mutations = [
            lambda value: value.update(red_flags={}),
            lambda value: value['red_flags'].append(None),
            lambda value: value['red_flags'][0].update(id='UNKNOWN'),
            lambda value: value['red_flags'].append(deepcopy(value['red_flags'][0])),
            lambda value: value['red_flags'][0].update(status='unresolved'),
            lambda value: value['red_flags'][0].update(summary=''),
            lambda value: value['red_flags'][0].update(basis_ids=['MISSING']),
            lambda value: value['red_flags'][0].update(basis_ids=['M-1']),
        ]
        for mutate in mutations:
            value = deepcopy(self.value)
            mutate(value)
            with self.subTest(value=value['red_flags']):
                self.assertTrue(analysis_issues(value))
                with self.assertRaises(ValueError):
                    sync_project_red_flags(self.root, value)
                self.assertEqual(self.card.read_bytes(), self.original)

    def test_standalone_input_never_updates_project_card(self):
        standalone = self.put('standalone.json', json.dumps(self.value))
        result = publish_analysis(standalone)
        self.assertNotIn('project_card', result)
        self.assertEqual(self.card.read_bytes(), self.original)

    def test_both_cli_entrypoints_sync_card_and_return_conflicts(self):
        for command in ('render-analysis', 'validate-analysis'):
            with self.subTest(command=command):
                args = (command, self.source)
                if command == 'validate-analysis':
                    args += ('--render', self.source.with_suffix('.md'), '--format', 'json')
                result = self.cli('upwork_project', *args)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('Red Flags', self.card.read_text(encoding='utf-8-sig'))
                self.card.write_bytes(self.card.read_bytes().replace(b'The agency hires', b'Manual change'))
                previous = self.card.read_bytes()
                result = self.cli('upwork_project', *args)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(self.card.read_bytes(), previous)
                # Restore the known original outside the next CLI invocation.
                self.card.write_bytes(self.original)


if __name__ == '__main__':
    unittest.main()
