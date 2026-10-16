"""Native projections generated from one policy/workflow source; preserve manual edits."""

import hashlib
import json
from pathlib import Path
import re
import tomllib
from contextlib import nullcontext

from .runtime import PRIMARY, settings, role_settings
from .storage import locked, replace_bytes


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _publish(root, outputs, *, check=False):
    root = Path(root).resolve()
    manifest = root / 'ꘖ/data/native-config.json'
    with (nullcontext() if check else locked(root / 'ꘖ/data/native-config.lock')):
        previous = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
        issues, planned = [], {}
        for target, text in outputs.items():
            target = Path(target)
            payload = text.encode('utf-8')
            actual = target.read_bytes() if target.exists() else None
            key = str(target.resolve())
            if actual != payload:
                if actual is not None and previous.get(key) != _digest(actual):
                    issues.append({'file': key, 'message': 'Manual/unowned native configuration preserved'})
                elif check:
                    issues.append({'file': key, 'message': 'Native projection is missing or stale; run build-native'})
                else:
                    planned[target] = payload
        if issues:
            return {'valid': False, 'issues': issues, 'written': []}
        if not check:
            for target, payload in planned.items():
                replace_bytes(target, payload)
            previous.update({str(Path(p).resolve()): _digest(text.encode('utf-8')) for p, text in outputs.items()})
            replace_bytes(manifest, (json.dumps(previous, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        return {'valid': True, 'issues': [], 'written': [str(p) for p in planned],
                'outputs': [str(p) for p in outputs]}


def _toml_statements(text):
    """Yield logical statements without splitting arrays, comments or strings."""
    start = index = depth = 0
    quote, comment = None, False
    while index < len(text):
        char = text[index]
        if comment:
            if char == '\n':
                comment = False
            else:
                index += 1
                continue
        elif quote:
            if quote.startswith('"') and char == '\\':
                index += 2
                continue
            if text.startswith(quote, index):
                index += len(quote)
                if len(quote) == 3:
                    # TOML permits one or two literal quotes before the closing triple.
                    while index < len(text) and text[index] == quote[0]:
                        index += 1
                quote = None
                continue
            index += 1
            continue
        elif char in "\"'":
            quote = char * 3 if text.startswith(char * 3, index) else char
            index += len(quote)
            continue
        elif char == '#':
            comment = True
        elif char in '[{':
            depth += 1
        elif char in ']}':
            depth -= 1
        if char == '\n' and depth == 0:
            yield start, index + 1
            start = index + 1
        index += 1
    if start < len(text):
        yield start, len(text)


def _root_options(text, minimum=65536):
    data = tomllib.loads(text) if text.strip() else {}
    names = list(data.get('project_doc_fallback_filenames', []))
    if 'CODEX.md' not in names:
        names.append('CODEX.md')
    values = {'project_doc_fallback_filenames': json.dumps(names, ensure_ascii=False),
              'project_doc_max_bytes': str(max(minimum, data.get('project_doc_max_bytes', 0)))}
    edits, found = [], set()
    for start, end in _toml_statements(text):
        statement = text[start:end].lstrip()
        if statement.startswith('['):
            break
        for key, value in values.items():
            if re.match(r'^(?:' + key + '|"' + key + '"|\'' + key + r"')\s*=", statement):
                newline = '\r\n' if text[start:end].endswith('\r\n') else '\n'
                edits.append((start, end, key + ' = ' + value + newline))
                found.add(key)
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    text = ''.join(key + ' = ' + value + '\n' for key, value in values.items() if key not in found) + text
    tomllib.loads(text)
    return text


def _rule_body(path):
    body = re.sub(r'\A---\r?\n[\s\S]*?\r?\n---\r?\n', '', path.read_text(encoding='utf-8'))
    def link(match):
        label, target = match.groups()
        if target.startswith('<') and target.endswith('>'):
            target = target[1:-1]
        if re.match(r'^[a-z]+:|^#|^/', target, re.I):
            return match.group(0)
        file, sep, fragment = target.partition('#')
        return f'[{label}](<{(path.parent / file).resolve().as_posix()}{sep}{fragment}>)'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, body).strip()


def _discovery_config(root, result, *, check=False, minimum=65536):
    config_path = root / '.codex/config.toml'
    existing = config_path.read_text(encoding='utf-8') if config_path.exists() else ''
    wanted = _root_options(existing, minimum)
    if check and existing != wanted:
        result['valid'] = False
        result['issues'].append({'file': str(config_path), 'message': 'CODEX.md discovery is not configured'})
    elif not check and result['valid'] and existing != wanted:
        replace_bytes(config_path, wanted.encode('utf-8'))
        result['written'].append(str(config_path))
    return result


def _project_rule_paths(root, primary):
    """Resolve path-only AG registrations; fail visibly on unsupported selectors."""
    agents = root / '.agents'
    paths = list(sorted((agents / 'rules').glob('*.md')))
    manifest = agents / 'rules.json'
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding='utf-8-sig'))
        if not isinstance(data, dict) or not isinstance(data.get('entries', []), list):
            raise ValueError('rules.json needs an entries list')
        if data.get('inherits'):
            raise ValueError('Codex projection does not support rules.json inherits; preserve it and resolve explicitly')
        for entry in data.get('entries', []):
            if not isinstance(entry, dict) or not isinstance(entry.get('path'), str):
                raise ValueError('Each rules.json entry needs a path')
            if set(entry) - {'path'}:
                raise ValueError('Codex projection does not support filtered rules.json entries; preserve them and resolve explicitly')
            source = (agents / Path(entry['path']).expanduser()).resolve()
            if source == (primary / 'rules').resolve():
                continue  # The shared policy has its own native projection.
            if source.is_dir():
                paths.extend(sorted(source.rglob('*.md')))
            elif source.is_file() and source.suffix == '.md':
                paths.append(source)
            else:
                raise ValueError(f'Configured rule source is missing or unsupported: {source}')
    shared = (primary / 'rules').resolve()
    return list(dict.fromkeys(path.resolve() for path in paths if not path.resolve().is_relative_to(shared)))


def configure_codex_project(root, primary=PRIMARY, job_url=None, label=None, *, check=False):
    root, primary = Path(root).resolve(), Path(primary).resolve()
    if root == Path(settings()['workspace_root']).resolve():
        return {'valid': True, 'issues': [], 'written': []}
    try:
        paths = _project_rule_paths(root, primary)
    except (ValueError, OSError) as exc:
        if not check:
            raise
        return {'valid': False, 'issues': [{'file': str(root / '.agents/rules.json'), 'message': str(exc)}], 'written': []}
    fingerprint = _digest(b''.join(str(path).encode('utf-8') + b'\0' + path.read_bytes() for path in paths))
    body = f'<!-- Generated from project .agents rule sources; source {fingerprint}; edit those rules. -->\n\n'
    body += '# Правила проекта Upwork\n\n'
    shared = Path(settings()['workspace_root']) / 'CODEX.md'
    body += f'Общий регламент: [CODEX.md](<{shared.as_posix()}>).\n'
    body += 'Если полный текст общего регламента ещё не загружен нативно, прочитай его до работы.\n'
    body += f'Общий навык: [upwork-init](<{(primary / "skills/upwork-init/SKILL.md").as_posix()}>).\n'
    body += 'Правила ниже получены из проектной .agents/rules и подключений rules.json; пользовательская KB, рабочие proposal и точный журнал общие для обеих систем.\n\n'
    for path in paths:
        trigger = re.search(r'^trigger:\s*(\S+)', path.read_text(encoding='utf-8'), re.M)
        if trigger and trigger[1] != 'always_on':
            body += f'Условное правило ({trigger[1]}): [{path.name}](<{path.as_posix()}>); прочитай при применимости.\n\n'
        else:
            body += _rule_body(path) + '\n\n'
    body = body.rstrip() + '\n'
    result = _publish(root, {root / 'CODEX.md': body}, check=check)
    _discovery_config(root, result, check=check, minimum=65536 + len(body.encode('utf-8')))
    if not check and not result['valid']:
        raise ValueError(result['issues'])
    return result


def build_native(root=None, *, primary=PRIMARY, check=False):
    config = settings()
    root = Path(root or config['workspace_root']).resolve()
    primary = Path(primary).resolve()
    pieces = []
    for path in sorted((primary / 'rules').glob('*.md')):
        pieces.append(_rule_body(path))
    driver = (primary / 'platforms/codex.md').read_text(encoding='utf-8')
    source_paths = [primary / 'runtime.json', *sorted((primary / 'rules').glob('*.md')),
                    primary / 'platforms/codex.md', primary / 'agents/worker.md',
                    primary / 'skills/upwork-init/SKILL.md']
    source_hash = _digest(b''.join(p.read_bytes() for p in source_paths))
    header = f'<!-- Generated by upwork_project.py build-native; source {source_hash}; edit canonical sources. -->\n\n'
    instructions = header + '\n\n'.join(pieces) + '\n\n' + driver
    if len(instructions.encode('utf-8')) > 65536:
        raise ValueError('Codex policy projection exceeds the configured native instruction budget')
    skill_source = primary / 'skills/upwork-init/SKILL.md'
    skill = ('---\nname: upwork-init\ndescription: Создаёт проект и выполняет полный анализ вакансии Upwork; продолжает его после прерывания.\n---\n'
             f'Прочитай и выполни общий навык [{skill_source.name}](<{skill_source.as_posix()}>).\n'
             'Определи текущую UI-среду по беседе и используй соответствующий платформенный адаптер общего навыка.\n')
    outputs = {root / 'CODEX.md': instructions,
               root / '.agents/skills/upwork-init/SKILL.md': skill}
    worker = (primary / 'agents/worker.md').read_text(encoding='utf-8')
    for role in ('AA', 'AF'):
        value = role_settings('codex', role)
        name = value['agent']
        purpose = 'Независимая предметная проверка пяти этапов и согласованности KB.' if role == 'AA' else 'Сбор и извлечение доказательств по назначенному вопросу.'
        instructions_role = f'Роль: {role}. {purpose}\n{worker}\n{driver}'
        model_fields = '' if config['platforms']['codex'].get('subagents', {}).get('selection') == 'parent' else (
            f'model = {json.dumps(value["model"])}\nmodel_reasoning_effort = {json.dumps(value["effort"])}\n')
        outputs[root / f'.codex/agents/{name}.toml'] = (
            '# Generated from runtime.json and agents/worker.md; do not edit.\n'
            f'name = {json.dumps(name)}\ndescription = {json.dumps(purpose, ensure_ascii=False)}\n'
            + model_fields +
            f'developer_instructions = {json.dumps(instructions_role, ensure_ascii=False)}\n')
    # Shared worker text is also projected into the existing Antigravity discovery path.
    flash = role_settings('antigravity', 'AF')
    outputs[primary / 'agents/af-worker.md'] = ('---\nname: af-worker\ndescription: "Извлекает и проверяет доказательства Upwork по назначенному вопросу."\n'
        f'model: {flash["tier"]}\nsubagent: true\nmainAgent: false\n---\n{worker}\n'
        'Среда: Antigravity. Следуй платформенному протоколу и runtime.json; tier не доказывает точную модель.\n')
    result = _publish(root, outputs, check=check)
    _discovery_config(root, result, check=check)
    result.update(source_sha256=source_hash, policy_bytes=len(instructions.encode('utf-8')),
                  canonical_runtime=str(primary / 'runtime.json'))
    return result
