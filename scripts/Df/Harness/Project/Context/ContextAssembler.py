# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.journal import answer_groups, canonicalize_journal_dir_identity, get_existing_step_ids, journal_pair_dirs, step_errors, step_file
from datetime import datetime, timezone
from Df.Harness.Project.Context.LetterDiscoverer import LetterDiscoverer
import glob as glob_mod
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ContextAssembler:
	# @used-by :func:`agent_tools.context.assemble()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextGenerator.ContextGenerator.__build()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_context_classes()`
	def __init__(self, root: Path, manifest: dict | None=None, now: datetime | None=None) -> None:
		self.__root = root
		self.__manifest = manifest
		self.__now = now
	# @used-by :meth:`ContextAssembler.__collect_section_items()`
	@staticmethod
	def __collect_drafts(root: Path, pp, allowed: tuple[Path, ...], section: dict, items: list) -> None:
		for raw_rel in section.get('drafts', []):
			directory = LetterDiscoverer.inside_allowed(root, LetterDiscoverer.expand_entry(pp, raw_rel), allowed)
			if not directory.is_dir():
				if section.get('optional', False):
					continue
				raise FileNotFoundError(directory)
			for group in sorted({path.parent for path in directory.rglob('*.md') if path.name in ('draft.md', 'final.md')}):
				chosen = LetterDiscoverer.resolve_letter_file(group)
				if chosen:
					items.append((LetterDiscoverer.inside_allowed(root, chosen, allowed), None))
	# @used-by :meth:`ContextAssembler.__collect_section_items()`
	@staticmethod
	def __collect_globs(root: Path, pp, allowed: tuple[Path, ...], section: dict, items: list) -> None:
		for raw_pattern in section.get('globs', []):
			pattern = LetterDiscoverer.expand_entry(pp, raw_pattern)
			pat_p = Path(pattern)
			if '..' in pat_p.parts:
				raise ValueError(f'Invalid glob: {raw_pattern}')
			if pat_p.is_absolute():
				if str(raw_pattern) == pattern and (not any((pat_p.is_relative_to(ar.resolve()) for ar in (root, *allowed)))):
					raise ValueError(f'Invalid glob: {raw_pattern}')
				matches = sorted((Path(m).resolve() for m in glob_mod.glob(pattern, recursive=True) if Path(m).is_file()))
			else:
				matches = sorted((p for p in root.glob(pattern) if p.is_file()))
			if not matches and (not section.get('optional', False)):
				raise FileNotFoundError(f'No sources match {raw_pattern}')
			items.extend(((LetterDiscoverer.inside_allowed(root, p, allowed), None) for p in matches))
	# @used-by :meth:`ContextAssembler.__collect_journals()`
	@staticmethod
	def __collect_journal_steps(root: Path, allowed: tuple[Path, ...], jdir: Path, items: list) -> None:
		req_dir, res_dir = journal_pair_dirs(jdir)
		group_by_step = {step: group for group in answer_groups(jdir) for step in group['steps']}
		added_groups: set[str] = set()
		for step_id in sorted(get_existing_step_ids(jdir)):
			errors = step_errors(jdir, step_id)
			if errors:
				raise ValueError('Incomplete journal; context preserved: ' + '; '.join(errors))
			if step_id in group_by_step:
				grp = group_by_step[step_id]
				if grp['turn'] not in added_groups:
					added_groups.add(grp['turn'])
					items.extend(((LetterDiscoverer.inside_allowed(root, step_file(req_dir, m, directory=jdir), allowed), 'User (req; shared answer group ' + grp['turn'] + ')') for m in grp['steps']))
					items.extend(((LetterDiscoverer.inside_allowed(root, step_file(res_dir, m, directory=jdir), allowed), 'Agent (one final answer shared across requests; group ' + grp['turn'] + ')') for m in grp['steps']))
			else:
				for fdir, role in ((req_dir, 'User (req)'), (res_dir, 'Agent (res)')):
					cand = step_file(fdir, step_id, directory=jdir)
					if cand.is_file() and cand.read_text(encoding='utf-8').strip():
						items.append((LetterDiscoverer.inside_allowed(root, cand, allowed), role))
	# @used-by :meth:`ContextAssembler.__collect_section_items()`
	@classmethod
	def __collect_journals(cls, root: Path, pp, allowed: tuple[Path, ...], section: dict, items: list) -> None:
		for raw_jrel in section.get('journals', []):
			jdir = cls.__resolve_journal_dir(root, pp, allowed, raw_jrel)
			if not jdir.is_dir():
				if section.get('optional', False):
					continue
				raise FileNotFoundError(f'Missing journal directory: {raw_jrel}')
			cls.__collect_journal_steps(root, allowed, jdir, items)
	# @used-by :meth:`ContextAssembler.assemble()`
	@classmethod
	def __collect_section_items(cls, root: Path, pp, allowed: tuple[Path, ...], section: dict) -> list:
		items = [(LetterDiscoverer.inside_allowed(root, LetterDiscoverer.expand_entry(pp, path), allowed), None) for path in section.get('files', [])]
		cls.__collect_globs(root, pp, allowed, section, items)
		cls.__collect_drafts(root, pp, allowed, section, items)
		cls.__collect_journals(root, pp, allowed, section, items)
		for group in section.get('letters', []):
			directory = LetterDiscoverer.inside_allowed(root, LetterDiscoverer.expand_entry(pp, group['root']), allowed)
			if directory.is_dir() or (not section.get('optional', False)):
				items.extend(((LetterDiscoverer.inside_allowed(root, p, allowed), group['author']) for p in LetterDiscoverer(directory, group.get('languages', ['EN', 'RU'])).discover()))
		excl = [LetterDiscoverer.expand_entry(pp, pat) for pat in section.get('exclude', [])]
		return [(p, author) for p, author in items if not LetterDiscoverer.is_excluded(p.relative_to(root) if p.is_relative_to(root) else Path(p.as_posix()), excl)]
	# @used-by :meth:`ContextAssembler.assemble()`
	@staticmethod
	def __render_section(root: Path, title: str, items: list, seen: set[Path], selected: list[Path], blocks: list[str]) -> None:
		blocks.append(f'\n# {title}\n')
		for source, author in items:
			if source in seen:
				continue
			seen.add(source)
			content = source.read_bytes().decode('utf-8')
			if not content.strip():
				raise ValueError(f'Empty source: {source}')
			selected.append(source)
			fence = LetterDiscoverer.fence(content)
			label = source.relative_to(root).as_posix() if source.is_relative_to(root) else source.as_posix()
			blocks.append(f'\n## {label}\n')
			if author:
				blocks.append(f'\nAuthor: {author}\n')
			blocks.append(f'\n{fence}markdown\n{content}')
			blocks.append(('' if content.endswith('\n') else '\n') + f'{fence}\n')
	# @used-by :meth:`ContextAssembler.__collect_journals()`
	@staticmethod
	def __resolve_journal_dir(root: Path, pp, allowed: tuple[Path, ...], raw_jrel: str) -> Path:
		journal_rel = LetterDiscoverer.expand_entry(pp, raw_jrel)
		jdir = LetterDiscoverer.inside_allowed(root, journal_rel, allowed)
		if not jdir.is_dir():
			canon_j = canonicalize_journal_dir_identity(jdir)
			if canon_j.is_dir():
				jdir = LetterDiscoverer.inside_allowed(root, canon_j, allowed)
			elif journal_rel in ('\ua66e/1 - Analysis', '\ua66e/1 - \u0410\u043d\u0430\u043b\u0438\u0437'):
				alt = LetterDiscoverer.inside_allowed(root, '\ua66e/1 - \u0410\u043d\u0430\u043b\u0438\u0437' if '\ua66e/1 - Analysis' == journal_rel else '\ua66e/1 - Analysis', allowed)
				if alt.is_dir():
					jdir = alt
		return jdir
	# @used-by :func:`agent_tools.context.assemble()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextGenerator.ContextGenerator.__build()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_context_classes()`
	def assemble(self) -> tuple[str, list[Path]]:
		from agent_tools.path_registry import canonicalize_root_dir, project_paths
		root = canonicalize_root_dir(self.__root)
		pp = project_paths(root, exact_root=True)
		allowed = (*pp.linked_roots, *([pp.kb_dir] if not pp.kb_dir.resolve().is_relative_to(root) else ()))
		manifest = LetterDiscoverer.default_config(root) if None is self.__manifest else self.__manifest
		if 1 != manifest.get('version') or not manifest.get('sections'):
			raise ValueError('Context manifest requires version=1 and nonempty sections')
		blocks = [f"# Context\n\nGenerated: {(self.__now or datetime.now(timezone.utc)).isoformat(timespec='seconds')}\n"]
		selected, seen = ([], set())
		for section in manifest['sections']:
			items = self.__collect_section_items(root, pp, allowed, section)
			if items:
				self.__render_section(root, section['title'], items, seen, selected, blocks)
			elif not section.get('optional', False):
				raise ValueError(f"Empty source section: {section['title']}")
		if not selected:
			raise ValueError('No sources selected')
		return (''.join(blocks), selected)
