# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from html.parser import HTMLParser
from typing import override
from Df.Harness.Research.HtmlAnchorResolver import HtmlAnchorResolver
from Df.Harness.lib.research import VOID_ELEMENTS
import json
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_HIDDEN_TAGS = frozenset({'head', 'script', 'style', 'noscript', 'template', 'svg'})
class HtmlData(HTMLParser):
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__extract_html()`
	# @see :meth:`html.parser.HTMLParser.__init__()`
	@override
	def __init__(self) -> None:
		super().__init__(convert_charrefs=True)
		self.stack, self.text, self.headings, self.anchors, self.scripts, self.json_ld = ([], [], [], [], [], [])
		self.title, self.meta, self.meta_all, self.canonical, self.heading, self.script = ('', {}, {}, [], None, None)
		self.links, self.link = ([], None)
		self.images, self.embeds = ([], [])
		self.anchor_ranges, self.section_ranges = ({}, [])
		self.position = 0
	# @used-by :meth:`HtmlData.handle_endtag()`
	def __close_script(self) -> None:
		if 'application/ld+json' == self.script['type']:
			try:
				self.json_ld.append(json.loads(self.script['text']))
			except ValueError:
				self.json_ld.append({'parse_error': True, 'raw': self.script['text']})
		self.script = None
	# @used-by :meth:`HtmlData.handle_endtag()`
	def __close_stack_to(self, tag: str) -> None:
		for i in range(len(self.stack) - 1, -1, -1):
			if self.stack[i]['tag'] == tag:
				for frame in self.stack[i:]:
					frame['end'] = self.position
					anchor = frame['raw_anchor']
					if anchor:
						for span in self.anchor_ranges.get(anchor, []):
							if None is span['end']:
								span['end'] = self.position
				del self.stack[i:]
				break
	# @used-by :meth:`HtmlData.handle_starttag()`
	def __handle_anchor(self, tag: str, anchor: str, is_void: bool, hidden_ctx: bool) -> None:
		parent_frame = self.stack[-1] if self.stack else None
		self.anchors.append(anchor)
		self.anchor_ranges.setdefault(anchor, []).append({'start': self.position, 'end': self.position if is_void else None, 'tag': tag, 'parent': parent_frame, 'hidden': hidden_ctx})
		if not hidden_ctx:
			for frame in self.stack:
				if not frame['hidden']:
					frame['anchors'].append(anchor)
			if self.heading:
				self.heading['_child_anchors'].append(anchor)
	# @used-by :meth:`HtmlData.handle_starttag()`
	def __handle_heading(self, tag: str, attrs: dict, anchor: str | None) -> None:
		pos = self.position
		level = int(tag[1])
		for section in self.section_ranges:
			if None is section['end'] and section['level'] >= level:
				section['end'] = pos
		self.heading = {'level': level, 'text': '', 'anchor': attrs.get('id'), 'ancestor_anchors': [x['anchor'] for x in self.stack if x['anchor'] and (not x['hidden'])], 'start': pos, 'end': None, '_head_end': None, '_frames': list(self.stack), '_child_anchors': [anchor] if anchor else []}
		self.section_ranges.append(self.heading)
	# @used-by :meth:`HtmlData.handle_starttag()`
	def __handle_media(self, tag: str, attrs: dict) -> None:
		if 'a' == tag and attrs.get('href'):
			self.link = {'href': attrs['href'], 'text': ''}
		elif 'img' == tag:
			self.images.append({'src': attrs.get('src') or attrs.get('data-src') or '', 'alt': attrs.get('alt', ''), 'has_alt_attr': 'alt' in attrs, 'width': attrs.get('width'), 'height': attrs.get('height')})
		elif tag in ('iframe', 'video') and (attrs.get('src') or attrs.get('data-src')):
			self.embeds.append({'tag': tag, 'src': attrs.get('src') or attrs.get('data-src')})
	# @used-by :meth:`HtmlData.handle_starttag()`
	def __handle_meta_and_script(self, tag: str, attrs: dict) -> None:
		if 'meta' == tag:
			name = attrs.get('name') or attrs.get('property')
			if name:
				self.meta[name] = attrs.get('content', '')
				self.meta_all.setdefault(name, []).append(attrs.get('content', ''))
		elif 'link' == tag and 'canonical' in attrs.get('rel', '').split():
			self.canonical.append(attrs.get('href'))
		elif 'script' == tag:
			self.script = {'src': attrs.get('src'), 'type': attrs.get('type'), 'text': ''}
			if attrs.get('src'):
				self.scripts.append(attrs['src'])
	# @used-by :meth:`HtmlData.result()`
	def __image_alt_summary(self) -> dict[str, int]:
		site_name = (self.meta.get('og:site_name') or '').strip()
		total = len(self.images)
		empty_alt = sum((1 for img in self.images if not (img.get('alt') or '').strip()))
		filename_alt = sum((1 for img in self.images if (img.get('alt') or '').strip() and re.search('(?i)\\.(?:jpe?g|png|gif|webp|avif|svg|bmp|tiff?)\\b', (img.get('alt') or '').strip())))
		repeated_alt = sum((1 for img in self.images if site_name and (img.get('alt') or '').strip().lower() == site_name.lower()))
		return {'total': total, 'empty_alt': empty_alt, 'filename_like_alt': filename_alt, 'repeated_site_name_alt': repeated_alt, 'descriptive_alt': max(0, total - empty_alt - filename_alt - repeated_alt)}
	# @used-by :meth:`HtmlData.result()`
	def __seo_diagnostics(self, title_str: str, clean_headings: list[dict]) -> dict:
		h1_count = sum((1 for h in clean_headings if 1 == h.get('level')))
		meta_desc = self.meta.get('description', '')
		spaced_brand = bool(re.search('\\b(?:[A-Za-z]\\s+){3,}[A-Za-z]\\b', (self.meta.get('og:site_name') or '') + ' ' + json.dumps(self.json_ld, ensure_ascii=False)))
		json_ld_types = [item.get('@type') for item in self.json_ld if isinstance(item, dict) and item.get('@type')]
		empty_desc = any((isinstance(item, dict) and 'description' in item and (not str(item.get('description') or '').strip()) for item in self.json_ld))
		insecure_img = any((isinstance(item, dict) and isinstance(item.get('image'), str) and (item['image'].startswith('http://') or item['image'].startswith('//') or item['image'].startswith('/')) for item in self.json_ld))
		return {'h1_count': h1_count, 'missing_h1': 0 == h1_count, 'multiple_h1': 1 < h1_count, 'title_length': len(title_str), 'overlong_title': 65 < len(title_str), 'meta_description_length': len(meta_desc), 'missing_meta_description': not bool(meta_desc.strip()), 'spaced_brand_name': spaced_brand, 'json_ld_types': json_ld_types, 'empty_json_ld_description': empty_desc, 'insecure_or_relative_json_ld_image': insecure_img}
	# @used-by :meth:`html.parser.HTMLParser.handle_data()`
	# @see :meth:`html.parser.HTMLParser.handle_data()`
	@override
	def handle_data(self, value: str) -> None:
		tags = {frame['tag'] for frame in self.stack}
		if self.script:
			self.script['text'] += value
		if 'title' in tags:
			self.title += value
		if self.heading:
			self.heading['text'] += value
		if None is not self.link and (not tags.intersection(('script', 'style'))):
			self.link['text'] += value
		if not tags.intersection(('script', 'style', 'head')):
			self.text.append(value)
			self.position += len(value)
	# @used-by :meth:`html.parser.HTMLParser.handle_endtag()`
	# @see :meth:`html.parser.HTMLParser.handle_endtag()`
	@override
	def handle_endtag(self, tag: str) -> None:
		if 'a' == tag and None is not self.link:
			self.link['text'] = ' '.join(self.link['text'].split())
			self.links.append(self.link)
			self.link = None
		if self.heading and re.fullmatch('h[1-6]', tag):
			self.heading['text'] = ' '.join(self.heading['text'].split())
			self.heading['_head_end'] = self.position
			self.headings.append(self.heading)
			self.heading = None
		if 'script' == tag and self.script:
			self.__close_script()
		self.__close_stack_to(tag)
		if tag in ('p', 'div', 'section', 'li', 'br') or re.fullmatch('h[1-6]', tag):
			self.text.append('\n')
			self.position += 1
	# @used-by :meth:`html.parser.HTMLParser.handle_starttag()`
	# @see :meth:`html.parser.HTMLParser.handle_starttag()`
	@override
	def handle_starttag(self, tag: str, attrs) -> None:
		attrs_d = dict(attrs)
		is_void = tag in VOID_ELEMENTS
		hidden_ctx = bool({f['tag'] for f in self.stack} & _HIDDEN_TAGS) or tag in _HIDDEN_TAGS
		anchor = attrs_d.get('id') or (attrs_d.get('name') if 'a' == tag else None)
		if anchor:
			self.__handle_anchor(tag, anchor, is_void, hidden_ctx)
		self.__handle_media(tag, attrs_d)
		self.__handle_meta_and_script(tag, attrs_d)
		if re.fullmatch('h[1-6]', tag) and (not hidden_ctx):
			self.__handle_heading(tag, attrs_d, anchor)
		if not is_void:
			self.stack.append({'tag': tag, 'anchor': anchor if not hidden_ctx else None, 'raw_anchor': anchor, 'hidden': hidden_ctx, 'start': self.position, 'end': None, 'anchors': [anchor] if anchor and (not hidden_ctx) else []})
	# @used-by :meth:`Df.Harness.Perf.SuiteProfiler.SuiteProfiler.profile()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__extract_html()`
	# @used-by :meth:`Df.Harness.TestRunner.ParallelRunner.ParallelRunner.__run_unittest_modules()`
	# @used-by :meth:`Df.Harness.TestRunner.SuiteRunner.SuiteRunner.__run_unittest_suite()`
	# @used-by :meth:`test_registration_portability.RegistrationTests.test_slow_previous_success_does_not_erase_a_newer_failed_attempt()`
	def result(self) -> dict:
		plain = ''.join(self.text)
		clean_text = '\n'.join((x.strip() for x in plain.splitlines() if x.strip()))
		title_str = ' '.join(self.title.split())
		clean_headings, sections, anchor_ranges, anchor_content, all_anchors, ambiguous_set = HtmlAnchorResolver(plain, self.anchors, self.anchor_ranges, self.section_ranges).resolve()
		word_count = len(re.findall('\\w+', clean_text))
		return {'title': title_str, 'meta': self.meta, 'meta_all': self.meta_all, 'canonical': self.canonical, 'headings': clean_headings, 'anchors': sorted(all_anchors), 'links': self.links, 'scripts': self.scripts, 'images': self.images, 'image_alt_summary': self.__image_alt_summary(), 'embeds': self.embeds, 'word_count': word_count, 'seo_diagnostics': self.__seo_diagnostics(title_str, clean_headings), 'json_ld': self.json_ld, 'sections': sections, 'anchor_ranges': anchor_ranges, 'anchor_content': anchor_content, 'ambiguous_anchors': sorted(ambiguous_set), 'text': clean_text}
