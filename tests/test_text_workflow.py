"""Offline client-text transactions and adversarial preservation checks.

These fixtures have a real v3 primary capture and no five-stage job workflow.
The tests exercise public read/check/apply behavior, not implementation strings.
"""

from copy import deepcopy
import json
import os

from test_agent_tools import TemporaryCase
from test_evidence_contract import claim_metadata, v3_analysis
from agent_tools import text_claims, text_workflow
from agent_tools.claims import claim_digest, claim_index


def codes(result):
    issues = result['issues'] if isinstance(result, dict) else result
    return {issue['code'] for issue in issues}


class TextWorkspaceCase(TemporaryCase):
    def setUp(self):
        super().setUp()
        self.project = self.root / 'plain-text-workspace'
        self.project.mkdir()

    def project_file(self, relative, text):
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode('utf-8'))
        return path

    def registry(self, value=None):
        if value is None:
            captured = v3_analysis(self.project)
            value = {'schema_version': 3, 'facts': captured['facts']}
        return text_claims.save_registry(self.project, value), value

    def start(self, base='1. The captured page contains the concern.\n', **overrides):
        relative = overrides.get('target', 'result/EN/proposal.md')
        target = self.project_file(relative, base)
        spec = {'kind': 'proposal', 'mode': 'edit', 'changes': 'prose',
                'target': relative, 'goal': 'Explain the observed page content.',
                'requests': ['Revise the specified proposal only.']}
        spec.update(overrides)
        return target, text_workflow.begin(self.project, spec)

    def manifest(self, text, *, kind='proposal', ids=('F-PRIMARY-1',), role='observation'):
        return {'schema_version': 1, 'registry': 'ꘖ/KB/TextClaims.json', 'blocks': [
            {'key': 'text-' + str(index), 'section': block['section'],
             'text_sha256': text_claims.digest(block['text'].encode()),
             'role': role, 'goal_basis': 'The requested answer concerns this observed content.',
             'new_content': 'This point adds the captured page content.', 'claim_ids': list(ids),
             **({'nonfactual_basis': 'Exact commercial offer, not a claim about an observed system.'}
                if role == 'nonfactual' else {})}
            for index, block in enumerate(text_claims.blocks(text, kind), 1)]}


class TextMapTests(TextWorkspaceCase):
    def test_standalone_proposal_map_needs_no_five_analysis_stages(self):
        self.registry()
        candidate = '1. The captured page contains the concern.\n'
        target, op = self.start()
        result = text_workflow.check(self.project, op['id'], candidate, self.manifest(candidate))
        self.assertTrue(result['valid'], result['issues'])
        self.assertTrue((self.project / 'ꘖ/data/text-project.json').is_file())
        self.assertFalse((self.project / 'ꘖ/project.json').exists())
        self.assertFalse((self.project / 'ꘖ/KB/Analysis.json').exists())
        self.assertEqual(result['claim_versions'].keys(), {'F-PRIMARY-1'})
        self.assertEqual(target.read_text(encoding='utf-8'), candidate)

    def test_limited_claim_rejects_lazy_conditional_qualification(self):
        captured = v3_analysis(self.project)
        captured['facts'][0]['verification_status'] = 'limited'
        captured['facts'][0]['missing_checks'] = ['Verify on mobile viewport.']
        self.registry({'schema_version': 3, 'facts': captured['facts']})
        candidate = '1. The captured page contains the concern if valid.\n'
        target, op = self.start()
        manifest = self.manifest(candidate)
        manifest['blocks'][0]['qualification'] = 'if'
        result = text_workflow.check(self.project, op['id'], candidate, manifest)
        self.assertFalse(result['valid'])
        self.assertIn('text.qualification_lazy', codes(result))

        candidate_ok = '1. The captured page contains the concern for desktop-only.\n'
        manifest_ok = self.manifest(candidate_ok)
        manifest_ok['blocks'][0]['qualification'] = 'desktop-only'
        result_ok = text_workflow.check(self.project, op['id'], candidate_ok, manifest_ok)
        self.assertTrue(result_ok['valid'], result_ok['issues'])

    def test_map_includes_proposal_continuations_and_literal_evidence(self):
        candidate = ('1. The captured page contains the concern.\n'
                     'The captured page also contains Alternative.\n'
                     '```text\nThe concern\n```\n\n'
                     '2. The next point follows.\n')
        blocks = text_claims.blocks(candidate, 'proposal')
        self.assertEqual([block['section'] for block in blocks], ['1', '2'])
        self.assertIn('The captured page also contains Alternative.', blocks[0]['text'])
        self.assertIn('```text\nThe concern\n```', blocks[0]['text'])
        self.assertIn('The captured page also contains Alternative.', blocks[0]['prose'])

    def test_article_grouping_node_does_not_duplicate_its_child_claim(self):
        candidate = ('# I. Analysis\n## 1\n<a name="I.1"></a>\n'
                     '### 1.1\n<a name="I.1.1"></a>\nThe concern is present.\n'
                     '# II. Recommendations\n## 1\n<a name="II.1"></a>\n'
                     '**[§I.1.1](#I.1.1)** → inspect the captured page.\n')
        mapped = text_claims.blocks(candidate, 'article')
        self.assertEqual([block['section'] for block in mapped], ['I.1.1', 'II.1'])

    def test_stale_block_bytes_or_missing_coverage_fail(self):
        self.registry()
        original = '1. The captured page contains the concern.\n'
        manifest = self.manifest(original)
        changed = '1. The captured page contains Alternative.\n'
        self.assertIn('text.block_version', codes(text_claims.validate_map(self.project, changed, 'proposal', manifest)))
        manifest['blocks'] = []
        self.assertIn('text.coverage', codes(text_claims.validate_map(self.project, original, 'proposal', manifest)))

    def test_substantive_paragraph_cannot_be_unmapped_or_unsourced(self):
        candidate = '1. The page contains a claim.\n'
        result = text_claims.validate_map(self.project, candidate, 'proposal', self.manifest(candidate, ids=()))
        self.assertIn('text.unsourced', codes(result))

    def test_explicit_offer_can_be_nonfactual_without_a_registry(self):
        candidate = '1. Fix the listener for $50.\n'
        result = text_claims.validate_map(self.project, candidate, 'proposal',
                                         self.manifest(candidate, ids=(), role='nonfactual'))
        self.assertTrue(result['valid'], result['issues'])
        self.assertFalse((self.project / 'ꘖ/KB/TextClaims.json').exists())

    def test_numeric_measurement_cannot_come_from_claim_wording_alone(self):
        self.registry()
        candidate = '1. The captured page contains 47 records.\n'
        result = text_claims.validate_map(self.project, candidate, 'proposal', self.manifest(candidate))
        self.assertIn('text.number', codes(result))


class TextTransactionTests(TextWorkspaceCase):
    def test_propose_creates_reviewable_candidate_without_writing_target(self):
        self.registry()
        original = '1. The captured page contains the concern.\n'
        target, op = self.start(original, mode='propose')
        candidate = '1. The captured page contains Alternative.\n'
        checked = text_workflow.check(self.project, op['id'], candidate, self.manifest(candidate))
        self.assertTrue(checked['valid'], checked['issues'])
        self.assertEqual(target.read_bytes(), original.encode())
        self.assertTrue((self.project / checked['candidate']).is_file())
        with self.assertRaisesRegex(ValueError, 'proposes/inspects'):
            text_workflow.apply(self.project, checked['check'])
        self.assertEqual(target.read_bytes(), original.encode())

    def test_manual_change_after_check_preserves_the_users_new_bytes(self):
        target, op = self.start('1. The queue refers to §3.\n\n3. The handler runs.\n', changes='renumber')
        candidate = '1. The queue refers to §2.\n\n2. The handler runs.\n'
        checked = text_workflow.check(self.project, op['id'], candidate)
        self.assertTrue(checked['valid'], checked['issues'])
        manual = b'1. User rewrote this while the agent reviewed its candidate.\n'
        target.write_bytes(manual)
        with self.assertRaisesRegex(ValueError, 'stale|conflict|failed'):
            text_workflow.apply(self.project, checked['check'])
        self.assertEqual(target.read_bytes(), manual)

    def test_changed_protected_file_is_reported_without_restore(self):
        protected = self.project_file('result/EN/draft.working.md', 'User original\n')
        target, op = self.start(changes='renumber', protected=['result/EN/draft.working.md'])
        protected.write_bytes(b'User is now editing this protected document.\n')
        checked = text_workflow.check(self.project, op['id'], target.read_text(encoding='utf-8'))
        self.assertIn('text.protected', codes(checked))
        self.assertEqual(protected.read_bytes(), b'User is now editing this protected document.\n')
        with self.assertRaises(ValueError):
            text_workflow.apply(self.project, checked['check'])
        self.assertEqual(protected.read_bytes(), b'User is now editing this protected document.\n')

    def test_begin_never_overwrites_a_protected_previous_draft(self):
        protected = self.project_file('result/EN/draft.prev.md', 'User preserved a different baseline.\n')
        before = protected.read_bytes()
        try:
            self.start(target='result/EN/draft.md', protected=['result/EN/draft.prev.md'])
        except ValueError:
            pass  # Refusing before any side effect is also correct.
        self.assertEqual(protected.read_bytes(), before)

    def test_successful_mechanical_apply_has_a_receipt_and_preserves_original(self):
        original = '1. The queue refers to §3.\n\n3. The handler runs.\n'
        target, op = self.start(original, changes='renumber')
        candidate = '1. The queue refers to §2.\n\n2. The handler runs.\n'
        checked = text_workflow.check(self.project, op['id'], candidate)
        applied = text_workflow.apply(self.project, checked['check'])
        self.assertEqual(target.read_text(encoding='utf-8'), candidate)
        self.assertTrue((self.project / applied['receipt']).is_file())
        self.assertEqual(text_workflow.operation(self.project, op['id'])[1], original.encode())
        self.assertTrue(text_workflow.gate(self.project)['valid'])
        with self.assertRaisesRegex(ValueError, 'semantic publication'):
            text_workflow.gate(self.project, publication=True)

    def test_registered_target_cannot_be_overwritten_via_formatter(self):
        target, _ = self.start()
        before = target.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Registered text target'):
            text_workflow.write_candidate_output(target, b'Replacement', expected_sha256=text_claims.digest(before))
        self.assertEqual(target.read_bytes(), before)

    def test_formatter_cannot_overwrite_a_document_protected_by_the_operation(self):
        protected = self.project_file('result/EN/draft.working.md', 'User original\n')
        self.start(protected=['result/EN/draft.working.md'])
        before = protected.read_bytes()
        with self.assertRaisesRegex(ValueError, 'protected|Protected|Registered'):
            text_workflow.write_candidate_output(protected, b'Agent overwrote it.\n',
                                                 expected_sha256=text_claims.digest(before))
        self.assertEqual(protected.read_bytes(), before)

    def test_target_indirection_created_after_capture_cannot_redirect_apply(self):
        original = '1. See https://example.org/original\n'
        protected = self.project_file('result/EN/draft.working.md', original)
        target, op = self.start(original, changes='links', protected=['result/EN/draft.working.md'])
        target.unlink()
        try:
            os.symlink(protected, target)
        except OSError as exc:
            self.skipTest('Host does not permit test symlink creation: ' + str(exc))
        candidate = '1. See https://example.org/replacement\n'
        try:
            checked = text_workflow.check(self.project, op['id'], candidate)
            text_workflow.apply(self.project, checked['check'])
        except ValueError:
            self.assertEqual(protected.read_bytes(), original.encode())
            return
        self.fail('The changed target indirection let apply overwrite the protected file')

    def test_unregistered_candidate_output_requires_cas_and_keeps_history(self):
        output = self.project_file('scratch/candidate.md', 'Initial candidate\n')
        before = output.read_bytes()
        with self.assertRaisesRegex(ValueError, 'expected-sha256'):
            text_workflow.write_candidate_output(output, b'Changed candidate\n')
        self.assertEqual(output.read_bytes(), before)
        receipt = text_workflow.write_candidate_output(output, b'Changed candidate\n', expected_sha256=text_claims.digest(before))
        self.assertEqual(receipt['kind'], 'candidate')
        self.assertFalse(receipt['publication_approved'])
        self.assertEqual(output.read_bytes(), b'Changed candidate\n')

    def test_direct_write_bypass_never_acquires_a_valid_receipt(self):
        target, _ = self.start()
        target.write_bytes(b'1. Direct shell overwrite.\n')
        with self.assertRaisesRegex(ValueError, 'without a current apply receipt'):
            text_workflow.gate(self.project)


class TextMechanicalScopeTests(TextWorkspaceCase):
    def scope(self, base, candidate, *, kind='proposal', changes='renumber'):
        operation = {'kind': kind, 'mode': 'edit', 'changes': changes, 'allow_sections': []}
        return text_workflow.scope_issues(operation, base.encode(), candidate)

    def test_renumber_cannot_rewrite_plain_prose(self):
        base = '1. The form exists.\n3. It sends an event.\n'
        candidate = '1. The form was deleted.\n2. It sends an event.\n'
        self.assertIn('text.scope', codes(self.scope(base, candidate)))

    def test_renumber_cannot_rewrite_article_heading_text(self):
        base = '# I. Analysis\n## 1. The page loads\n<a name="I.1"></a>\nThe concern is present.\n'
        candidate = '# I. Analysis\n## 1. The payment system leaks data\n<a name="I.1"></a>\nThe concern is present.\n'
        self.assertIn('text.scope', codes(self.scope(base, candidate, kind='article')))

    def test_renumber_cannot_rewrite_a_quoted_section_example(self):
        base = '1. The source says "§1 is the original example".\n'
        candidate = '2. The source says "§2 is the original example".\n'
        self.assertIn('text.scope', codes(self.scope(base, candidate)))

    def test_renumber_cannot_rewrite_a_section_symbol_inside_url(self):
        base = '1. The endpoint is https://example.org/§1\n'
        candidate = '2. The endpoint is https://example.org/§2\n'
        self.assertIn('text.scope', codes(self.scope(base, candidate)))

    def test_renumber_preserves_inline_and_fenced_code(self):
        base = '1. The literal is `§1`.\n```js\nconst ref = "§1";\n```\n'
        for candidate in (base.replace('`§1`', '`§2`'), base.replace('"§1"', '"§2"')):
            self.assertIn('text.scope', codes(self.scope(base, candidate)))

    def test_links_can_change_a_destination_but_cannot_change_link_label(self):
        base = '1. Read [the documentation](https://example.org/old).\n'
        good = '1. Read [the documentation](https://example.org/new).\n'
        bad = '1. Read [the website leaks payment data](https://example.org/new).\n'
        self.assertEqual(self.scope(base, good, kind='article', changes='links'), [])
        self.assertIn('text.scope', codes(self.scope(base, bad, kind='article', changes='links')))

    def test_links_cannot_rewrite_exact_ascii_source_quote(self):
        base = '1. The source says "Use https://example.org/original".\n'
        candidate = '1. The source says "Use https://example.org/replacement".\n'
        self.assertIn('text.scope', codes(self.scope(base, candidate, changes='links')))

    def test_inspect_never_allows_even_one_word_change(self):
        op = {'kind': 'proposal', 'mode': 'inspect', 'changes': 'prose', 'allow_sections': []}
        issues = text_workflow.scope_issues(op, b'1. The form exists.\n', '1. The form changed.\n')
        self.assertIn('text.inspect_write', codes(issues))


class TextClaimRevisionTests(TextWorkspaceCase):
    def dependent_registry(self):
        captured = v3_analysis(self.project)
        fact = captured['facts'][0]
        second = claim_metadata('F-DEPENDENT-1')
        second.update(essence='The first dependent text refers to the captured content.',
                      evidence=[], derived_from=[{'claim_id': fact['id'], 'sha256': claim_digest(fact)}])
        third = claim_metadata('F-DEPENDENT-2')
        third.update(essence='The second dependent text refers to the first conclusion.',
                     evidence=[], derived_from=[{'claim_id': second['id'], 'sha256': claim_digest(second)}])
        return {'schema_version': 3, 'facts': [fact, second, third]}

    def test_primary_revision_marks_all_transitive_dependents_stale_and_archives_old_bytes(self):
        value = self.dependent_registry()
        saved, _ = self.registry(value)
        original = (self.project / saved['registry']).read_bytes()
        changed = deepcopy(value)
        changed['facts'][0]['essence'] = 'The captured page includes Alternative.'
        updated = text_claims.save_registry(self.project, changed, expected_sha256=saved['sha256'])
        self.assertEqual(updated['invalidated_claims'], ['F-DEPENDENT-1', 'F-DEPENDENT-2'])
        current = json.loads((self.project / updated['registry']).read_text(encoding='utf-8'))
        index = claim_index(current)
        for ident in updated['invalidated_claims']:
            self.assertEqual(index[ident]['verification_status'], 'stale')
            self.assertTrue(index[ident]['missing_checks'])
            self.assertTrue(index[ident]['superseded_dependencies'])
        archive = self.project / 'ꘖ/data/text-claim-history' / (text_claims.digest(original) + '.json')
        self.assertEqual(archive.read_bytes(), original)

    def test_registry_compare_and_swap_never_overwrites_manual_revision(self):
        saved, value = self.registry()
        path = self.project / saved['registry']
        manual = path.read_bytes() + b'\n'
        path.write_bytes(manual)
        value['facts'][0]['essence'] = 'A revised claim.'
        with self.assertRaisesRegex(ValueError, 'registry changed'):
            text_claims.save_registry(self.project, value, expected_sha256=saved['sha256'])
        self.assertEqual(path.read_bytes(), manual)

    def test_changed_primary_bytes_invalidate_an_existing_semantic_check(self):
        self.registry()
        candidate = '1. The captured page contains the concern.\n'
        _, op = self.start(candidate, mode='propose')
        checked = text_workflow.check(self.project, op['id'], candidate, self.manifest(candidate))
        self.assertTrue(checked['valid'], checked['issues'])
        body = next(path for path in checked['inputs'] if path.endswith('response.bin'))
        (self.project / body).write_bytes(b'The original concern was removed.')
        with self.assertRaisesRegex(ValueError, 'stale|failed'):
            text_workflow.refresh_check(self.project, checked['check'])

    def test_a_self_authored_note_is_not_a_native_reassessment_of_changed_evidence(self):
        value = self.dependent_registry()
        saved, _ = self.registry(value)
        changed = deepcopy(value)
        changed['facts'][0]['essence'] = 'The captured page includes Alternative.'
        changed['facts'][1]['derived_from'][0]['sha256'] = claim_digest(changed['facts'][0])
        changed['facts'][2]['derived_from'][0]['sha256'] = claim_digest(changed['facts'][1])
        self.project_file('ꘖ/data/my-opinion.txt', 'Everything is still true because I say so.\n')
        reassessments = {claim['id']: {'basis': 'I consider it unchanged.',
                          'previous_sha256': claim_digest(claim),
                          'evidence': ['ꘖ/data/my-opinion.txt']}
                         for claim in value['facts'][1:]}
        try:
            updated = text_claims.save_registry(self.project, changed,
                expected_sha256=saved['sha256'], reassessments=reassessments)
        except ValueError:
            return  # Refusing unbound reassessment metadata is safe.
        self.assertEqual(updated['invalidated_claims'], ['F-DEPENDENT-1', 'F-DEPENDENT-2'])
