# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace per-profile Harness projections with shared native connections":
# https://github.com/dmitry-ai/harness/issues/35
import json
import re
import shutil
from test_agent_tools import TemporaryCase
from agent_tools import article, configuration, runtime
GOLD = runtime.PRIMARY / 'skills/df-article/references/2725.md'
def rules(findings, severity=None):
	return {f.rule for f in findings if None is severity or f.severity == severity}
def wrap(*analysis, recommendations=('Fix it (**[§I.1](#I.1)**).',)):
	out = ['# I. Analysis']
	for index, body in enumerate(analysis, 1):
		out += [f'## {index}', f"<a name='I.{index}'></a>", body, '']
	out.append('# II. Recommendations')
	for index, body in enumerate(recommendations, 1):
		out += [f'## {index}', f"<a name='II.{index}'></a>", body, '']
	r = '\n'.join(out)
	return r
class ReferenceArticleTests(TemporaryCase):
	def test_external_document_spacing_preserves_its_number_and_literal_examples(self):
		text = wrap('The rule is 11 CCR § 7025.\nThe exact quotation is «11 CCR § 7025».\n`11 CCR § 7025`')
		value, report, findings = article.render(article.to_source(text), text)
		self.assertFalse(any(('error' == f.severity for f in findings)))
		self.assertEqual(value, text.replace('The rule is 11 CCR § 7025.', 'The rule is 11 CCR §7025.'))
		self.assertEqual(report['external_references_normalized'][0]['document'], '11 CCR')
		self.assertEqual(report['external_references_normalized'][0]['after'], '§7025')
	def test_reference_article_has_no_errors_and_only_known_warnings(self):
		findings = article.lint_text(GOLD.read_text(encoding='utf-8'), path=GOLD)
		self.assertEqual(rules(findings, 'error'), set(), [f.format() for f in findings if 'error' == f.severity])
		warnings = {(f.rule, f.line) for f in findings if 'warning' == f.severity}
		self.assertEqual({rule for rule, _ in warnings}, {'STRUCT-LEVEL', 'EN-VAGUE'})
	def test_keyed_view_round_trip_changes_only_normalizations(self):
		gold = GOLD.read_text(encoding='utf-8')
		source = article.to_source(gold)
		self.assertNotIn('<a name=', source)
		self.assertIn('## @I.1\n', source)
		self.assertIn('**{§@I.4.1, §@I.5.1, §@I.6}** →', source)
		markdown, report, findings = article.render(source, gold)
		self.assertEqual(findings, [])
		self.assertEqual(report, {'renumbered': [], 'added': [], 'removed': []})
		changed = [(a, b) for a, b in zip(gold.splitlines(), markdown.splitlines()) if a != b]
		self.assertEqual(len(gold.splitlines()), len(markdown.splitlines()))
		self.assertEqual(changed, [('**{[§12.1](#I.12.1), [§15.1](#I.15.1)}** → **12** pages of **[§I.12.1](#I.12.1)** are indexable.', '**{[§12.1](#I.12.1), [§15.1](#I.15.1)}** → **12** pages of **[§12.1](#I.12.1)** are indexable.'), ('### 17.2.1', '#### 17.2.1')])
		self.assertEqual(rules(article.lint_text(markdown), 'error'), set())
	def test_deleted_premise_blocks_rendering_until_dependents_are_resolved(self):
		source = article.to_source(GOLD.read_text(encoding='utf-8'))
		without = re.sub('(?ms)^## @I\\.6\\n.*?(?=^## @I\\.7\\n)', '', source)
		_, _, findings = article.render(without)
		dangling = [f for f in findings if 'KEY-DANGLING' == f.rule]
		self.assertEqual(len(dangling), 2)
		src = self.put('draft.src.md', without)
		result = self.cli('df_article', 'render', src, '-o', self.root / 'draft.md')
		self.assertEqual(result.returncode, 1, result.stdout)
		self.assertFalse((self.root / 'draft.md').exists())
	def test_render_renumbers_references_and_reports_removed_sections(self):
		gold = GOLD.read_text(encoding='utf-8')
		source = article.to_source(gold)
		source = re.sub('(?ms)^## @I\\.6\\n.*?(?=^## @I\\.7\\n)', '', source)
		source = source.replace('**{§@I.4.1, §@I.5.1, §@I.6}**', '**{§@I.4.1, §@I.5.1}**')
		source = source.replace('from Bluehost (**§@I.6**) to', 'to')
		markdown, report, findings = article.render(source, gold)
		self.assertEqual(findings, [])
		self.assertEqual(report['removed'], ['I.6'])
		self.assertIn(['I.7', 'I.6'], report['renumbered'])
		self.assertIn("## 6\n<a name='I.6'></a>\n### 6.1\n<a name='I.6.1'></a>\n**{[§4.1](#I.4.1), [§5.1](#I.5.1)}** →", markdown)
		self.assertIn('**[§I.6.2](#I.6.2)** → configure a reverse proxy', markdown)
		self.assertEqual(rules(article.lint_text(markdown), 'error'), set())
	def test_new_keys_are_numbered_by_position(self):
		source = '# I. Analysis\n## @react\nThe website runs on **React**.\n## @csr\n**§@react** → the website renders on the client.\n'
		markdown, report, findings = article.render(source)
		self.assertEqual(findings, [])
		self.assertIn("## 2\n<a name='I.2'></a>\n**[§1](#I.1)** → the website", markdown)
		self.assertEqual(report['added'], ['react', 'csr'])
class SlopDetectionTests(TemporaryCase):
	def assertFlags(self, text, rule, kind='article'):
		found = article.lint_text(text, kind=kind, lang='en', bans=[])
		self.assertIn(rule, rules(found), [f.format() for f in found])
	def test_arrow_followed_by_a_connective(self):
		self.assertFlags(wrap('**[§1](#I.1)** → although the React frontend pushes `region` into `window.dataLayer` on every form submission.'), 'ARROW-CONNECTIVE')
	def test_sentence_initial_connectives_and_subordinate_causes(self):
		self.assertFlags(wrap('Consequently, the `region` parameter is discarded before the `generate_lead` event reaches GA4.'), 'EN-CONNECTIVE-START')
		self.assertFlags(wrap('Because `GTM-WWDQT6Q9` has no trigger for `party_enquiry_submit`, this event is never sent to GA4.'), 'EN-SUBORDINATE-CAUSE')
		self.assertFlags(wrap('At the same time, `<head>` initializes **2** different Meta Pixel IDs.'), 'EN-CONNECTIVE-START')
		self.assertFlags(wrap('However, neither container contains any trigger, making `order_item` a dead-end `dataLayer` push.'), 'EN-PSEUDO-INFERENCE')
	def test_bold_label_lead_in(self):
		self.assertFlags(wrap('**Critical Currency Defect on Hong Kong Purchases (`GTM-T9T2V284`)**: On the Hong Kong portal both tags set `SGD`.'), 'BOLD-LEADIN')
	def test_process_narration(self):
		self.assertFlags(wrap('Inspection of the firing rules in `GTM-T9T2V284` reveals that the events are mapped to the wrong user actions.'), 'EN-PROCESS-NARRATION')
	def test_internal_analysis_apparatus(self):
		self.assertFlags(wrap('The `/404` page body has SHA-256 `17174d0fb845d24772c6c445197fcc498d7ac4c957fee890835a3254a57cc7b7`.'), 'APP-HASH')
		self.assertFlags(wrap('Limitation: the evidence array of F-SITE-CRAWL-AND-404 includes only `/404`.'), 'APP-ANALYSIS-FORM')
		self.assertFlags(wrap('The evidence array of F-SITE-CRAWL-AND-404 includes only `/404`.'), 'APP-ID')
		self.assertFlags(wrap('Proof: [observation](<ꘖ/KB/Evidence/HTTP/x/observation.json>).'), 'LINK-LOCAL')
	def test_enumerating_title_case_heading(self):
		text = wrap('Fact.').replace('## 1\n', '## 1. Missing Events, Duplicate Events, and External Booking Platform Gaps\n')
		found = article.lint_text(text, kind='article', lang='en', bans=[])
		self.assertTrue({'HEADING-ENUM', 'HEADING-TITLECASE'} <= rules(found))
	def test_two_sentences_on_one_line_and_identifier_overload(self):
		self.assertFlags(wrap('The page has one form. It posts to `/submit`.'), 'SENT-SPLIT')
		self.assertFlags(wrap(' '.join((f'`id{i}`' for i in range(10))) + ' are present.'), 'SENT-IDENTIFIERS')
	def test_structure_errors(self):
		text = wrap('Fact.', 'Second fact.').replace("<a name='I.2'></a>", "<a name='I.3'></a>")
		found = article.lint_text(text, kind='article', lang='en', bans=[])
		self.assertIn('ANCHOR-MISMATCH', rules(found))
		text = wrap('See **[§2](#I.1)**.')
		self.assertIn('REF-LABEL', rules(article.lint_text(text, kind='article', lang='en', bans=[])))
		text = wrap('Fact.').replace('## 1\n', '## 2\n').replace("'I.1'", "'I.2'")
		self.assertIn('STRUCT-SEQ', rules(article.lint_text(text, kind='article', lang='en', bans=[])))
	def test_duplicated_output_lines_and_unreadable_literal(self):
		body = "The page loads `GTM-X`:\n```bash\ncurl -s https://example.org/ | grep -o 'GTM-[A-Z]*'\n```\n> GTM-X\n> GTM-X"
		self.assertFlags(wrap(body), 'CODE-DUP-OUTPUT')
		body = "Value:\n```bash\ncurl -s https://example.org/x.js | grep -o '" + 'a' * 120 + "'\n```\n> a"
		self.assertFlags(wrap(body), 'CODE-UNREADABLE')
	def test_orphan_analysis_paragraph_is_reported(self):
		text = wrap('Used fact.', 'Unused fact.', recommendations=('Act on **[§I.1](#I.1)**.',))
		orphans = [f for f in article.lint_text(text, kind='article', lang='en', bans=[]) if 'GRAPH-ORPHAN' == f.rule]
		self.assertEqual([f.message.split()[0] for f in orphans], ['§I.2'])
	def test_project_bans_are_discovered_from_the_project_root(self):
		project = self.root / 'job'
		self.put('job/ꘖ/data/article-bans.json', json.dumps({'bans': [{'pattern': '\\d{2} \\d{3} bytes', 'why': 'req/4: «Why do you state the byte count»'}]}))
		draft = self.put('job/result/article/EN/draft.md', wrap('The error page has `16 573` bytes and 16 573 bytes.'))
		found = article.lint_text(draft.read_text(encoding='utf-8'), path=draft)
		self.assertIn('BAN', rules(found, 'error'))
		self.assertTrue(project.exists())
	def test_proposal_references_and_markdown_links(self):
		text = '🔴 $50, 1 hour. The glitch is in §3.\n\n2. The handler runs.\n\n3. See [docs](https://example.org/a).\nFix §4.\n'
		found = article.lint_text(text, kind='proposal', lang='en', bans=[])
		self.assertIn('REF-DANGLING', rules(found, 'error'))
		self.assertIn('PROPOSAL-MARKDOWN-LINK', rules(found))
		self.assertNotIn('SENT-SPLIT', rules(found))
	def test_cli_exit_codes(self):
		self.assertEqual(self.cli('df_article', 'lint', GOLD).returncode, 0)
		bad = self.put('bad.md', wrap('Furthermore, the website is robust.'))
		result = self.cli('df_article', 'lint', bad)
		self.assertEqual(result.returncode, 1)
		self.assertIn('EN-CONNECTIVE-START', result.stdout)
class ResponseTests(TemporaryCase):
	def test_repeated_answer_is_a_signal_only_for_the_later_answer(self):
		self.put('j/res/4.md', 'Answer about arrow semantics.\n')
		later = self.put('j/res/5.md', 'Answer about arrow semantics.\n')
		self.assertIn('RESP-DUP', rules(article.check_response(later), 'warning'))
		self.assertNotIn('RESP-DUP', rules(article.check_response(later), 'error'))
		self.assertNotIn('means the new request was not executed', str(article.check_response(later)))
		self.assertNotIn('RESP-DUP', rules(article.check_response(self.root / 'j/res/4.md')))
		candidate = self.put('scratch/answer.md', 'Answer about arrow semantics.\n')
		self.assertIn('RESP-DUP', rules(article.check_response(candidate, journal=self.root / 'j')))
	def test_removal_claims_are_checked_against_the_file(self):
		draft = self.put('draft.md', 'Container `GTM-WWDQT6Q9` loads.\nThe tag is brittle.\n')
		answer = self.put('answer.md', 'Removed evaluative epithets (`Critical`, `brittle`) and method codes (`M-*`).\n')
		claims = [f for f in article.check_response(answer, against=[draft]) if 'RESP-CLAIM' == f.rule]
		self.assertEqual(len(claims), 1)
		self.assertIn('`brittle`', claims[0].message)
	def test_procedural_filler(self):
		answer = self.put('answer.md', 'In accordance with rule `SCOPE-2` the file and its backup snapshot were not modified.\n')
		self.assertIn('RESP-PROCEDURAL', rules(article.check_response(answer)))
class LexiconAndProjectionTests(TemporaryCase):
	def test_lexicon_entries_are_complete_and_compile(self):
		for entry in article.load_lexicon():
			self.assertTrue({'id', 'severity', 'kinds', 'lang', 'where', 'patterns', 'why', 'fix', 'source'} <= set(entry), entry.get('id'))
			self.assertIn(entry['severity'], ('error', 'warning'))
			self.assertTrue(set(entry['kinds']) <= {'article', 'proposal', 'letter', 'response'})
			for pattern in entry['patterns']:
				re.compile(pattern)
	def test_trailing_conditional_recommendation_is_flagged(self):
		text = wrap('Storefront has religious products: `curl`\n> mihrab clock', recommendations=('**[§I.1](#I.1)** → Submit an appeal in Meta Support if catalog products do not constitute religious practices.',))
		findings = article.lint_text(text)
		self.assertIn('REC-TRAILING-CONDITION', rules(findings, 'error'))
	def test_conditional_recommendation_must_branch_from_part_two_diagnostic_step(self):
		text_bad = wrap('Storefront has religious products: `curl`\n> mihrab clock', recommendations=('If the catalog of **[§I.1](#I.1)** is decorative → Submit an appeal.',))
		findings_bad = article.lint_text(text_bad)
		self.assertIn('GRAPH-CONDITIONAL-STEP', rules(findings_bad, 'error'))
		text_good = wrap('Storefront bottleneck: `curl`\n> slow', recommendations=('Profile interactions with DevTools (**[§I.1](#I.1)**).', 'If the bottleneck of **[§II.1](#II.1)** turns out to be script execution → split bundle.'))
		findings_good = article.lint_text(text_good)
		self.assertNotIn('GRAPH-CONDITIONAL-STEP', rules(findings_good, 'error'))
	def test_build_native_uses_shared_skills_without_project_wrappers(self):
		primary = self.root / 'canonical'
		for relative in ('rules', 'platforms', 'skills/upwork-init', 'agents'):
			(primary / relative).mkdir(parents=True, exist_ok=True)
		for path in runtime.PRIMARY.joinpath('rules').glob('*.md'):
			shutil.copyfile(path, primary / 'rules' / path.name)
		for relative in ('runtime.json', 'platforms/codex.md', 'skills/upwork-init/SKILL.md', 'agents/worker.md'):
			shutil.copyfile(runtime.PRIMARY / relative, primary / relative)
		shutil.copytree(runtime.PRIMARY / 'skills/df-article', primary / 'skills/df-article')
		output = self.root / 'workspace'
		self.assertTrue(configuration.build_native(output, primary=primary)['valid'])
		self.assertFalse((output / '.agents/skills/df-article/SKILL.md').exists())
		manifest = json.loads((primary / 'platforms/antigravity/skills.json').read_text(encoding='utf-8'))
		self.assertEqual(manifest['entries'], [{'path': (primary / 'skills').as_posix()}])
		self.assertTrue((primary / 'skills/df-article/SKILL.md').is_file())
		self.assertIn('10-client-text.md', (output / '.codex/config.toml').read_text(encoding='utf-8'))
