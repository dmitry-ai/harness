# 2026-10-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from pathlib import Path
import re
import sys
def slugify(title: str) -> str:
	slug = title.lower()
	slug = re.sub('[^a-z0-9\\u0430-\\u044f\\u0451\\s-]', '', slug)
	slug = re.sub('[\\s_]+', '-', slug).strip('-')
	trans = {'\u0441\u0435\u0440\u0432\u0435\u0440': 'servers', '\u0434\u043e\u0441\u0442\u0443\u043f': 'access', 'git': 'git-workflow', '\u043f\u0440\u0430\u0432\u043a': 'workflow', '\u0434\u0435\u043f\u043b\u043e\u0439': 'deploy', '\u0440\u0430\u0437\u0432\u0435\u0440\u0442': 'deploy', '\u043a\u0440\u043e\u0441\u0441\u043f\u043b\u0430\u0442\u0444\u043e\u0440\u043c': 'crossplatform', '\u0443\u043d\u0438\u0432\u0435\u0440\u0441\u0430\u043b\u044c\u043d': 'crossplatform'}
	r = slug[:20] if slug else 'module'
	for k, v in trans.items():
		if k in slug:
			r = v
			break
	return r
def split_rules(rules_dir: Path, max_bytes: int=4000) -> bool:
	r = False
	map_file = rules_dir / '90-project.md'
	if map_file.exists():
		content = map_file.read_text(encoding='utf-8')
		if len(content.encode('utf-8')) <= max_bytes and '--force' not in sys.argv:
			print(f"90-project.md is within budget ({len(content.encode('utf-8'))} bytes <= {max_bytes}). No split needed.")
		else:
			fm_match = re.match('^---\\s*\\n(.*?)\\n---\\s*\\n', content, re.DOTALL)
			fm = fm_match.group(0) if fm_match else ''
			body = content[len(fm):] if fm_match else content
			sections = re.split('(?m)(?=^# )', body)
			preserved_sections = []
			extracted_sections = []
			keep_headings = ('passport', 'map', 'no backups', 'autosplit', 'project', '\u043f\u0430\u0441\u043f\u043e\u0440\u0442', '\u043a\u0430\u0440\u0442\u0430', '\u0437\u0430\u043f\u0440\u0435\u0442 \u0431\u044d\u043a\u0430\u043f\u043e\u0432', '\u0430\u0432\u0442\u043e\u0440\u0430\u0437\u0431\u0438\u0435\u043d\u0438\u0435')
			for sec in sections:
				stripped = sec.strip()
				if stripped:
					first_line = stripped.split('\n', 1)[0].lower()
					if any((h in first_line for h in keep_headings)):
						preserved_sections.append(sec)
					else:
						extracted_sections.append(sec)
			if not extracted_sections:
				print('No detachable sections found in 90-project.md.')
			else:
				existing_files = list(rules_dir.glob('9[1-9]-*.md'))
				used_indices = set()
				for f in existing_files:
					m = re.match('^9([1-9])-.*\\.md$', f.name)
					if m:
						used_indices.add(int(m.group(1)))
				next_idx = 1
				new_map_links = []
				for sec in extracted_sections:
					while next_idx in used_indices and next_idx <= 9:
						next_idx += 1
					if next_idx > 9:
						print('Warning: All indices 91-99 are used!')
						break
					lines = sec.strip().split('\n')
					title = lines[0].lstrip('# ').strip()
					slug = slugify(title)
					filename = f'9{next_idx}-{slug}.md'
					filepath = rules_dir / filename
					mod_content = f'---\ntrigger: model_decision\ndescription: "{title}"\n---\n\n{sec.strip()}\n'
					filepath.write_text(mod_content, encoding='utf-8')
					print(f"Created modular rule: {filepath.name} ({len(mod_content.encode('utf-8'))} bytes)")
					used_indices.add(next_idx)
					new_map_links.append(f'- **{title}** — [.agents/rules/{filename}](<file:///{filepath.as_posix()}>)')
					next_idx += 1
				map_body = '\n\n'.join((s.strip() for s in preserved_sections if s.strip()))
				if new_map_links:
					map_body += '\n\n# Additional Rule Modules\n' + '\n'.join(new_map_links) + '\n'
				new_map_content = f'---\ntrigger: always_on\ndescription: "Project rules map"\n---\n\n{map_body.strip()}\n'
				map_file.write_text(new_map_content, encoding='utf-8')
				print(f"Updated 90-project.md: new size {len(new_map_content.encode('utf-8'))} bytes.")
				r = True
	return r
def main():
	if len(sys.argv) < 2:
		rules_dir = Path.cwd() / '.agents' / 'rules'
	else:
		target = Path(sys.argv[1])
		if 'rules' == target.name and '.agents' == target.parent.name:
			rules_dir = target
		else:
			rules_dir = target / '.agents' / 'rules'
	if not rules_dir.exists():
		print(f'Error: rules directory not found at {rules_dir}', file=sys.stderr)
		sys.exit(1)
	split_rules(rules_dir)
if '__main__' == __name__:
	main()
