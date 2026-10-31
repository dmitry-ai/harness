# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prohibit URL percent-encoding in authored Markdown links (LINK-5) and add --readable link validator":
# https://github.com/dmitry-ai/harness/issues/9
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from test_agent_tools import TemporaryCase
from test_analysis_workflow import ProjectCase
from agent_tools.analysis import publish_owned, render_analysis
from agent_tools.context import assemble
from agent_tools.journal import record_step
from agent_tools.knowledge import sync_website_card
from agent_tools.links import markdown_link, readable_link_issues, readable_reference, references, validate_file
from agent_tools.project_card import sync_block
from agent_tools import workflow
class ReadableReferenceTests(TemporaryCase):
	def setUp(self):
		super().setUp()
		(self.root / 'ꘖ').mkdir()
	def test_original_file_uri_becomes_a_readable_local_reference(self):
		encoded = 'file:///C:/work/8%20-%20burattidesigns.com/%EA%98%96/KB/Evidence/source.json'
		self.assertEqual(readable_reference(encoded), 'C:/work/8 - burattidesigns.com/ꘖ/KB/Evidence/source.json')
		link = markdown_link('Source', encoded)
		self.assertEqual(link, '[Source](<C:/work/8 - burattidesigns.com/ꘖ/KB/Evidence/source.json>)')
		self.assertEqual(readable_link_issues(link), [])
	def test_readable_source_survives_a_renderer_that_encodes_its_href(self):
		target = self.put('folder with spaces/ꘖ.json', '{}')
		source = markdown_link('Source', target)
		rendered_targets, _ = references(source)
		self.assertEqual(len(rendered_targets), 1)
		self.assertIn('%20', rendered_targets[0])
		self.assertNotIn('%20', source)
		self.assertIn('ꘖ', source)
		document = self.put('draft.md', source)
		self.assertEqual(validate_file(document, readable_links=True), [])
	def test_utf8_anchor_and_balanced_parentheses_need_no_url_encoding(self):
		target = self.put('data (copy).md', '# Section ꘖ\n')
		link = markdown_link('Section [1]', target.as_posix() + '#section-%EA%98%96')
		self.assertIn('#section-ꘖ>', link)
		self.assertIn('Section \\[1\\]', link)
		document = self.put('final.md', link)
		self.assertEqual(validate_file(document, local_anchors=True, readable_links=True), [])
	def test_encoded_authored_links_are_detected_in_all_supported_text_forms(self):
		cases = ['[Source](Evidence/with%20space.json)', '[Source](file:///C:/folder/data.json)', '[Section](#%EA%98%96)', 'https://example.org/%D0%BF%D1%83%D1%82%D1%8C', '![Figure](image%20one.png)', '<a href="https://example.org/with%20space">Source</a>', '<img src="image%20one.png">', '<p>https://example.org/with%20space</p>', 'C:/folder/with%20space.json']
		for content in cases:
			with self.subTest(content=content):
				self.assertTrue(readable_link_issues(content))
	def test_exact_quotes_code_and_source_copies_are_not_rewritten_or_rejected(self):
		exact = '[Source](https://example.org/raw%20source/%EA%98%96)'
		content = '> ' + exact + '\n\n```markdown\n' + exact + '\n```\n\n`' + exact + '`\n'
		self.assertEqual(readable_link_issues(content), [])
		self.assertEqual(readable_link_issues('<blockquote><a href="https://example.org/raw%20source">Exact</a></blockquote>'), [])
		target = self.root / 'source-copy.md'
		publish_owned(target, content)
		self.assertEqual(target.read_bytes(), content.encode())
		journal = self.root / 'journal'
		record_step(journal, exact, exact)
		self.assertEqual((journal / 'req/1.md').read_bytes(), exact.encode())
		self.assertEqual((journal / 'res/1.md').read_bytes(), exact.encode())
		exported, _ = assemble(self.root, {'version': 1, 'sections': [{'title': 'Source', 'files': ['source-copy.md']}], 'output': 'Context.md'})
		self.assertIn(content, exported)
		self.assertEqual(readable_link_issues(exported), [])
	def test_query_signatures_delimiters_literal_percent_and_invalid_utf8_are_preserved(self):
		source = 'https://example.org/with%20space/%EA%98%96%2Fpart%23x%25%FF?sig=x%2Fy%20z#%D1%8F'
		expected = 'https://example.org/with space/ꘖ%2Fpart%23x%25%FF?sig=x%2Fy%20z#\u044f'
		self.assertEqual(readable_reference(source), expected)
		self.assertEqual(readable_reference(expected), expected)
		self.assertEqual(readable_link_issues(markdown_link(None, source)), [])
	def test_publication_guard_keeps_previous_document_and_primary_json_intact(self):
		document = self.root / 'draft.md'
		publish_owned(document, 'Original draft.\n')
		for suffix in ('.md', '.txt', '.html'):
			with self.subTest(suffix=suffix):
				with self.assertRaisesRegex(ValueError, 'LINK-5'):
					publish_owned(self.root / ('final' + suffix), '[Source](https://example.org/with%20space)')
		with self.assertRaisesRegex(ValueError, 'LINK-5'):
			publish_owned(document, '[Source](https://example.org/with%20space)')
		self.assertEqual(document.read_bytes(), b'Original draft.\n')
		primary = self.root / 'primary.json'
		exact = '{"url": "https://example.org/with%20space"}\n'
		publish_owned(primary, exact)
		self.assertEqual(primary.read_bytes(), exact.encode())
	def test_cli_readability_check_catches_original_encoding_and_accepts_readable_destination(self):
		target = self.put('with space.json', '{}')
		document = self.put('final.md', '[Source](with%20space.json)')
		result = self.cli('validate_links', '--readable', document)
		self.assertNotEqual(result.returncode, 0)
		self.assertIn('LINK-5', result.stderr)
		document.write_text(markdown_link('Source', target.name), encoding='utf-8')
		result = self.cli('validate_links', '--readable', document)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
	def test_readable_navigation_links_can_address_a_directory(self):
		directory = self.root / 'folder with spaces'
		directory.mkdir()
		document = self.put('rules.md', markdown_link('Sources', directory.name))
		self.assertEqual(validate_file(document, readable_links=True), [])
		document.write_text(markdown_link('Section', directory.name + '#missing'), encoding='utf-8')
		self.assertTrue(validate_file(document, readable_links=True))
	def test_docx_hyperlinks_are_readable_without_altering_their_visible_source_text(self):
		import io
		import zipfile
		from agent_tools.upwork_data import extract_docx_markdown
		stream = io.BytesIO()
		with zipfile.ZipFile(stream, 'w') as archive:
			archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body><w:p><w:hyperlink r:id="rId1"><w:r><w:t>Original source title</w:t></w:r></w:hyperlink></w:p></w:body></w:document>')
			archive.writestr('word/_rels/document.xml.rels', '<Relationships><Relationship Id="rId1" Target="https://example.org/with%20space/%EA%98%96"/></Relationships>')
		output = extract_docx_markdown(stream.getvalue())
		self.assertIn('[Original source title](<https://example.org/with space/ꘖ>)', output)
		self.assertEqual(readable_link_issues(output), [])
class ReadableProjectTests(ProjectCase):
	def test_analysis_sources_are_readable_while_quotes_keep_their_exact_bytes(self):
		value = self.valid_analysis()
		exact = 'Exact source: https://example.org/with%20space'
		value['concerns'][0]['for'][0].update(source='Evidence/with%20space/%EA%98%96.json', quote=exact)
		output = render_analysis(value)
		self.assertIn('[Source](<Evidence/with space/ꘖ.json>)', output)
		self.assertIn('> ' + exact, output)
		self.assertEqual(readable_link_issues(output), [])
	def test_website_card_uses_readable_iri_and_keeps_original_website_selection(self):
		from test_onboarding import claim
		value = self.valid_analysis()
		value['identity'] = [claim('H-SITE-1')]
		url = 'https://example.org/with%20space/%EA%98%96?sig=x%2Fy'
		value['websites'] = [{'url': url, 'role': 'target', 'basis_id': 'H-SITE-1'}]
		result = sync_website_card(self.project, value)
		self.assertEqual(result['status'], 'published')
		content = (self.project / '.md').read_text(encoding='utf-8')
		self.assertIn('https://example.org/with space/ꘖ?sig=x%2Fy', content)
		self.assertNotIn('%EA%98%96', content)
		self.assertEqual(value['websites'][0]['url'], url)
		with self.assertRaisesRegex(ValueError, 'LINK-5'):
			sync_block(self.project, self.project / '.md', 'unsafe', '[Source](https://example.org/a%20b)')
	def test_project_check_covers_agent_kb_and_client_markdown_text_and_html(self):
		self.valid_analysis()
		files = ['ꘖ/KB/Notes.md', 'result/EN/draft.md', 'result/EN/final.txt', 'result/publish.html']
		for relative in files:
			self.put_project(relative, '[Source](https://example.org/with%20space)')
		issues = workflow.check_project(self.project)['issues']
		flagged = {issue['field'] for issue in issues if 'LINK-5' in issue['message']}
		self.assertTrue(set(files).issubset(flagged), issues)
	def test_record_answer_blocks_encoded_authored_links_before_any_journal_mutation(self):
		with self.assertRaisesRegex(ValueError, 'LINK-5'):
			workflow.record_current_answer(self.project, '[Source](https://example.org/with%20space)')
		self.assertFalse(list((self.project / 'ꙮ/1 - Analysis/res').glob('*.md')))
