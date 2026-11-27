# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from html.parser import HTMLParser
from typing import override
from Df.Harness.lib.research import dfh_document_urls
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class HtmlReferences(HTMLParser):
	# @used-by :func:`Df.Harness.lib.completion_links.dfh_authored_nonquote_hrefs()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__authored_targets()`
	# @used-by :meth:`Df.Harness.Research.LinkAuditor.LinkAuditor.__collect_authored_targets()`
	# @used-by :meth:`Df.Harness.Research.LinkAuditor.LinkAuditor.references()`
	# @used-by :meth:`Df.Harness.Research.NetworkLinkChecker.NetworkLinkChecker.__check_anchor_status()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_links_markdown_lib_and_network_checker()`
	# @see :meth:`html.parser.HTMLParser.__init__()`
	@override
	def __init__(self, *, authored_only: bool=False) -> None:
		super().__init__(convert_charrefs=True)
		self.anchors: list[str] = []
		self.links: list[str] = []
		self.authored_only = authored_only
		self.literal_depth = 0
	# @used-by :meth:`html.parser.HTMLParser.handle_data()`
	# @see :meth:`html.parser.HTMLParser.handle_data()`
	@override
	def handle_data(self, data: str) -> None:
		if self.authored_only and (not self.literal_depth):
			self.links.extend(dfh_document_urls(data))
	# @used-by :meth:`html.parser.HTMLParser.handle_endtag()`
	# @see :meth:`html.parser.HTMLParser.handle_endtag()`
	@override
	def handle_endtag(self, tag: str) -> None:
		if self.authored_only and tag in ('pre', 'code', 'blockquote'):
			self.literal_depth = max(0, self.literal_depth - 1)
	# @used-by :meth:`html.parser.HTMLParser.handle_starttag()`
	# @see :meth:`html.parser.HTMLParser.handle_starttag()`
	@override
	def handle_starttag(self, tag: str, attrs) -> None:
		if self.authored_only and tag in ('pre', 'code', 'blockquote'):
			self.literal_depth += 1
		if not (self.authored_only and self.literal_depth):
			values = dict(attrs)
			if values.get('id'):
				self.anchors.append(values['id'])
			if 'a' == tag:
				if values.get('name') and values['name'] != values.get('id'):
					self.anchors.append(values['name'])
				if values.get('href'):
					self.links.append(values['href'])
			elif 'img' == tag and values.get('src'):
				self.links.append(values['src'])
