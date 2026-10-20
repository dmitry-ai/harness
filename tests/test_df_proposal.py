"""Proposal regressions from the user's numbered texts and editing incidents."""

from test_agent_tools import TemporaryCase
from agent_tools import proposal


def rules(findings, severity=None):
    return {finding.rule for finding in findings
            if severity is None or finding.severity == severity}


def lint(text, **kwargs):
    return proposal.lint_text(text, lang='en', lexicon=[], bans=[], **kwargs)


class ProposalTransformTests(TemporaryCase):
    def test_explicit_external_codes_and_standards_are_not_internal_points(self):
        text = ('1. The consent setting conflicts with 11 CCR § 7025.\n'
                'RFC 9110 §15.4.3 and ISO 27001:2022 §5.1 remain external.\n'
                '2. Inspect the setting described in §1.\n')
        source = proposal.to_source(text)
        value, report, findings = proposal.render(source, text)
        self.assertEqual(value, text.replace('11 CCR § 7025', '11 CCR §7025'))
        self.assertEqual(findings, [])
        self.assertEqual(report['external_references_normalized'],
                         [{'line':1,'document':'11 CCR','before':'§ 7025','after':'§7025'}])
        self.assertNotIn('REF-DANGLING', rules(lint(text)))
        self.assertIn('REF-DANGLING', rules(lint('1. A local reference to §7025.\n')))

    def test_reordering_changes_local_refs_but_preserves_the_external_paragraph(self):
        text = ('1. The consent setting follows 11 CCR § 1 and RFC 9110 § 15.4.3.\n\n'
                '2. Inspect the setting in §1.\n')
        first, second = proposal.to_source(text).split('\n\n')
        result, _, findings = proposal.render(second + '\n' + first + '\n', text)
        self.assertEqual(findings, [])
        self.assertIn('1. Inspect the setting in §2.', result)
        self.assertIn('2. The consent setting follows 11 CCR §1 and RFC 9110 §15.4.3.', result)
        self.assertIn('REF-EXTERNAL-SPACE', rules(proposal.lint_text(text)))

    def test_external_spacing_normalization_preserves_quoted_examples_and_code(self):
        text = ('1. Read 11 CCR § 7025.\n'
                'The exact quotation is «11 CCR § 7025».\n'
                '`11 CCR § 7025`\n'
                '```text\n11 CCR § 7025\n```\n')
        value, _, findings = proposal.render(proposal.to_source(text), text)
        self.assertEqual(findings, [])
        self.assertEqual(value, text.replace('Read 11 CCR § 7025.', 'Read 11 CCR §7025.'))

    def test_round_trip_preserves_all_wording_quotes_code_zero_prefaces_and_newlines(self):
        text = ('🔴 1.  The website uses §2 and §§2-3.\r\n\r\n'
                '2. The form sends `§999` and «§998» unchanged.\r\n'
                '2.0. It sends:\r\n'
                '2.1. The exact endpoint is https://example.org/a#§997.\r\n'
                '```js\r\n2. Reference: §996\r\n```\r\n\r\n'
                '3. «How would you inspect your website?»\r\n'
                '3.0.1.  The export contains events.\r\n'
                '3.0.2. The handler captures §2.1.')
        source = proposal.to_source(text)
        self.assertIn('§§@2-@3', source)
        self.assertIn('`§999`', source)
        self.assertIn('https://example.org/a#§997.', source)
        rendered, report, findings = proposal.render(source, text)
        self.assertEqual(rendered, text)
        self.assertEqual(findings, [])
        self.assertEqual(report, {'renumbered': [], 'added': [], 'removed': []})

    def test_reordering_moves_child_references_and_keeps_prose(self):
        old = '1. The form exists.\n1.1. The handler sends an event.\n\n2. The event uses §1.1.\n'
        source = proposal.to_source(old)
        first, second = source.split('\n\n')
        rendered, report, findings = proposal.render(second + '\n' + first + '\n', old)
        self.assertEqual(findings, [])
        self.assertEqual(rendered, '1. The event uses §2.1.\n\n2. The form exists.\n2.1. The handler sends an event.\n')
        self.assertEqual(report['renumbered'], [['2', '1'], ['1', '2'], ['1.1', '2.1']])

    def test_deleted_referenced_point_blocks_render(self):
        rendered, report, findings = proposal.render('@2. The event uses §@1.\n',
                                                    '1. The form exists.\n2. The event uses §1.\n')
        self.assertIn('KEY-DANGLING', rules(findings, 'error'))
        self.assertIn('1', report['removed'])
        self.assertIn('§@1', rendered)

    def test_new_descriptive_keys_assign_numbers_without_article_headings(self):
        text, report, findings = proposal.render('@form The form exists.\n@form.reason The listener sends §@event.\n\n@event The handler runs.\n')
        self.assertEqual(findings, [])
        self.assertEqual(text, '1. The form exists.\n1.1. The listener sends §2.\n\n2. The handler runs.\n')
        self.assertEqual(report['added'], ['form', 'form.reason', 'event'])
        self.assertNotIn('<a ', text)

    def test_numbers_in_keyed_body_cannot_silently_rebind(self):
        _, _, findings = proposal.render('@one See §2.\n@two The event fires.\n')
        self.assertIn('KEY-NUMERIC-REF', rules(findings, 'error'))

    def test_duplicate_and_missing_parent_keys_are_errors(self):
        _, _, findings = proposal.render('@one.child The child exists.\n@one The form exists.\n@one The duplicate exists.\n')
        self.assertTrue({'KEY-PARENT', 'KEY-DUP'} <= rules(findings, 'error'))

    def test_children_cannot_be_left_behind_after_moving_a_sibling(self):
        _, _, findings = proposal.render('@one The form exists.\n@one.a The first child exists.\n@one.b The next child exists.\n@one.a.last The detached child exists.\n')
        self.assertIn('KEY-NONCONTIGUOUS', rules(findings, 'error'))

    def test_both_range_boundaries_renumber_and_reversed_range_fails(self):
        _, _, findings = proposal.render('@last See §§@first-@last.\n@first The fact exists.\n')
        self.assertIn('PROPOSAL-RANGE-ORDER', rules(findings, 'error'))

    def test_literals_in_ascii_quotation_and_markdown_url_remain_unchanged(self):
        old = '1. The reference says "see §7" and links to [§8](https://example.org/§9).\n'
        source = proposal.to_source(old)
        self.assertEqual(source, '@1 The reference says "see §7" and links to [§8](https://example.org/§9).\n')
        self.assertEqual(proposal.render(source, old)[0], old)


class ProposalLintTests(TemporaryCase):
    def test_plain_numbered_proposal_needs_no_article_parts_or_anchors(self):
        text = '1. The website serves a form.\n\n2. The listener sends an event.\n2.1. The event uses §1.\n'
        self.assertEqual(lint(text), [])

    def test_empty_and_unnumbered_fragments_fail(self):
        for text in ('', 'The website returns 200.'):
            self.assertIn('PROPOSAL-EMPTY', rules(lint(text), 'error'))

    def test_sequence_duplicate_and_missing_parent_fail(self):
        text = '1. The form exists.\n1. The form exists again.\n3. The event runs.\n3.2.1. The parent is absent.\n'
        self.assertTrue({'PROPOSAL-SEQ', 'PROPOSAL-DUP', 'PROPOSAL-PARENT'} <= rules(lint(text), 'error'))

    def test_editorial_zero_prefaces_are_valid(self):
        text = '1. The form exists.\n1.0. It sends:\n1.1. The event runs.\n\n2. The question follows.\n2.0.1. The export has events.\n2.0.2. The queue has records.\n'
        self.assertEqual(lint(text), [])

    def test_flat_profile_is_explicit(self):
        text = '1. The form exists.\n1.1. The event runs.\n'
        self.assertNotIn('PROPOSAL-FLAT', rules(lint(text)))
        self.assertIn('PROPOSAL-FLAT', rules(lint(text, profile={'numbering': 'flat'}), 'error'))

    def test_actual_field_can_start_at_a_later_global_point(self):
        text = '11. The event uses §2.\n12. The handler runs.\n'
        self.assertEqual(lint(text, profile={'start': 11, 'reference_targets': ['2']}), [])

    def test_dangling_references_have_no_distance_exception(self):
        text = '1. The event uses §999.\n2. The handler uses §2.9.\n'
        self.assertEqual(sum(f.rule == 'REF-DANGLING' for f in lint(text)), 2)

    def test_space_after_section_sign_cannot_hide_a_dangling_reference(self):
        found = lint('1. See § 999.\n')
        self.assertTrue({'PROPOSAL-REF-SPACE', 'REF-DANGLING'} <= rules(found, 'error'))

    def test_real_exemplar_glued_point_is_reported(self):
        found = lint('1. The form exists.\n1.1. Read the URL.1.1. Read the updated URL.\n')
        self.assertIn('PROPOSAL-CONCAT', rules(found, 'error'))

    def test_every_range_member_and_range_punctuation_are_checked(self):
        text = '1. The range is §§2-4.\n2. The form exists.\n4. The handler uses §1–§2.\n'
        found = lint(text)
        self.assertIn('REF-DANGLING', rules(found, 'error'))
        self.assertIn('PROPOSAL-RANGE', rules(found, 'error'))

    def test_refs_in_code_quotes_and_urls_are_not_proposal_refs(self):
        text = '1. The literal `§999` and «§998» remain: https://example.org/§997\n```text\n§996\n```\n'
        self.assertNotIn('REF-DANGLING', rules(lint(text)))

    def test_rendered_proposal_cannot_keep_source_keys(self):
        self.assertIn('KEY-UNRENDERED', rules(lint('1. See §@missing.\n'), 'error'))

    def test_markdown_article_shell_is_rejected(self):
        text = '# I. Analysis\n<a name="I.1"></a>\n1. See [docs](https://example.org/a).\n'
        self.assertTrue({'PROPOSAL-HEADING', 'PROPOSAL-ANCHOR', 'PROPOSAL-MARKDOWN-LINK'} <= rules(lint(text), 'error'))

    def test_url_repetition_refers_to_the_first_point(self):
        found = lint('1. See https://example.org/a\n\n2. See https://example.org/a\n')
        repeated = [f for f in found if f.rule == 'PROPOSAL-DUP-URL']
        self.assertEqual(len(repeated), 1)
        self.assertIn('line 1', repeated[0].message)

    def test_technical_voice_and_direct_offer_are_distinct(self):
        text = '1. I can fix the listener for $50.\n'
        self.assertIn('PROPOSAL-FIRST-PERSON', rules(lint(text), 'error'))
        self.assertNotIn('PROPOSAL-FIRST-PERSON', rules(lint(text, profile={'voice': 'offer'})))
        self.assertNotIn('PROPOSAL-FIRST-PERSON', rules(lint('1. «What have I configured?»\n1.1. The listener sends events.\n')))

    def test_actual_words_in_client_quotes_are_not_rewritten(self):
        text = '1. «How would you give us that full journey?»\n1.1. The export stores the event sequence.\n'
        self.assertNotIn('PROPOSAL-JOURNEY', rules(lint(text)))
        self.assertIn('PROPOSAL-JOURNEY', rules(lint('1. The export reconstructs the journey.\n'), 'error'))

    def test_owner_subject_uses_shared_lexicon_and_preserves_quotations(self):
        author = proposal.lint_text('1. Your website sends an event.\n', lang='en', bans=[])
        quote = proposal.lint_text('1. The question says «your website».\n', lang='en', bans=[])
        self.assertIn('TEXT-OWNER', rules(author, 'error'))
        self.assertNotIn('TEXT-OWNER', rules(quote))


class ProposalFieldTests(TemporaryCase):
    def test_aggregate_room_cannot_hide_one_oversized_field(self):
        fields = {'Cover Letter': 'a' * 5001, 'Q1': 'b'}
        found = proposal.lint_fields(fields, {'Cover Letter': 5000, 'Q1': 5000})
        self.assertIn('PROPOSAL-FIELD-LIMIT', rules(found, 'error'))

    def test_limits_count_exact_text_including_urls_and_newlines(self):
        fields = {'Cover Letter': '1. See https://example.org/\n'}
        limit = len(fields['Cover Letter'])
        self.assertEqual(proposal.lint_fields(fields, {'Cover Letter': limit}), [])
        self.assertIn('PROPOSAL-FIELD-LIMIT', rules(proposal.lint_fields(fields, {'Cover Letter': limit - 1})))

    def test_missing_field_and_unconfirmed_limit_are_distinct_errors(self):
        found = proposal.lint_fields({'Q1': 'Answer'}, {'Cover Letter': 5000})
        self.assertEqual(rules(found, 'error'), {'PROPOSAL-FIELD-MISSING', 'PROPOSAL-FIELD-LIMIT-MISSING'})

    def test_zero_or_noninteger_limit_is_not_accepted_as_configuration(self):
        for limit in (0, -1, 2.5, True):
            with self.assertRaises(ValueError):
                proposal.lint_fields({'Q1': 'Answer'}, {'Q1': limit})

    def test_browser_character_length_cannot_undercount_astral_unicode(self):
        self.assertIn('PROPOSAL-FIELD-LIMIT', rules(proposal.lint_fields({'Q1': '🔴'}, {'Q1': 1})))
        self.assertEqual(proposal.lint_fields({'Q1': '🔴'}, {'Q1': 1}, count_mode='unicode'), [])
