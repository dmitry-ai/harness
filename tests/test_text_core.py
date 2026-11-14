# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Generalize keyed section numbering (@key), section-reference validation, and profile dispatch across article.py, proposal.py, text_workflow.py, text_claims.py, and text_cli.py":
# https://github.com/dmitry-ai/harness/issues/70
# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
import os
from unittest.mock import patch
from test_agent_tools import TemporaryCase
from test_df_article import wrap, rules
from agent_tools import article, proposal, text_core, text_sections
class ArticleIntegrityTests(TemporaryCase):
	def lint(self, text):
		return article.lint_text(text, kind='article', lexicon=[], bans=[])
	def test_section_sign_anchors_survive_source_render_without_previous(self):
		text = wrap('Fact.', recommendations=('Act on **[§I.1](#§I.1)**.',)).replace("name='I.1'", "name='§I.1'").replace("name='II.1'", "name='§II.1'")
		source = article.to_source(text)
		self.assertNotIn('§@§', source)
		result, _, findings = article.render(source)
		self.assertEqual(findings, [])
		self.assertEqual(result, text)
		self.assertNotIn('ANCHOR-MISMATCH', rules(self.lint(result)))
	def test_mixed_anchor_style_follows_keys_when_renumbering(self):
		text = wrap('First.', 'Second.', recommendations=('Use **[§I.2](#I.2)**.',)).replace("name='I.1'", "name='§I.1'")
		source = article.to_source(text)
		a, b = (source.index('## @I.1\n'), source.index('## @I.2\n'))
		c = source.index('# II.')
		source = source[:a] + source[b:c] + source[a:b] + source[c:]
		result, _, findings = article.render(source)
		self.assertEqual(findings, [])
		self.assertIn("## 2\n<a name='§I.2'></a>\nFirst.", result)
		self.assertIn('**[§I.1](#I.1)**', result)
	def test_literals_quotes_and_urls_are_not_rewritten(self):
		literals = '`[§1](#I.1)` and ``§@not-a-key ` x``.\n«§999» and "§1000".\nhttps://example.org/§123\n> [§3](#I.3)\n```bash\nprintf "§@also-literal"\n```'
		text = wrap(literals)
		source = article.to_source(text)
		for line in literals.splitlines():
			self.assertIn(line, source)
		result, _, findings = article.render(source)
		self.assertEqual(findings, [])
		for line in literals.splitlines():
			self.assertIn(line, result)
		self.assertNotIn('REF-BARE', rules(self.lint(result)))
	def test_bare_article_reference_is_converted_or_diagnosed(self):
		text = wrap('See §999.')
		self.assertIn('REF-BARE', rules(self.lint(text), 'error'))
		result, _, findings = article.render(article.to_source(text))
		self.assertIn('KEY-DANGLING', rules(findings, 'error'))
		self.assertIn('§@I.999', result)
	def test_reference_range_checks_both_ends_and_order(self):
		text = wrap('Fact.', 'Second fact.', recommendations=('Use **[§§I.1-I.999](#I.1)**.',))
		self.assertIn('REF-DANGLING', rules(self.lint(text), 'error'))
		_, _, findings = article.render(article.to_source(text))
		self.assertIn('KEY-DANGLING', rules(findings, 'error'))
		reverse = text.replace('I.1-I.999](#I.1)', 'I.2-I.1](#I.2)')
		self.assertIn('REF-RANGE', rules(self.lint(reverse), 'error'))
	def test_valid_range_is_renumbered_and_generic_links_are_preserved(self):
		text = wrap('Fact.', 'Second.', recommendations=('Use **[§§I.1-I.2](#I.1)** and [the fact](#I.2).',))
		source = article.to_source(text)
		self.assertIn('§§@I.1-@I.2', source)
		result, _, findings = article.render(source)
		self.assertEqual(findings, [])
		self.assertIn('**[§§I.1-I.2](#I.1)** and [the fact](#I.2)', result)
	def test_article_requires_parts_and_addressed_content(self):
		self.assertTrue({'STRUCT-PARTS', 'STRUCT-EMPTY', 'STRUCT-UNADDRESSED'} <= rules(self.lint('The website returns 200.'), 'error'))
		self.assertIn('STRUCT-UNADDRESSED', rules(self.lint('# I. Analysis\nUnaddressed fact.\n# II. Recommendations\nAct.'), 'error'))
	def test_used_leaf_does_not_make_unused_sibling_a_premise(self):
		text = '# I. Analysis\n## 1\n<a name="I.1"></a>\n### 1.1\n<a name="I.1.1"></a>\nFact.\n### 1.2\n<a name="I.1.2"></a>\nUnused.\n# II. Recommendations\n## 1\n<a name="II.1"></a>\nAct on **[§I.1.1](#I.1.1)**.'
		orphans = [finding for finding in self.lint(text) if 'GRAPH-ORPHAN' == finding.rule]
		self.assertEqual([finding.message.split()[0] for finding in orphans], ['§I.1.2'])
	def test_unfounded_cycle_is_not_evidence(self):
		text = wrap('**[§2](#I.2)** → fact.', '**[§1](#I.1)** → other fact.')
		self.assertIn('GRAPH-CYCLE', rules(self.lint(text), 'error'))
		supported = text.replace('→ other fact.', '→ other fact.\n[Source](https://example.org/source)')
		self.assertNotIn('GRAPH-CYCLE', rules(self.lint(supported)))
	def test_explicit_group_count_matches_displayed_list(self):
		text = wrap('- `/a`\n- `/b`').replace('## 1\n', '## 1. Pages (3)\n', 1)
		self.assertIn('GROUP-COUNT', rules(self.lint(text), 'error'))
		self.assertNotIn('GROUP-COUNT', rules(self.lint(text.replace('Pages (3)', 'Pages (2)'))))
		self.assertNotIn('GROUP-COUNT', rules(self.lint(wrap('A fact.'))))
	def test_native_list_numbering_is_distinct_from_addressable_headings_and_quotes(self):
		text = wrap('1. First\n2. Second\n\n> 2. Exact quoted numbering\n\n`2. literal`', 'Other fact.')
		findings = [finding for finding in self.lint(text) if 'LIST-AUTONUM' == finding.rule]
		self.assertEqual(len(findings), 1)
		self.assertEqual(findings[0].excerpt, '2. Second')
	def test_formatted_link_style_is_explicit_and_preserves_literals(self):
		text = wrap('https://example.org/a\n[Source](https://example.org/b)\n`https://example.org/code`\n«https://example.org/quote»\n> https://example.org/quoted')
		self.assertNotIn('LINK-BARE', rules(self.lint(text)))
		findings = article.lint_text(text, lexicon=[], bans=[], link_style='formatted')
		bare = [finding.excerpt for finding in findings if 'LINK-BARE' == finding.rule]
		self.assertEqual(bare, ['https://example.org/a'])
	def test_render_mapping_exposes_keys_and_spans_without_polluting_report(self):
		source = '# I. Analysis\n## @first\nFact.\n# II. Recommendations\n## @action\nAct on **§@first**.'
		result, report, _ = article.render(source)
		mapping = article.render_map(source, result)
		self.assertEqual(mapping[0]['key'], 'first')
		self.assertEqual(mapping[0]['number'], 'I.1')
		self.assertEqual(mapping[0]['rendered']['start'], 2)
		self.assertEqual(set(report), {'renumbered', 'added'})
	def test_render_diff_never_writes_target_and_force_cannot_publish_invalid_links(self):
		target = self.put('draft.md', 'User text.\n')
		source = self.put('draft.src.md', '# I. Analysis\n## @fact\nA fact.\n')
		result = self.cli('df_article', 'render', source, '-o', target, '--diff')
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertIn('+A fact.', result.stdout)
		self.assertEqual(target.read_text(), 'User text.\n')
		source.write_text('# I. Analysis\n## @fact\nSee §@missing.\n', encoding='utf-8')
		failed = self.cli('df_article', 'render', source, '-o', target, '--force')
		self.assertEqual(failed.returncode, 1)
		self.assertEqual(target.read_text(), 'User text.\n')
class SharedMechanicsTests(TemporaryCase):
	def test_article_reexports_single_shared_implementation(self):
		for name in ('Finding', 'Line', 'scan', 'clean', 'check_prose', 'check_code', 'check_response', 'replay', 'load_lexicon'):
			self.assertIs(getattr(article, name), getattr(text_core, name))
		self.assertTrue(issubclass(article.Section, text_sections.AddressedSection))
		self.assertTrue(issubclass(proposal.ProposalBlock, text_sections.AddressedSection))
		self.assertIs(text_sections.keyed_engine('article'), article)
		self.assertIs(text_sections.keyed_engine('proposal'), proposal)
		with self.assertRaises(ValueError):
			text_sections.keyed_engine('letter')
		self.assertEqual([b['section'] for b in text_sections.content_blocks('First.\n\nSecond.', 'letter')], ['1', '2'])
	def test_fence_contents_end_only_at_matching_fence(self):
		text = '````bash\nprintf ok\n```\ntext\n~~~~\n````\nAfter.'
		lines = text_core.scan(text)
		self.assertEqual([line.kind for line in lines], ['fence', 'code', 'code', 'code', 'code', 'fence', 'prose'])
	def test_shell_can_be_configured(self):
		with patch.dict(os.environ, {'DF_TEXT_BASH': '/selected/bash'}):
			self.assertEqual(text_core.default_shell(), '/selected/bash')
	def test_hashed_asset_is_a_warning_not_proof_of_an_error(self):
		findings = []
		text_core.check_code(text_core.scan('```bash\ncurl -s https://example.org/assets/index-Abc12345.js\n```'), findings)
		self.assertIn('CODE-VOLATILE', rules(findings, 'warning'))
		self.assertNotIn('CODE-VOLATILE', rules(findings, 'error'))
	def test_identical_answer_does_not_prove_nonexecution(self):
		self.put('journal/res/1.md', 'Done.\n')
		candidate = self.put('candidate.md', 'Done.\n')
		findings = text_core.check_response(candidate, journal=self.root / 'journal', lexicon=[])
		self.assertIn('RESP-DUP', rules(findings, 'warning'))
		self.assertEqual(rules(findings, 'error'), set())
class ReplayTests(TemporaryCase):
	def test_nonzero_exit_cannot_match_printed_stdout(self):
		text = '```bash\nprintf ok\nexit 7\n```\n> ok\n'
		self.assertEqual(text_core.replay(text)[0]['status'], 'exit-mismatch')
		accepted = text_core.replay(text, expected_exit={1: 7})[0]
		self.assertEqual(accepted['status'], 'match')
		self.assertEqual(accepted['returncode'], 7)
		self.assertEqual(accepted['stdout'], 'ok')
	def test_pipeline_and_intermediate_command_failures_are_not_hidden(self):
		for command in ('false | printf ok', 'false\nprintf ok'):
			result = text_core.replay(f'```bash\n{command}\n```\n> ok\n')[0]
			self.assertEqual(result['status'], 'exit-mismatch')
			self.assertNotEqual(result['returncode'], 0)
	def test_negative_grep_observation_requires_explicit_exit_contract(self):
		text = '```bash\nprintf text | grep absent\n```\n> `<empty response>`\n'
		self.assertEqual(text_core.replay(text)[0]['status'], 'exit-mismatch')
		result = text_core.replay(text, contracts={1: {'exit': 1}})[0]
		self.assertEqual(result['status'], 'match')
		self.assertEqual(result['stdout'], '')
	def test_quoted_numbered_links_are_presentation_of_raw_output(self):
		text = '```bash\nprintf "/a\\n/b\\n"\n```\n> 1. [`/a`](https://example.org/a)\n> 1. [`/b`](https://example.org/b)\n'
		result = text_core.replay(text)[0]
		self.assertEqual(result['status'], 'match')
		self.assertEqual(result['stdout'], '/a\n/b\n')
		self.assertIn('[`/a`]', result['presentation'])
	def test_missing_output_uncovered_selector_and_empty_document_are_not_success(self):
		no_output = self.put('no-output.md', '```bash\nprintf ok\n```\n')
		self.assertEqual(text_core.replay(no_output.read_text())[0]['status'], 'no-quoted-output')
		self.assertEqual(self.cli('df_article', 'replay', no_output).returncode, 1)
		self.assertEqual(text_core.replay(no_output.read_text(), only=[999])[0]['status'], 'uncovered')
		self.assertEqual(self.cli('df_article', 'replay', no_output, '--line', '999').returncode, 1)
		empty = self.put('empty.md', 'No commands.')
		self.assertEqual(self.cli('df_article', 'replay', empty).returncode, 1)
	def test_explicit_raw_contract_does_not_require_quote_wrapper(self):
		result = text_core.replay('```bash\nprintf ok\n```', contracts={1: {'exit': 0, 'stdout': 'ok'}})[0]
		self.assertEqual(result['status'], 'match')
	def test_changed_blocks_need_receipts_unchanged_moves_do_not(self):
		old = '```bash\nprintf ok\n```\n> ok\n'
		moved = '\n\n' + old
		self.assertEqual(text_core.changed_command_lines(moved, old), [])
		self.assertEqual(text_core.changed_command_lines(moved.replace('> ok', '> different'), old), [3])
		self.assertEqual(text_core.changed_command_lines(old), [1])
	def test_unclosed_fence_is_an_error(self):
		result = text_core.replay('```bash\nprintf ok\n', contracts={1: {'stdout': 'ok'}})[0]
		self.assertEqual(result['status'], 'error')
		self.assertIn('unclosed', result['error'])
