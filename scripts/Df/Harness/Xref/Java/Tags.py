# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.text.trim import df_trim_text_left, df_trim_text_left_right
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class Tags:
	__BARE_BLOCK_RE = re.compile(r'^\*?\s*@(used-by|uses)\b')
	__EXT_RUNNERS = frozenset({'build.ps1', 'CLI', 'IntelliJ', 'JUnit', 'JVM', 'META-INF/plugin.xml', 'non-instantiable', 'unused'})
	__JAVA_LANG_TYPES = frozenset({'AutoCloseable', 'Comparable', 'Iterable', 'Object', 'Runnable', 'Thread', 'Throwable'})
	__LINK_RE = re.compile(r'^\{@link\s+([^}]+)\}(.*)$')
	__LIST_TAG_RE = re.compile(r'^\*?\s*-\s*@(used-by|uses)\s+(.+?)\s*$')
	__SEE_TAG_RE = re.compile(r'^\*?\s*@see\s+(.+?)\s*$')
	# @used-by :func:`agent_tools.xref.java_tags.parse_javadoc_block()`
	# @used-by :meth:`Df.Harness.Xref.Java.Graph.Graph.__add_see_override_edges()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.__check_java_def()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.__sync_java_def_edit()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.check_file_local()`
	# @used-by :meth:`Tags.collect_file_uses()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_java_xref_classes_tokenize_index_graph_and_sync()`
	def __init__(self, lines: list[str], anchor_line: int, rel_path: str='') -> None:
		self.__lines = lines
		self.__anchor_line = anchor_line
		self.__rel_path = rel_path
	# @used-by :func:`agent_tools.xref.java_tags.parse_javadoc_block()`
	# @used-by :meth:`Df.Harness.Xref.Java.Graph.Graph.__add_see_override_edges()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.__check_java_def()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.__sync_java_def_edit()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.check_file_local()`
	# @used-by :meth:`Tags.collect_file_uses()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_java_xref_classes_tokenize_index_graph_and_sync()`
	def parse_javadoc_block(self) -> dict:
		end_idx = self.__anchor_line - 2
		r = {'desc_lines': [], 'end_line': self.__anchor_line - 1, 'has_block': False, 'see': [], 'start_line': self.__anchor_line, 'syntax_errors': [], 'used_by': [], 'uses': []}
		if 0 <= end_idx and self.__lines[end_idx].strip().endswith('*/'):
			start_idx = end_idx
			while 0 <= start_idx and (not self.__lines[start_idx].strip().startswith('/*')):
				start_idx -= 1
			if 0 <= start_idx and self.__lines[start_idx].strip().startswith('/**'):
				r = Tags.parse_javadoc_lines(self.__lines, start_idx, end_idx, self.__rel_path)
		return r
	# @used-by :meth:`Tags.__classify_javadoc_line()`
	@staticmethod
	def __build_link_entry(tag: str, rest: str, lineno: int) -> dict:
		m = Tags.__LINK_RE.match(rest)
		if None is m:
			r = {'lineno': lineno, 'link_target': None, 'note': '', 'raw_value': rest, 'tag': tag}
		else:
			r = {'lineno': lineno, 'link_target': m.group(1).strip(), 'note': m.group(2).strip(), 'raw_value': rest, 'tag': tag}
		return r
	# @used-by :meth:`Tags.parse_javadoc_lines()`
	@staticmethod
	def __classify_javadoc_line(inner: str, lineno: int, rel_path: str, desc: list[str], used_by: list[dict], uses: list[dict], see: list[dict], errs: list[str]) -> None:
		bm = Tags.__BARE_BLOCK_RE.match(inner)
		lm = Tags.__LIST_TAG_RE.match(inner)
		sm = Tags.__SEE_TAG_RE.match(inner)
		if None is not bm:
			tag = bm.group(1)
			errs.append(f'XREF: {rel_path}:{lineno} Java Javadoc forbids bare @{tag} block tag (use "- @{tag} ...")')
		elif None is not lm:
			entry = Tags.__build_link_entry(lm.group(1), lm.group(2).strip(), lineno)
			(used_by if 'used-by' == lm.group(1) else uses).append(entry)
		elif None is not sm:
			see.append({'lineno': lineno, 'raw_value': sm.group(1).strip(), 'tag': 'see'})
		elif inner and '*' != inner:
			desc.append(str(df_trim_text_left(inner, '*')).strip())
	# @used-by :meth:`Tags.resolve_target()`
	@staticmethod
	def __resolve_external_java_ref(t_clean: str, m_part: str, current_finfo: dict) -> tuple[bool, str | None]:
		head = t_clean.split('.', 1)[0] if t_clean else ''
		if head in current_finfo['imports']:
			fqn = current_finfo['imports'][head] + t_clean[len(head):]
			r: tuple[bool, str | None] = (True, f'{fqn}#{m_part.strip()}' if m_part else fqn)
		elif t_clean in Tags.__JAVA_LANG_TYPES or t_clean.startswith(('java.', 'javax.', 'com.intellij.', 'org.jetbrains.')):
			fqn = f'java.lang.{t_clean}' if t_clean in Tags.__JAVA_LANG_TYPES else t_clean
			r = (True, f'{fqn}#{m_part.strip()}' if m_part else fqn)
		else:
			r = (False, None)
		return r
	# @used-by :meth:`Tags.resolve_target()`
	@staticmethod
	def __resolve_repo_java_member(t_fqn: str, m_part: str, repo_index: dict) -> tuple[bool, str | None]:
		if not m_part:
			r: tuple[bool, str | None] = (True, t_fqn)
		else:
			clean_m = re.sub(r'\s+', ' ', m_part.strip()).replace('( ', '(').replace(' )', ')')
			cand = f'{t_fqn}#{clean_m}'
			if cand in repo_index['symbols']:
				r = (True, cand)
			else:
				mname = clean_m.split('(', 1)[0]
				hits = [sk for sk in repo_index['symbols'] if sk.startswith(f'{t_fqn}#{mname}(')]
				r = (True, hits[0]) if 1 == len(hits) else (False, None)
		return r
	# @used-by :meth:`Tags.resolve_target()`
	@staticmethod
	def __resolve_type_fqn(type_raw: str, current_finfo: dict, repo_index: dict) -> str | None:
		types, pkg = (repo_index['types'], current_finfo['package'])
		cands = [type_raw]
		if pkg:
			cands.insert(0, f'{pkg}.{type_raw}')
		head = type_raw.split('.', 1)[0]
		if head in current_finfo['imports']:
			cands.insert(0, current_finfo['imports'][head] + type_raw[len(head):])
		r: str | None = next((c for c in cands if c in types), None)
		if None is r:
			suffix = f'.{type_raw}'
			hits = [tfqn for tfqn in types if tfqn.endswith(suffix)]
			r = hits[0] if 1 == len(hits) else None
		return r
	# @used-by :meth:`Tags.format_ref()`
	@staticmethod
	def __shorten_java_type(t_fqn: str, current_finfo: dict, repo_index: dict) -> str:
		tinfo = repo_index['types'].get(t_fqn)
		if None is not tinfo:
			tpkg, tqual = (tinfo['package'], tinfo['qualname'])
			top = tqual.split('.', 1)[0]
			r = tqual if (tpkg == current_finfo['package'] or current_finfo['imports'].get(top) == (f'{tpkg}.{top}' if tpkg else top)) else t_fqn
		else:
			simple = t_fqn.rsplit('.', 1)[-1]
			r = simple if (current_finfo['imports'].get(simple) == t_fqn or t_fqn.startswith('java.lang.')) else t_fqn
		return r
	# @used-by :func:`agent_tools.xref.java_tags.collect_file_java_uses()`
	# @used-by :meth:`Df.Harness.Xref.Java.Graph.Graph.__add_java_uses_edges()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.__validate_java_file_uses()`
	@staticmethod
	def collect_file_uses(finfo: dict) -> list[dict]:
		out: list[dict] = []
		for dinfo in finfo['defs']:
			hdr = Tags(finfo['lines'], dinfo['doc_anchor_line'], finfo['rel_path']).parse_javadoc_block()
			caller = dinfo['enclosing_res'] if dinfo['is_anon'] else dinfo['symbol_key']
			for entry in hdr['uses']:
				out.append({**entry, 'caller_key': caller})
		return out
	# @used-by :func:`agent_tools.xref.java_tags.format_java_ref()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.__check_java_override()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.__expected_java_used_by()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.__sync_java_def_edit()`
	@staticmethod
	def format_ref(target_key: str, current_finfo: dict, repo_index: dict, *, wrap_link: bool=True) -> str:
		if '#' not in target_key and target_key not in repo_index['types']:
			r = target_key
		else:
			t_fqn, sig = target_key.split('#', 1) if '#' in target_key else (target_key, '')
			disp = Tags.__shorten_java_type(t_fqn, current_finfo, repo_index)
			ref = f'{disp}#{sig}' if sig else disp
			r = f'{{@link {ref}}}' if wrap_link else ref
		return r
	# @used-by :func:`agent_tools.xref.java_tags.is_valid_java_external()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.__collect_actual_java_used_by()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.__sync_java_def_edit()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref_cov.DfHarnessS11Wave2bXrefCovTests.test_java_xref_covers_enums_anon_classes_overrides_and_external_tags()`
	@staticmethod
	def is_valid_external(raw_value: str, repo_root: Path) -> bool:
		token = raw_value.split()[0] if raw_value.strip() else ''
		if token in Tags.__EXT_RUNNERS or token.startswith(('http://', 'https://')):
			r = True
		elif '/' in token or token.endswith(('.gradle', '.java', '.json', '.kts', '.md', '.ps1', '.xml')):
			r = (repo_root / token).exists() or token.startswith(('META-INF/', 'src/'))
		else:
			r = False
		return r
	# @used-by :func:`agent_tools.xref.java_tags._parse_javadoc_lines()`
	# @used-by :meth:`Tags.parse_javadoc_block()`
	@staticmethod
	def parse_javadoc_lines(lines: list[str], start_idx: int, end_idx: int, rel_path: str, *, trim_lr_fn=None) -> dict:
		desc, used_by, uses, see, errs = ([], [], [], [], [])
		trim_lr = trim_lr_fn if None is not trim_lr_fn else df_trim_text_left_right
		for idx in range(start_idx, end_idx + 1):
			st = lines[idx].strip()
			if st in ('/**', '*/'):
				continue
			inner = trim_lr(st, '/**', '*/').strip()
			Tags.__classify_javadoc_line(inner, idx + 1, rel_path, desc, used_by, uses, see, errs)
		return {'desc_lines': desc, 'end_line': end_idx + 1, 'has_block': True, 'see': see, 'start_line': start_idx + 1, 'syntax_errors': errs, 'used_by': used_by, 'uses': uses}
	# @used-by :func:`agent_tools.xref.java_tags.resolve_java_target()`
	# @used-by :meth:`Df.Harness.Xref.Java.Graph.Graph.__add_java_uses_edges()`
	# @used-by :meth:`Df.Harness.Xref.Java.Graph.Graph.__add_see_override_edges()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.__collect_actual_java_used_by()`
	# @used-by :meth:`Df.Harness.Xref.Java.Syncer.Syncer.__validate_java_file_uses()`
	@staticmethod
	def resolve_target(raw_target: str, current_finfo: dict, repo_index: dict) -> tuple[bool, str | None]:
		t_part, m_part = raw_target.split('#', 1) if '#' in raw_target else (raw_target, '')
		t_clean = t_part.strip()
		t_fqn = Tags.__resolve_type_fqn(t_clean, current_finfo, repo_index) if t_clean else None
		if None is not t_fqn:
			r = Tags.__resolve_repo_java_member(t_fqn, m_part, repo_index)
		else:
			r = Tags.__resolve_external_java_ref(t_clean, m_part, current_finfo)
		return r
