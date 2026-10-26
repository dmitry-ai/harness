#!/usr/bin/env python3
"""Auto-split project rules in .agents/rules/ into modular files when 90-project.md grows."""

import os
from pathlib import Path
import re
import sys


def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9а-яё\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug).strip('-')
    # Транслитерация базовых слов для удобства
    trans = {
        'сервер': 'servers',
        'доступ': 'access',
        'git': 'git-workflow',
        'правк': 'workflow',
        'деплой': 'deploy',
        'разверт': 'deploy',
        'кроссплатформ': 'crossplatform',
        'универсальн': 'crossplatform',
    }
    for k, v in trans.items():
        if k in slug:
            return v
    return slug[:20] if slug else 'module'


def split_rules(rules_dir: Path, max_bytes: int = 4000) -> bool:
    map_file = rules_dir / "90-project.md"
    if not map_file.exists():
        return False

    content = map_file.read_text(encoding="utf-8")
    if len(content.encode("utf-8")) <= max_bytes and "--force" not in sys.argv:
        print(f"90-project.md is within budget ({len(content.encode('utf-8'))} bytes <= {max_bytes}). No split needed.")
        return False

    # Extract frontmatter
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    fm = fm_match.group(0) if fm_match else ""
    body = content[len(fm):] if fm_match else content

    # Split by level 1 headers: # Header
    sections = re.split(r'(?m)(?=^# )', body)
    preserved_sections = []
    extracted_sections = []

    # Headings to keep in the map
    keep_headings = ("паспорт", "карта", "запрет бэкапов", "авторазбиение")

    for sec in sections:
        stripped = sec.strip()
        if not stripped:
            continue
        first_line = stripped.split("\n", 1)[0].lower()
        if any(h in first_line for h in keep_headings):
            preserved_sections.append(sec)
        else:
            extracted_sections.append(sec)

    if not extracted_sections:
        print("No detachable sections found in 90-project.md.")
        return False

    # Find existing 9X files to determine next index
    existing_files = list(rules_dir.glob("9[1-9]-*.md"))
    used_indices = set()
    for f in existing_files:
        m = re.match(r'^9([1-9])-.*\.md$', f.name)
        if m:
            used_indices.add(int(m.group(1)))

    next_idx = 1
    new_map_links = []

    for sec in extracted_sections:
        while next_idx in used_indices and next_idx <= 9:
            next_idx += 1
        if next_idx > 9:
            print("Warning: All indices 91-99 are used!")
            break

        lines = sec.strip().split("\n")
        title = lines[0].lstrip("# ").strip()
        slug = slugify(title)
        filename = f"9{next_idx}-{slug}.md"
        filepath = rules_dir / filename

        mod_content = f"""---
trigger: model_decision
description: "{title}"
---

{sec.strip()}
"""
        filepath.write_text(mod_content, encoding="utf-8")
        print(f"Created modular rule: {filepath.name} ({len(mod_content.encode('utf-8'))} bytes)")
        used_indices.add(next_idx)

        new_map_links.append(f"- **{title}** — [.agents/rules/{filename}](<file:///{filepath.as_posix()}>)")
        next_idx += 1

    # Reconstruct 90-project.md
    map_body = "\n\n".join(s.strip() for s in preserved_sections if s.strip())
    if new_map_links:
        map_body += "\n\n# Дополнительные модули правил\n" + "\n".join(new_map_links) + "\n"

    new_map_content = f"""---
trigger: always_on
description: "Карта проектных правил"
---

{map_body.strip()}
"""
    map_file.write_text(new_map_content, encoding="utf-8")
    print(f"Updated 90-project.md: new size {len(new_map_content.encode('utf-8'))} bytes.")
    return True


def main():
    if len(sys.argv) < 2:
        cwd = Path.cwd()
        rules_dir = cwd / ".agents" / "rules"
    else:
        target = Path(sys.argv[1])
        if (target / ".agents" / "rules").exists():
            rules_dir = target / ".agents" / "rules"
        elif target.name == "rules" and target.parent.name == ".agents":
            rules_dir = target
        else:
            rules_dir = target / ".agents" / "rules"

    if not rules_dir.exists():
        print(f"Error: rules directory not found at {rules_dir}", file=sys.stderr)
        sys.exit(1)

    split_rules(rules_dir)


if __name__ == "__main__":
    main()
