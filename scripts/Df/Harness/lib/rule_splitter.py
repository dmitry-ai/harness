# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import re
import sys
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_KEEP_HEADINGS = ('passport', 'map', 'no backups', 'autosplit', 'project', '\u043f\u0430\u0441\u043f\u043e\u0440\u0442', '\u043a\u0430\u0440\u0442\u0430', '\u0437\u0430\u043f\u0440\u0435\u0442 \u0431\u044d\u043a\u0430\u043f\u043e\u0432', '\u0430\u0432\u0442\u043e\u0440\u0430\u0437\u0431\u0438\u0435\u043d\u0438\u0435')
_SLUG_TRANS = {'\u0441\u0435\u0440\u0432\u0435\u0440': 'servers', '\u0434\u043e\u0441\u0442\u0443\u043f': 'access', 'git': 'git-workflow', '\u043f\u0440\u0430\u0432\u043a': 'workflow', '\u0434\u0435\u043f\u043b\u043e\u0439': 'deploy', '\u0440\u0430\u0437\u0432\u0435\u0440\u0442': 'deploy', '\u043a\u0440\u043e\u0441\u0441\u043f\u043b\u0430\u0442\u0444\u043e\u0440\u043c': 'crossplatform', '\u0443\u043d\u0438\u0432\u0435\u0440\u0441\u0430\u043b\u044c\u043d': 'crossplatform'}
# @used-by :func:`dfh_split_rules()`
def _partition_rule_sections(content: str) -> tuple[list[str], list[str]]:
	fm_match = re.match('^---\\s*\\n(.*?)\\n---\\s*\\n', content, re.DOTALL)
	body = content[len(fm_match.group(0)):] if fm_match else content
	preserved: list[str] = []
	extracted: list[str] = []
	for sec in re.split('(?m)(?=^# )', body):
		stripped = sec.strip()
		if stripped:
			first_line = stripped.split('\n', 1)[0].lower()
			if any((h in first_line for h in _KEEP_HEADINGS)):
				preserved.append(sec)
			else:
				extracted.append(sec)
	return (preserved, extracted)
# @used-by :func:`_write_split_modules()`
def _used_rule_indices(rules_dir: Path) -> set[int]:
	used: set[int] = set()
	for f in rules_dir.glob('9[1-9]-*.md'):
		m = re.match('^9([1-9])-.*\\.md$', f.name)
		if m:
			used.add(int(m.group(1)))
	return used
# @used-by :func:`dfh_split_rules()`
def _write_split_modules(rules_dir: Path, extracted: list[str]) -> list[str]:
	used_indices = _used_rule_indices(rules_dir)
	next_idx = 1
	links: list[str] = []
	for sec in extracted:
		while next_idx in used_indices and 9 >= next_idx:
			next_idx += 1
		if 9 < next_idx:
			print('Warning: All indices 91-99 are used!')
			break
		title = sec.strip().split('\n')[0].lstrip('# ').strip()
		filename = f'9{next_idx}-{dfh_slugify(title)}.md'
		filepath = rules_dir / filename
		mod_content = f'---\ntrigger: model_decision\ndescription: "{title}"\n---\n\n{sec.strip()}\n'
		filepath.write_text(mod_content, encoding='utf-8')
		print(f"Created modular rule: {filepath.name} ({len(mod_content.encode('utf-8'))} bytes)")
		used_indices.add(next_idx)
		links.append(f'- **{title}** \u2014 [.agents/rules/{filename}](<file:///{filepath.as_posix()}>)')
		next_idx += 1
	return links
# @used-by :func:`dfh_split_rules()`
def _write_updated_project_map(map_file: Path, preserved: list[str], new_links: list[str]) -> None:
	map_body = '\n\n'.join((s.strip() for s in preserved if s.strip()))
	if new_links:
		map_body += '\n\n# Additional Rule Modules\n' + '\n'.join(new_links) + '\n'
	new_map = f'---\ntrigger: always_on\ndescription: "Project rules map"\n---\n\n{map_body.strip()}\n'
	map_file.write_text(new_map, encoding='utf-8')
	print(f"Updated 90-project.md: new size {len(new_map.encode('utf-8'))} bytes.")
# @used-by :func:`_write_split_modules()`
# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_cli_subsystem_classes()`
def dfh_slugify(title: str) -> str:
	slug = re.sub('[\\s_]+', '-', re.sub('[^a-z0-9\\u0430-\\u044f\\u0451\\s-]', '', title.lower())).strip('-')
	r = slug[:20] if slug else 'module'
	for k, v in _SLUG_TRANS.items():
		if k in slug:
			r = v
			break
	return r
# @used-by :func:`dfh_split_rules_main()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_rule_splitter_and_config_blocks_helpers()`
def dfh_split_rules(rules_dir: Path, max_bytes: int=4000, *, force: bool | None=None) -> bool:
	r = False
	map_file = rules_dir / '90-project.md'
	is_force = ('--force' in sys.argv) if None is force else bool(force)
	if map_file.exists():
		content = map_file.read_text(encoding='utf-8')
		if len(content.encode('utf-8')) <= max_bytes and (not is_force):
			print(f"90-project.md is within budget ({len(content.encode('utf-8'))} bytes <= {max_bytes}). No split needed.")
		else:
			preserved, extracted = _partition_rule_sections(content)
			if not extracted:
				print('No detachable sections found in 90-project.md.')
			else:
				_write_updated_project_map(map_file, preserved, _write_split_modules(rules_dir, extracted))
				r = True
	return r
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_rule_splitter_and_config_blocks_helpers()`
# @used-by :mod:`split_project_rules`
def dfh_split_rules_main(argv: list[str] | None=None) -> None:
	eff = sys.argv if None is argv else argv
	if 2 > len(eff):
		rules_dir = Path.cwd() / '.agents' / 'rules'
	else:
		target = Path(eff[1])
		rules_dir = target if 'rules' == target.name and '.agents' == target.parent.name else (target / '.agents' / 'rules')
	if not rules_dir.exists():
		print(f'Error: rules directory not found at {rules_dir}', file=sys.stderr)
		sys.exit(1)
	dfh_split_rules(rules_dir)