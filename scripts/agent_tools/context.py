# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from .storage import data_dir_for, locked, replace_bytes
from .journal import canonicalize_journal_dir_identity, get_existing_step_ids, journal_pair_dirs, step_errors, step_file, answer_groups
# 2026-11-03
# "Refactor generate_context.py to export only current timestamp and Agent KB excluding Evidence":
# https://github.com/dmitry-ai/harness/issues/42
# @used-by :func:`assemble()`
# @used-by :func:`generate()`
def default_context_config(root: Path | str | None=None) -> dict:
	out_rel = 'ꙮ/0/Context.md'
	kb_glob = 'ꘖ/KB/**/*.md'
	ev_excl = 'ꘖ/KB/Evidence/**'
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	if None is not root:
		from .path_registry import project_paths
		pp = project_paths(root, exact_root=True)
		if pp.context_output.is_relative_to(pp.root):
			out_rel = pp.context_output.relative_to(pp.root).as_posix()
		kb_rel = pp.kb_dir.relative_to(pp.root).as_posix() if pp.kb_dir.is_relative_to(pp.root) else pp.kb_dir.as_posix()
		ev_rel = pp.evidence_dir.relative_to(pp.root).as_posix() if pp.evidence_dir.is_relative_to(pp.root) else pp.evidence_dir.as_posix()
		kb_glob = f'{kb_rel}/**/*.md'
		ev_excl = f'{ev_rel}/**'
	return {
		'version': 1,
		'output': out_rel,
		'sections': [
			{
				'title': 'Agent KB',
				'globs': [kb_glob],
				'exclude': [ev_excl],
				'optional': True,
			}
		],
	}
# 2026-11-03
# "Refactor generate_context.py to export only current timestamp and Agent KB excluding Evidence":
# https://github.com/dmitry-ai/harness/issues/42
# @used-by :func:`assemble()`
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
# 2026-10-11
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by :func:`generate()`
def inside(root: Path, path: str | Path) -> Path:
	target = (root / path).resolve()
	if not target.is_relative_to(root.resolve()):
		raise ValueError(f'Path escapes project root: {path}')
	r = target
	return r
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# @used-by :func:`assemble()`
def _inside_allowed(root: Path, path: str | Path, allowed_roots: tuple[Path, ...]=()) -> Path:
	p = Path(path)
	target = p.resolve() if p.is_absolute() else (root / p).resolve()
	for base in (root.resolve(), *(ar.resolve() for ar in allowed_roots)):
		if target.is_relative_to(base):
			return target
	raise ValueError(f'Path escapes project root: {path}')
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# @used-by :func:`assemble()`
# @used-by :func:`generate()`
def _expand_entry(pp, raw: str | Path) -> str:
	text = str(raw)
	return pp.expand(text) if ('${' in text or '%' in text) else text
# @used-by :func:`assemble()`
# @used-by :func:`discover_letters()`
# @used-by :meth:`test_agent_tools.ContextTests.test_empty_final_never_falls_back_to_draft()`
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
# @used-by :func:`assemble()`
# @used-by :meth:`test_agent_tools.ContextTests.test_final_without_draft_and_new_year_nested_letters()`
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
# @used-by :func:`assemble()`
def _fence(text: str) -> str:
	return '`' * max(3, max((len(m.group()) + 1 for m in re.finditer('`+', text)), default=3))
# 2026-10-11
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# @used-by :func:`generate()`
# @used-by :meth:`test_agent_tools.ContextTests.test_default_context_config_includes_agent_kb_and_excludes_evidence_subfolder()`
# @used-by :meth:`test_agent_tools.ContextTests.test_sources_and_fences_preserved_in_configured_order()`
# @used-by :meth:`test_context_and_storage_determinism.ContextAndStorageDeterminismTests.test_generate_accepts_explicit_now_for_deterministic_timestamp()`
# @used-by :meth:`test_parallel_runner.ParallelRunnerTests.test_context_generate_accepts_fixed_now()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_exact_quotes_code_and_source_copies_are_not_rewritten_or_rejected()`
def assemble(root: Path, manifest: dict | None=None, now: datetime | None=None) -> tuple[str, list[Path]]:
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import canonicalize_root_dir, project_paths
	import glob as glob_mod
	root = canonicalize_root_dir(root)
	pp = project_paths(root, exact_root=True)
	allowed_roots = (*pp.linked_roots, *([pp.kb_dir] if not pp.kb_dir.resolve().is_relative_to(root) else ()))
	if None is manifest:
		manifest = default_context_config(root)
	if 1 != manifest.get('version') or not manifest.get('sections'):
		raise ValueError('Context manifest requires version=1 and nonempty sections')
	timestamp = (now or datetime.now(timezone.utc)).isoformat(timespec='seconds')
	# 2026-11-03
	# "Refactor generate_context.py to export only current timestamp and Agent KB excluding Evidence":
	# https://github.com/dmitry-ai/harness/issues/42
	blocks = [f'# Context\n\nGenerated: {timestamp}\n']
	selected = []
	seen = set()
	for section in manifest['sections']:
		items = [(_inside_allowed(root, _expand_entry(pp, path), allowed_roots), None) for path in section.get('files', [])]
		for raw_pattern in section.get('globs', []):
			pattern = _expand_entry(pp, raw_pattern)
			pat_p = Path(pattern)
			if '..' in pat_p.parts:
				raise ValueError(f'Invalid glob: {raw_pattern}')
			if pat_p.is_absolute():
				if str(raw_pattern) == pattern and (not any((pat_p.is_relative_to(ar.resolve()) for ar in (root, *allowed_roots)))):
					raise ValueError(f'Invalid glob: {raw_pattern}')
				matches = sorted((Path(m).resolve() for m in glob_mod.glob(pattern, recursive=True) if Path(m).is_file()))
			else:
				matches = sorted((p for p in root.glob(pattern) if p.is_file()))
			if not matches and (not section.get('optional', False)):
				raise FileNotFoundError(f'No sources match {raw_pattern}')
			items.extend(((_inside_allowed(root, p, allowed_roots), None) for p in matches))
		# 2026-10-16
		# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
		# https://github.com/dmitry-ai/harness/issues/6
		for raw_rel in section.get('drafts', []):
			relative = _expand_entry(pp, raw_rel)
			directory = _inside_allowed(root, relative, allowed_roots)
			if not directory.is_dir() and section.get('optional', False):
				continue
			if not directory.is_dir():
				raise FileNotFoundError(directory)
			groups = sorted({path.parent for path in directory.rglob('*.md') if path.name in ('draft.md', 'final.md')})
			for group in groups:
				chosen = resolve_letter_file(group)
				if chosen:
					items.append((_inside_allowed(root, chosen, allowed_roots), None))
		# 2026-10-14
		# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
		# https://github.com/dmitry-ai/harness/issues/3
		for raw_jrel in section.get('journals', []):
			journal_rel = _expand_entry(pp, raw_jrel)
			jdir = _inside_allowed(root, journal_rel, allowed_roots)
			# 2026-11-21
			# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
			# https://github.com/dmitry-ai/harness/issues/109
			if not jdir.is_dir():
				canon_j = canonicalize_journal_dir_identity(jdir)
				if canon_j.is_dir():
					jdir = _inside_allowed(root, canon_j, allowed_roots)
				elif journal_rel in ('\ua66e/1 - Analysis', '\ua66e/1 - \u0410\u043d\u0430\u043b\u0438\u0437'):
					alt = _inside_allowed(root, '\ua66e/1 - \u0410\u043d\u0430\u043b\u0438\u0437' if '\ua66e/1 - Analysis' == journal_rel else '\ua66e/1 - Analysis', allowed_roots)
					if alt.is_dir():
						jdir = alt
			if not jdir.is_dir():
				if section.get('optional', False):
					continue
				raise FileNotFoundError(f'Missing journal directory: {raw_jrel}')
			step_ids = sorted(get_existing_step_ids(jdir))
			# 2026-11-20
			# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
			# https://github.com/dmitry-ai/harness/issues/101
			req_dir, res_dir = journal_pair_dirs(jdir)
			# 2026-10-15
			# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
			# https://github.com/dmitry-ai/harness/issues/4
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
						items.append((_inside_allowed(root, step_file(req_dir, member, directory=jdir), allowed_roots), 'User (req; shared answer group ' + group['turn'] + ')'))
					for member in group['steps']:
						items.append((_inside_allowed(root, step_file(res_dir, member, directory=jdir), allowed_roots), 'Agent (one final answer shared across requests; group ' + group['turn'] + ')'))
					continue
				for folder_dir, role in ((req_dir, 'User (req)'), (res_dir, 'Agent (res)')):
					# 2026-11-21
					# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
					# https://github.com/dmitry-ai/harness/issues/109
					candidate = step_file(folder_dir, step_id, directory=jdir)
					if candidate.is_file() and candidate.read_text(encoding='utf-8').strip():
						items.append((_inside_allowed(root, candidate, allowed_roots), role))
		for group in section.get('letters', []):
			directory = _inside_allowed(root, _expand_entry(pp, group['root']), allowed_roots)
			if not directory.is_dir() and section.get('optional', False):
				continue
			items.extend(((_inside_allowed(root, p, allowed_roots), group['author']) for p in discover_letters(directory, group.get('languages', ['EN', 'RU']))))
		excl_patterns = [_expand_entry(pp, pat) for pat in section.get('exclude', [])]
		filtered_items = []
		for p, author in items:
			rel_for_excl = p.relative_to(root) if p.is_relative_to(root) else Path(p.as_posix())
			if not _is_excluded(rel_for_excl, excl_patterns):
				filtered_items.append((p, author))
		items = filtered_items
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
			label = source.relative_to(root).as_posix() if source.is_relative_to(root) else source.as_posix()
			blocks.append(f'\n## {label}\n')
			if author:
				blocks.append(f'\nAuthor: {author}\n')
			blocks.append(f'\n{fence}markdown\n{content}')
			blocks.append(('' if content.endswith('\n') else '\n') + f'{fence}\n')
	if not selected:
		raise ValueError('No sources selected')
	r = (''.join(blocks), selected)
	return r
# 2026-10-11
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-11-23
# "Eliminate wall-clock race in context.generate and pre-lock flush race in storage.locked":
# https://github.com/dmitry-ai/harness/issues/158
# @used-by :func:`agent_tools.cli.main()`
# @used-by :meth:`test_agent_tools.ContextTests.test_default_context_config_includes_agent_kb_and_excludes_evidence_subfolder()`
# @used-by :meth:`test_agent_tools.ContextTests.test_missing_input_fails_and_dry_run_writes_nothing()`
# @used-by :meth:`test_agent_tools.ContextTests.test_output_cannot_overwrite_input_or_escape_root()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_context_and_storage_determinism.ContextAndStorageDeterminismTests.test_generate_accepts_explicit_now_for_deterministic_timestamp()`
# @used-by :meth:`test_onboarding.IsolationTests.test_incomplete_journal_does_not_replace_context()`
# @used-by :meth:`test_parallel_runner.ParallelRunnerTests.test_context_generate_accepts_fixed_now()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_proposal_export_selects_each_language_final_or_existing_draft()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_group_crash_reserves_all_numbers_and_preserves_previous_context()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
def generate(root: Path, config: Path | dict | None=None, output: Path | None=None, dry_run=False, now: datetime | None=None):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import canonicalize_root_dir, project_paths
	root = canonicalize_root_dir(root)
	pp = project_paths(root, exact_root=True)
	# 2026-11-03
	# "Refactor generate_context.py to export only current timestamp and Agent KB excluding Evidence":
	# https://github.com/dmitry-ai/harness/issues/42
	if None is config:
		manifest = default_context_config(root)
	elif isinstance(config, dict):
		manifest = config
	else:
		config_path = Path(config).resolve() if Path(config).is_absolute() else (root / config).resolve()
		if not config_path.is_file():
			raise FileNotFoundError(config_path)
		manifest = json.loads(config_path.read_text(encoding='utf-8-sig'))
	default_out = pp.context_output.relative_to(root).as_posix() if pp.context_output.is_relative_to(root) else 'ꙮ/0/Context.md'
	# 2026-10-14
	# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
	# https://github.com/dmitry-ai/harness/issues/3
	# @used-by :func:`generate()`
	def build():
		content, sources = assemble(root, manifest, now=now)
		raw_out = output if None is not output else _expand_entry(pp, manifest.get('output', default_out))
		target = inside(root, raw_out)
		if target in sources or (isinstance(config, (str, Path)) and target == (Path(config).resolve() if Path(config).is_absolute() else (root / config).resolve())):
			raise ValueError('Context output would overwrite an input')
		if not dry_run:
			replace_bytes(target, content.encode('utf-8'))
		r = (target, content, sources)
		return r
	if dry_run:
		return build()
	with locked(data_dir_for(root) / 'context.lock'):
		return build()
