# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Refactor generate_context.py to export only current timestamp and Agent KB excluding Evidence":
# https://github.com/dmitry-ai/harness/issues/42
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from .storage import data_dir_for, locked, replace_bytes
from .journal import get_existing_step_ids, step_errors, answer_groups
def default_context_config() -> dict:
	return {
		'version': 1,
		'output': 'ꙮ/0/Context.md',
		'sections': [
			{
				'title': 'Agent KB',
				'globs': ['ꘖ/KB/**/*.md'],
				'exclude': ['ꘖ/KB/Evidence/**'],
				'optional': True,
			}
		],
	}
def _is_excluded(rel_path: Path, patterns: list[str]) -> bool:
	rel_str = rel_path.as_posix()
	for pat in patterns:
		pat_norm = pat.replace('\\', '/').rstrip('/')
		if pat_norm.endswith('/**'):
			prefix = pat_norm[:-3].rstrip('/')
			if rel_str == prefix or rel_str.startswith(prefix + '/'):
				return True
		elif pat_norm.endswith('/*'):
			prefix = pat_norm[:-2].rstrip('/')
			if rel_path.parent.as_posix() == prefix:
				return True
		elif rel_path.match(pat) or rel_str == pat_norm or rel_str.startswith(pat_norm + '/'):
			return True
	return False
def inside(root: Path, path: str | Path) -> Path:
	target = (root / path).resolve()
	if not target.is_relative_to(root.resolve()):
		raise ValueError(f'Path escapes project root: {path}')
	r = target
	return r
def resolve_letter_file(path: Path, languages=('EN', 'RU')) -> Path | None:
	path = Path(path)
	if path.is_file():
		chosen = path.with_name('final.md') if 'draft.md' == path.name and path.with_name('final.md').exists() else path
	elif not path.is_dir():
		return None
	else:
		chosen = None
		for directory in [*(path / 'result' / language for language in languages), path]:
			for name in ('final.md', 'draft.md', '.md'):
				candidate = directory / name
				if candidate.exists():
					chosen = candidate
					break
			if None is not chosen:
				break
		if None is chosen:
			return None
	if not chosen.is_file() or not chosen.read_text(encoding='utf-8').strip():
		raise ValueError(f'Chosen letter is empty or not a file: {chosen}')
	return chosen
def discover_letters(root: Path, languages=('EN', 'RU')) -> list[Path]:
	if not root.is_dir():
		raise FileNotFoundError(root)
	groups = set()
	for path in root.rglob('*.md'):
		if path.name not in ('final.md', 'draft.md', '.md'):
			continue
		parent = path.parent
		if parent.name in languages and 'result' == parent.parent.name:
			parent = parent.parent.parent
		elif 'result' == parent.parent.name:
			continue
		groups.add(parent)
	r = [chosen for group in sorted(groups) if None is not (chosen := resolve_letter_file(group, languages))]
	return r
def _fence(text: str) -> str:
	return '`' * max(3, max((len(m.group()) + 1 for m in re.finditer('`+', text)), default=3))
# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Refactor generate_context.py to export only current timestamp and Agent KB excluding Evidence":
# https://github.com/dmitry-ai/harness/issues/42
def assemble(root: Path, manifest: dict | None=None, now: datetime | None=None) -> tuple[str, list[Path]]:
	root = Path(root).resolve()
	if None is manifest:
		manifest = default_context_config()
	if 1 != manifest.get('version') or not manifest.get('sections'):
		raise ValueError('Context manifest requires version=1 and nonempty sections')
	timestamp = (now or datetime.now(timezone.utc)).isoformat(timespec='seconds')
	blocks = [f'# Context\n\nGenerated: {timestamp}\n']
	selected = []
	seen = set()
	for section in manifest['sections']:
		items = [(inside(root, path), None) for path in section.get('files', [])]
		for pattern in section.get('globs', []):
			if Path(pattern).is_absolute() or '..' in Path(pattern).parts:
				raise ValueError(f'Invalid glob: {pattern}')
			matches = sorted((p for p in root.glob(pattern) if p.is_file()))
			if not matches and (not section.get('optional', False)):
				raise FileNotFoundError(f'No sources match {pattern}')
			items.extend(((inside(root, p), None) for p in matches))
		for relative in section.get('drafts', []):
			directory = inside(root, relative)
			if not directory.is_dir() and section.get('optional', False):
				continue
			if not directory.is_dir():
				raise FileNotFoundError(directory)
			groups = sorted({path.parent for path in directory.rglob('*.md') if path.name in ('draft.md', 'final.md')})
			for group in groups:
				chosen = resolve_letter_file(group)
				if chosen:
					items.append((inside(root, chosen), None))
		for journal_rel in section.get('journals', []):
			jdir = inside(root, journal_rel)
			if not jdir.is_dir() and journal_rel in ('ꙮ/1 - Analysis', 'ꙮ/1 - \u0410\u043d\u0430\u043b\u0438\u0437'):
				alt = inside(root, 'ꙮ/1 - \u0410\u043d\u0430\u043b\u0438\u0437' if 'ꙮ/1 - Analysis' == journal_rel else 'ꙮ/1 - Analysis')
				if alt.is_dir():
					jdir = alt
			if not jdir.is_dir():
				if section.get('optional', False):
					continue
				raise FileNotFoundError(f'Missing journal directory: {journal_rel}')
			step_ids = sorted(get_existing_step_ids(jdir))
			groups = answer_groups(jdir)
			group_by_step = {step: group for group in groups for step in group['steps']}
			added_groups = set()
			for step_id in step_ids:
				errors = step_errors(jdir, step_id)
				if errors:
					raise ValueError('Incomplete journal; context preserved: ' + '; '.join(errors))
				if step_id in group_by_step:
					group = group_by_step[step_id]
					if group['turn'] in added_groups:
						continue
					added_groups.add(group['turn'])
					for member in group['steps']:
						items.append((inside(root, jdir / 'req' / f'{member}.md'), 'User (req; shared answer group ' + group['turn'] + ')'))
					for member in group['steps']:
						items.append((inside(root, jdir / 'res' / f'{member}.md'), 'Agent (one final answer shared across requests; group ' + group['turn'] + ')'))
					continue
				for sub, role in (('req', 'User (req)'), ('res', 'Agent (res)')):
					candidate = jdir / sub / f'{step_id}.md'
					if candidate.is_file() and candidate.read_text(encoding='utf-8').strip():
						items.append((inside(root, candidate), role))
		for group in section.get('letters', []):
			directory = inside(root, group['root'])
			if not directory.is_dir() and section.get('optional', False):
				continue
			items.extend(((inside(root, p), group['author']) for p in discover_letters(directory, group.get('languages', ['EN', 'RU']))))
		items = [(p, author) for p, author in items if not _is_excluded(p.relative_to(root), section.get('exclude', []))]
		if not items:
			if not section.get('optional', False):
				raise ValueError(f"Empty source section: {section['title']}")
			continue
		blocks.append(f"\n# {section['title']}\n")
		for source, author in items:
			if source in seen:
				continue
			seen.add(source)
			content = source.read_bytes().decode('utf-8')
			if not content.strip():
				raise ValueError(f'Empty source: {source}')
			selected.append(source)
			fence = _fence(content)
			label = source.relative_to(root).as_posix()
			blocks.append(f'\n## {label}\n')
			if author:
				blocks.append(f'\nAuthor: {author}\n')
			blocks.append(f'\n{fence}markdown\n{content}')
			blocks.append(('' if content.endswith('\n') else '\n') + f'{fence}\n')
	if not selected:
		raise ValueError('No sources selected')
	r = (''.join(blocks), selected)
	return r
# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Refactor generate_context.py to export only current timestamp and Agent KB excluding Evidence":
# https://github.com/dmitry-ai/harness/issues/42
def generate(root: Path, config: Path | dict | None=None, output: Path | None=None, dry_run=False):
	root = Path(root).resolve()
	if None is config:
		manifest = default_context_config()
	elif isinstance(config, dict):
		manifest = config
	else:
		config_path = Path(config).resolve() if Path(config).is_absolute() else (root / config).resolve()
		if not config_path.is_file():
			raise FileNotFoundError(config_path)
		manifest = json.loads(config_path.read_text(encoding='utf-8-sig'))
	def build():
		content, sources = assemble(root, manifest)
		target = inside(root, output if None is not output else manifest.get('output', 'ꙮ/0/Context.md'))
		if target in sources or (isinstance(config, (str, Path)) and target == Path(config).resolve()):
			raise ValueError('Context output would overwrite an input')
		if not dry_run:
			replace_bytes(target, content.encode('utf-8'))
		r = (target, content, sources)
		return r
	if dry_run:
		return build()
	with locked(data_dir_for(root) / 'context.lock'):
		return build()
