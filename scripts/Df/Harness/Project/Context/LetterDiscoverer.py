# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class LetterDiscoverer:
	# @used-by :func:`agent_tools.context.discover_letters()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__collect_section_items()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_context_classes()`
	def __init__(self, root: Path, languages=('EN', 'RU')) -> None:
		self.__root = Path(root)
		self.__languages = languages
	# @used-by :meth:`LetterDiscoverer.resolve_letter_file()`
	@staticmethod
	def __pick_in_dir(path: Path, languages) -> Path | None:
		r = None
		for directory in [*(path / 'result' / language for language in languages), path]:
			for name in ('final.md', 'draft.md', '.md'):
				candidate = directory / name
				if candidate.exists():
					r = candidate
					break
			if None is not r:
				break
		return r
	# @used-by :func:`agent_tools.context.default_context_config()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.assemble()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextGenerator.ContextGenerator.__load_manifest()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_context_classes()`
	@staticmethod
	def default_config(root: Path | str | None=None) -> dict:
		out_rel, kb_glob, ev_excl = ('ꙮ/0/Context.md', 'ꘖ/KB/**/*.md', 'ꘖ/KB/Evidence/**')
		if None is not root:
			from agent_tools.path_registry import project_paths
			pp = project_paths(root, exact_root=True)
			if pp.context_output.is_relative_to(pp.root):
				out_rel = pp.context_output.relative_to(pp.root).as_posix()
			kb_rel = pp.kb_dir.relative_to(pp.root).as_posix() if pp.kb_dir.is_relative_to(pp.root) else pp.kb_dir.as_posix()
			ev_rel = pp.evidence_dir.relative_to(pp.root).as_posix() if pp.evidence_dir.is_relative_to(pp.root) else pp.evidence_dir.as_posix()
			kb_glob, ev_excl = (f'{kb_rel}/**/*.md', f'{ev_rel}/**')
		return {'version': 1, 'output': out_rel, 'sections': [{'title': 'Agent KB', 'globs': [kb_glob], 'exclude': [ev_excl], 'optional': True}]}
	# @used-by :func:`agent_tools.context.discover_letters()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__collect_section_items()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_context_classes()`
	def discover(self) -> list[Path]:
		if not self.__root.is_dir():
			raise FileNotFoundError(self.__root)
		groups: set[Path] = set()
		for path in self.__root.rglob('*.md'):
			if path.name not in ('final.md', 'draft.md', '.md'):
				continue
			parent = path.parent
			if parent.name in self.__languages and 'result' == parent.parent.name:
				groups.add(parent.parent.parent)
			elif 'result' != parent.parent.name:
				groups.add(parent)
		return [chosen for group in sorted(groups) if None is not (chosen := self.resolve_letter_file(group, self.__languages))]
	# @used-by :func:`agent_tools.context._expand_entry()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__collect_drafts()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__collect_globs()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__collect_section_items()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__resolve_journal_dir()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextGenerator.ContextGenerator.__build()`
	@staticmethod
	def expand_entry(pp, raw: str | Path) -> str:
		text = str(raw)
		return pp.expand(text) if ('${' in text or '%' in text) else text
	# @used-by :func:`agent_tools.context._fence()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__render_section()`
	@staticmethod
	def fence(text: str) -> str:
		return '`' * max(3, max((len(m.group()) + 1 for m in re.finditer('`+', text)), default=3))
	# @used-by :func:`agent_tools.context.inside()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextGenerator.ContextGenerator.__build()`
	@staticmethod
	def inside(root: Path, path: str | Path) -> Path:
		target = (root / path).resolve()
		if not target.is_relative_to(root.resolve()):
			raise ValueError(f'Path escapes project root: {path}')
		return target
	# @used-by :func:`agent_tools.context._inside_allowed()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__collect_drafts()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__collect_globs()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__collect_journal_steps()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__collect_section_items()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__resolve_journal_dir()`
	@staticmethod
	def inside_allowed(root: Path, path: str | Path, allowed_roots: tuple[Path, ...]=()) -> Path:
		p = Path(path)
		target = p.resolve() if p.is_absolute() else (root / p).resolve()
		r = next((target for base in (root.resolve(), *(ar.resolve() for ar in allowed_roots)) if target.is_relative_to(base)), None)
		if None is r:
			raise ValueError(f'Path escapes project root: {path}')
		return r
	# @used-by :func:`agent_tools.context._is_excluded()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__collect_section_items()`
	@staticmethod
	def is_excluded(rel_path: Path, patterns: list[str]) -> bool:
		rel_str = rel_path.as_posix()
		r = False
		for pat in patterns:
			pat_norm = pat.replace('\\', '/').rstrip('/')
			if pat_norm.endswith('/**'):
				prefix = pat_norm[:-3].rstrip('/')
				hit = rel_str == prefix or rel_str.startswith(prefix + '/')
			elif pat_norm.endswith('/*'):
				hit = rel_path.parent.as_posix() == pat_norm[:-2].rstrip('/')
			else:
				hit = rel_path.match(pat) or rel_str == pat_norm or rel_str.startswith(pat_norm + '/')
			if hit:
				r = True
				break
		return r
	# @used-by :func:`agent_tools.context.resolve_letter_file()`
	# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__collect_drafts()`
	# @used-by :meth:`LetterDiscoverer.discover()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_context_classes()`
	@classmethod
	def resolve_letter_file(cls, path: Path, languages=('EN', 'RU')) -> Path | None:
		p = Path(path)
		if p.is_file():
			chosen: Path | None = p.with_name('final.md') if 'draft.md' == p.name and p.with_name('final.md').exists() else p
		elif p.is_dir():
			chosen = cls.__pick_in_dir(p, languages)
		else:
			chosen = None
		if None is not chosen and (not chosen.is_file() or not chosen.read_text(encoding='utf-8').strip()):
			raise ValueError(f'Chosen letter is empty or not a file: {chosen}')
		return chosen
