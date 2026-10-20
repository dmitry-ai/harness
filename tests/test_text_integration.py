"""End-to-end offline text checks; native verdicts below are explicit test fixtures."""

from copy import deepcopy
import argparse
import json
from unittest.mock import patch
import uuid

from test_text_workflow import TextWorkspaceCase, codes
from agent_tools import journal, text_review, text_workflow, text_claims, text_sources
from agent_tools.links import Page
from agent_tools.research import json_data


class TextReviewTests(TextWorkspaceCase):
    def setUp(self):
        super().setUp()
        self.registry()
        self.target, self.op = self.start()
        self.candidate = '1. The captured page contains Alternative.\n'
        self.checked = text_workflow.check(self.project, self.op['id'], self.candidate, self.manifest(self.candidate))
        self.parent = str(uuid.uuid4())

    def package(self, **spec):
        return text_review.prepare(self.project, self.checked['check'], self.parent, spec)

    def report(self, package, *, result='approved', findings=None):
        return {'schema_version': 2, 'package': package['package'], 'package_sha256': package['package_sha256'],
            'scope': list(text_review.SCOPES), 'result': result, 'findings': findings or [],
            'claim_reviews': [{'claim_id': claim['claim_id'], 'observed': 'The saved capture contains Alternative.',
                'inferred': 'Only literal presence at this captured URL is stated.', 'method': 'Read the exact saved response bytes.',
                'alternatives': 'The live page may subsequently change.', 'limits': 'One captured page at one time.',
                'falsification': 'Absence of this literal text would falsify the statement.',
                'raw_vs_criteria': 'Literal presence is compared to literal presence, without inferring execution.',
                'test_alignment': {'target_claim': claim['essence'], 'tested_claim': 'The captured page contains Alternative.',
                    'relationship': 'direct', 'rationale': 'The literal excerpt is present in the primary response.',
                    'counterexample': 'A later changed live page would not falsify this historical capture.'},
                'text_checks': {key: 'Saved literal capture supports this one-page assertion; no causal, numerical or owner claims.' for key in text_review.TEXT_CHECKS},
                'outcome': 'supported'} for claim in package['claims']]}

    def record_fixture(self, package, reviewer=None, **kwargs):
        reviewer = reviewer or str(uuid.uuid4())
        report = self.report(package, **kwargs)
        final = json.dumps(report, ensure_ascii=False)
        native = {'surface': 'codex-ui', 'status': 'completed', 'parent_id': self.parent, 'reviewer_id': reviewer,
                  'final_response': final, 'final_response_sha256': text_claims.digest(final.encode())}
        path = self.project_file('ꘖ/KB/Evidence/Reviews/' + reviewer + '-fixture.json', json.dumps(native))
        with patch('agent_tools.metrics.verify_native_proof', return_value=native):
            return text_review.record(self.project, final.encode(), parent_id=self.parent, reviewer_id=reviewer,
                native_evidence=path.relative_to(self.project).as_posix())

    def verified(self):
        return patch('agent_tools.metrics.verify_native_proof', side_effect=lambda root, native, package=None: native)

    def test_independent_routine_verdict_apply_and_exact_journal(self):
        package = self.package()
        self.record_fixture(package)
        with self.verified():
            receipt = text_workflow.apply(self.project, self.checked['check'])
            self.assertEqual(self.target.read_bytes(), self.candidate.encode())
            self.assertTrue(text_workflow.gate(self.project, publication=True)['valid'])
            result = text_workflow.record_answer(self.project, self.project/'journal', self.op['requests'], 'Updated the captured observation.\n', 'fixture-turn')
        self.assertEqual(receipt['status'], 'applied')
        self.assertEqual(result['journal_steps'], [1])
        self.assertEqual((self.project/'journal/req/1.md').read_bytes(), self.op['requests'][0].encode())
        self.assertFalse((self.project/'ꘖ/project.json').exists())

    def test_parent_cannot_authorize_its_own_text(self):
        package = self.package()
        report = self.report(package); report['review_kind'] = 'self_review'
        with self.assertRaisesRegex(ValueError, 'independent'):
            text_review.record(self.project, json_data(report), parent_id=self.parent, reviewer_id=self.parent, native_evidence=None)

    def test_significant_subject_needs_two_distinct_reviewers(self):
        package = self.package(task_flags=['new_causal_analysis'])
        first = self.record_fixture(package)
        with self.verified(), self.assertRaisesRegex(ValueError, 'two reviewers'):
            text_workflow.apply(self.project, self.checked['check'])
        self.record_fixture(package, reviewer=first['reviewer_id'])
        with self.verified(), self.assertRaises(ValueError):
            text_workflow.apply(self.project, self.checked['check'])
        self.record_fixture(package)
        with self.verified():
            self.assertEqual(text_workflow.apply(self.project, self.checked['check'])['status'], 'applied')

    def test_map_change_does_not_inherit_an_old_check_approval(self):
        self.record_fixture(self.package())
        manifest = self.manifest(self.candidate)
        manifest['blocks'][0]['new_content'] = 'A revised declaration requiring review.'
        changed = text_workflow.check(self.project, self.op['id'], self.candidate, manifest)
        with self.verified(), self.assertRaisesRegex(ValueError, 'approval'):
            text_workflow.apply(self.project, changed['check'])

    def test_same_rejected_subject_cannot_be_reset_by_a_new_operation_path(self):
        initial = self.package()
        finding = {'id': 'scope-finding', 'severity': 'significant', 'status': 'open',
                   'description': 'The sample boundary requires independent confirmation.', 'claim_ids': ['text-1']}
        self.record_fixture(initial, result='needs_changes', findings=[finding])
        other = text_workflow.begin(self.project, {key: value for key, value in self.op.items()
            if key in ('kind','mode','changes','target','goal','requests')})
        checked = text_workflow.check(self.project, other['id'], self.candidate, self.manifest(self.candidate))
        package = text_review.prepare(self.project, checked['check'], self.parent)
        self.assertEqual(initial['subject_sha256'], package['subject_sha256'])
        self.assertEqual(package['risk'], 'significant')
        with self.verified(), self.assertRaises(ValueError):
            text_workflow.apply(self.project, checked['check'])


class TextBoundaryTests(TextWorkspaceCase):
    def test_dom_cli_dispatch_keeps_the_explicit_authorized_session(self):
        from agent_tools import operations
        parser = argparse.ArgumentParser()
        operations.add_parsers(parser.add_subparsers(dest='command', required=True))
        args = parser.parse_args(['capture-dom', str(self.project), '--url', 'https://example.org/',
                                  '--tab-id', 'selected', '--session-id', 'authorized-fixture'])
        with patch('agent_tools.research.capture_dom', return_value={'fixture': True}) as capture:
            self.assertEqual(operations.execute(args), {'fixture': True})
        self.assertEqual(capture.call_args.kwargs['session_id'], 'authorized-fixture')
        self.assertNotIn('port', capture.call_args.kwargs)

    def test_application_hashing_is_distinct_from_service_fingerprints(self):
        from agent_tools.proposal import lint_text
        valid = lint_text('1. The tag hashes the email address with SHA-256.\n')
        self.assertNotIn('APP-HASH', {finding.rule for finding in valid})
        invalid = lint_text('1. The response body has SHA-256 `1234`.\n')
        self.assertIn('APP-HASH', {finding.rule for finding in invalid})

    def test_matching_request_blocks_direct_write_but_unrelated_journal_is_allowed(self):
        target, op = self.start()
        target.write_text('Direct unreviewed overwrite.\n', encoding='utf-8')
        chat = self.project/'journal'
        self.assertEqual(journal.record_step(chat, 'Which browser profile is active?', 'The configured profile is C1.\n'), 1)
        with self.assertRaisesRegex(ValueError, 'without a current apply receipt'):
            journal.record_step(chat, op['requests'][0], 'Updated the proposal.\n')
        self.assertEqual(target.read_text(), 'Direct unreviewed overwrite.\n')

    def test_missing_map_is_an_invalid_result_instead_of_a_crash(self):
        _, op = self.start()
        result = text_workflow.check(self.project, op['id'], '1. A substantive new claim.\n')
        self.assertFalse(result['valid'])
        self.assertIn('text.map', codes(result))

    def test_links_only_allows_url_presentation_but_preserves_crlf_and_anchor_words(self):
        original = '1. Read https://example.org/a\r\n'
        target, op = self.start(original, changes='links')
        base = original.encode()
        allowed = '1. Read [**example.org**/a](https://example.org/a)\r\n'
        self.assertEqual(text_workflow.scope_issues(op, base, allowed), [])
        self.assertIn('text.scope', codes(text_workflow.scope_issues(op, base, allowed.replace('\r\n','\n'))))
        self.assertIn('text.scope', codes(text_workflow.scope_issues(op, base, '1. Read [unrelated label](https://example.org/a)\r\n')))
        self.assertEqual(text_workflow.scope_issues(op, b'1. Read https://example.org/a.\r\n',
                         '1. Read [**example.org**/a](https://example.org/a).\r\n'), [])

    def test_section_scope_covers_group_headers_and_protects_part_title(self):
        source = '# I. Analysis\n## 1\n<a name="§I.1"></a>\n### 1.1\n<a name="§I.1.1"></a>\nFact.\n# II. Recommendations\n## 1\n<a name="§II.1"></a>\nAct.\n'
        op = {'kind':'article','mode':'edit','changes':'prose','allow_sections':['II.1']}
        self.assertIn('text.outside_scope', codes(text_workflow.scope_issues(op,source.encode(),source.replace('# I. Analysis','# I. Changed title'))))
        op['allow_sections'] = ['I.1']
        self.assertEqual(text_workflow.scope_issues(op,source.encode(),source.replace('Fact.','Another fact.')), [])
        self.assertIn('text.outside_scope', codes(text_workflow.scope_issues(op,source.encode(),source.replace('Act.','Another action.'))))

    def test_renumber_scope_accepts_external_spacing_without_rebinding_its_number(self):
        base = '1. Read 11 CCR § 7025.\n2. See §1.\n'
        op = {'kind':'proposal','mode':'edit','changes':'renumber','allow_sections':[]}
        self.assertEqual(text_workflow.scope_issues(op,base.encode(),base.replace('§ 7025','§7025')), [])
        self.assertIn('text.scope', codes(text_workflow.scope_issues(op,base.encode(),base.replace('§ 7025','§7026'))))

    def test_network_source_checks_distinguish_missing_anchor_and_skip_inline_code(self):
        seen = []
        def fetch(url, timeout):
            seen.append(url)
            return Page(url,200,'text/html','<h2 id="real">Real section</h2>')
        self.assertEqual(text_sources.check_links('Read [docs](https://example.org/#real).\n`https://not-a-source.invalid`',fetcher=fetch), [])
        self.assertNotIn('https://not-a-source.invalid', seen)
        self.assertTrue(text_sources.check_links('https://example.org/#invented',fetcher=fetch))

    def test_cli_proposal_profile_and_fields_have_real_exit_status(self):
        proposal = self.project_file('candidate.md', '1. The website contains a form.\n')
        self.assertEqual(self.cli('df_proposal','lint',proposal).returncode,0)
        fields = self.project_file('fields.json',json.dumps({'Cover Letter':'abcdef'}))
        limits = self.project_file('limits.json',json.dumps({'Cover Letter':5}))
        self.assertEqual(self.cli('df_proposal','fields','--fields',fields,'--limits',limits).returncode,1)
