"""Native projections generated from one policy/workflow source; preserve manual edits."""

import hashlib
import json
from pathlib import Path
import re
import tomllib
from contextlib import nullcontext

from .runtime import PRIMARY, settings, role_settings, profile_name
from .storage import locked, replace_bytes


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _publish(root, outputs, *, check=False, merge=None, retire=()):
    root = Path(root).resolve()
    manifest = root / 'ꘖ/data/native-config.json'
    if not outputs and not any(Path(path).exists() for path in retire):
        return {'valid': True, 'issues': [], 'written': [], 'outputs': [], 'removed': []}
    with (nullcontext() if check else locked(root / 'ꘖ/data/native-config.lock')):
        receipt_bytes = manifest.read_bytes() if manifest.exists() else None
        previous = json.loads(receipt_bytes) if receipt_bytes is not None else {}
        issues, planned, removed, preimages = [], {}, [], {}
        for target, text in outputs.items():
            target = Path(target)
            if any(p.is_symlink() or p.is_junction() for p in (target, *target.parents) if p.exists()):
                issues.append({'file': str(target), 'message': 'Linked native configuration preserved'})
                continue
            payload = text.encode('utf-8')
            actual = target.read_bytes() if target.exists() else None
            key = str(target.resolve())
            if actual != payload:
                owned = previous.get(key)
                owned = owned.get('sha256') if isinstance(owned, dict) else owned
                if actual is not None and owned != _digest(actual) and (merge or {}).get(target) != actual:
                    issues.append({'file': key, 'message': 'Manual/unowned native configuration preserved'})
                elif check:
                    issues.append({'file': key, 'message': 'Native projection is missing or stale; run build-native'})
                else:
                    planned[target] = payload
                    preimages[target] = actual
        for target in retire:
            target = Path(target)
            if any(p.is_symlink() or p.is_junction() for p in (target, *target.parents) if p.exists()):
                issues.append({'file': str(target), 'message': 'Linked legacy file preserved'})
                continue
            target = target.resolve()
            if not target.is_relative_to(root):
                raise ValueError('Retirement must stay inside the configured root')
            if target.exists():
                if previous.get(str(target)) != _digest(target.read_bytes()):
                    issues.append({'file': str(target), 'message': 'Manual/unowned legacy file preserved'})
                elif check:
                    issues.append({'file': str(target), 'message': 'Owned legacy file needs migration'})
                else:
                    removed.append(target)
        if issues:
            return {'valid': False, 'issues': issues, 'written': []}
        if not check:
            for target, payload in planned.items():
                if (target.read_bytes() if target.exists() else None) != preimages[target]:
                    raise ValueError('Native configuration changed during publication; external edit preserved')
                replace_bytes(target, payload)
            previous.update({str(Path(p).resolve()): _digest(text.encode('utf-8')) for p, text in outputs.items()})
            for target in removed:
                # Native configuration is in place before retiring its old projection.
                if _digest(target.read_bytes()) != previous[str(target)]:
                    raise ValueError('Legacy file changed during migration')
                target.unlink()
                previous.pop(str(target), None)
            config = root / '.codex/config.toml'
            if config in outputs:
                if not outputs[config].strip():
                    if config.read_bytes() != outputs[config].encode('utf-8'):
                        raise ValueError('Empty projection changed during retirement; external edit preserved')
                    config.unlink()  # Only the exact empty, merged and read-back projection.
                    previous.pop(str(config), None)
                    try:
                        config.parent.rmdir()  # Empty directory only; custom roles/settings stay.
                    except OSError:
                        pass
                else:
                    value = tomllib.loads(outputs[config]).get('developer_instructions', '')
                    previous[str(config)] = {'sha256': _digest(outputs[config].encode()),
                                             'block_sha256': _digest(_managed_block(value).encode())}
            if (manifest.read_bytes() if manifest.exists() else None) != receipt_bytes:
                raise ValueError('Ownership receipt changed during publication; external edit preserved')
            if previous:
                replace_bytes(manifest, (json.dumps(previous, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
            elif manifest.exists():
                manifest.unlink()  # No remaining projections need an ownership receipt.
        return {'valid': True, 'issues': [], 'written': [str(p) for p in planned],
                'outputs': [str(p) for p in outputs], 'removed': [str(p) for p in removed]}


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


START = '<!-- upwork-init:instructions:start -->'
END = '<!-- upwork-init:instructions:end -->'


def _managed_block(value):
    if START not in value and END not in value:
        return ''
    if value.count(START) != 1 or value.count(END) != 1 or value.index(START) > value.index(END):
        raise ValueError('Malformed managed developer instructions; configuration preserved')
    return value[value.index(START):value.index(END) + len(END)]


def _root_options(text, instructions=None, *, legacy_bytes=None, expected_block=None):
    data = tomllib.loads(text) if text.strip() else {}
    value = data.get('developer_instructions', '')
    old_block = _managed_block(value)
    block = START + '\n' + instructions.strip() + '\n' + END if instructions else ''
    if old_block and old_block != block and _digest(old_block.encode()) != expected_block:
        raise ValueError('Managed developer instructions were manually edited; configuration preserved')
    value = value.replace(old_block, block) if old_block else value + ('\n\n' if value and block else '') + block
    values = {'developer_instructions': json.dumps(value, ensure_ascii=False) if value.strip() else None} if 'developer_instructions' in data or block else {}
    if legacy_bytes is not None:
        names = data.get('project_doc_fallback_filenames', [])
        if 'CODEX.md' in names:
            remaining = [name for name in names if name != 'CODEX.md']
            values['project_doc_fallback_filenames'] = json.dumps(remaining) if remaining else None
        if data.get('project_doc_max_bytes') in (65536, 65536 + legacy_bytes):
            values['project_doc_max_bytes'] = None
    edits, found = [], set()
    for start, end in _toml_statements(text):
        statement = text[start:end].lstrip()
        if statement.startswith('['):
            break
        for key, value in values.items():
            if re.match(r'^(?:' + key + '|"' + key + '"|\'' + key + r"')\s*=", statement):
                newline = '\r\n' if text[start:end].endswith('\r\n') else '\n'
                edits.append((start, end, '' if value is None else key + ' = ' + value + newline))
                found.add(key)
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    text = ''.join(key + ' = ' + value + '\n' for key, value in values.items() if key not in found and value is not None) + text
    tomllib.loads(text)
    return text


def _native_config(root, instructions=None):
    config_path = root / '.codex/config.toml'
    actual = config_path.read_bytes() if config_path.exists() else None
    existing = actual.decode('utf-8') if actual is not None else ''
    manifest = root / 'ꘖ/data/native-config.json'
    receipt = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
    owned = receipt.get(str(config_path), {})
    legacy = root / 'CODEX.md'
    legacy_bytes = None
    if legacy.exists() and receipt.get(str(legacy)) == _digest(legacy.read_bytes()):
        legacy_bytes = len(legacy.read_bytes())
    wanted = _root_options(existing, instructions, legacy_bytes=legacy_bytes,
                           expected_block=owned.get('block_sha256') if isinstance(owned, dict) else None)
    return config_path, wanted, {config_path: actual}


def _loader(primary, local=(), *, restore_global=True):
    paths = [*sorted((primary / 'rules').glob('*.md')), primary / 'platforms/codex.md', *local]
    lines = ['До выполнения задания прочитай перечисленные канонические источники правил.',
             'Общие правила always_on и адаптер Codex обязательны в каждом новом чате, включая дочерние.',
             'Для проектных источников соблюдай trigger из frontmatter; ссылки не являются копиями правил.']
    if restore_global:
        lines.append(f'Сначала выполни Python-инструмент "{(primary / "scripts/upwork_project.py").as_posix()}" policy-instructions --platform codex; примени возвращённые глобальные developer_instructions текущего профиля дополнительно к этим правилам. Команда читает только нужный TOML-ключ, не весь конфиг.')
    lines.extend(f'- {path.as_posix()}' for path in dict.fromkeys(paths))
    lines.extend(['Затем в точном корне проекта текущего чата прочитай локальные .agents/rules/*.md и .agents/rules.json.',
                  'Прочитай все дополнительные path-источники из rules.json, соблюдая trigger; общий каталог правил повторно читать не нужно.',
                  'Не выбирай соседний проект. Если корень текущей задачи неизвестен, определи его по явной привязке чата.',
                  f'Для установленного корня каждого хода выполни Python-инструмент "{(primary / "scripts/upwork_project.py").as_posix()}" turn-begin "<точный корень текущего чата>" --platform codex; UUID берётся из CODEX_THREAD_ID, профиль — из CODEX_HOME.',
                  'FILE-3 и EXEC-5 действуют также для обычного аналитического ответа и исследования .agents; профиль статьи/proposal не задаёт их область.',
                  'Основной агент перед окончательным ответом выполняет answer-prepare с точными UTF-8-байтами по references/turn-completion.md; дочерний агент не ведёт пользовательский журнал.'])
    return '\n'.join(lines)


def global_codex_instructions():
    """Preserve profile-specific global instructions shadowed by a native string key."""
    homes = settings()['platforms']['codex']['homes']
    try:
        name = profile_name()
        names = [name]
    except ValueError:
        names = list(homes)
    values = []
    for name in names:
        path = Path(homes[name]) / 'config.toml'
        value = tomllib.loads(path.read_bytes().decode('utf-8-sig')).get('developer_instructions', '') if path.exists() else ''
        if not isinstance(value, str):
            raise ValueError('Global developer_instructions must be a string')
        values.append(value)
    if len(set(values)) != 1:
        raise ValueError('Global profile instructions differ; select the actual --codex-profile instead of combining accounts')
    return {'developer_instructions': values[0], 'profile': names[0] if len(names) == 1 else 'identical across configured profiles'}


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
    try:
        native = root / '.codex/config.toml'
        data = tomllib.loads(native.read_bytes().decode('utf-8')) if native.exists() else {}
        current = data.get('developer_instructions', '')
        # An absent local key must keep inheriting all native parent instructions.
        # Only a pre-existing local override needs an explicit shared loader.
        manual = current.replace(_managed_block(current), '').strip()
        path, text, merge = _native_config(root, _loader(primary, paths, restore_global=False) if manual else None)
        result = _publish(root, {path: text} if text or path.exists() else {}, check=check, merge=merge, retire=[root / 'CODEX.md'])
    except ValueError as exc:
        if not check:
            raise
        return {'valid': False, 'issues': [{'file': str(root / '.codex/config.toml'), 'message': str(exc)}], 'written': []}
    if not check and not result['valid']:
        raise ValueError(result['issues'])
    return result


def _frontmatter(path):
    """Plain `key: value` pairs of a SKILL.md frontmatter (the shared skills use no nested YAML)."""
    text = path.read_text(encoding='utf-8-sig')
    match = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n', text, re.S)
    values = {}
    for line in (match.group(1).splitlines() if match else []):
        key, sep, value = line.partition(':')
        if sep and key.strip() and not key.startswith(' '):
            value = value.strip()
            values[key.strip()] = json.loads(value) if value.startswith('"') else value
    return values


def build_native(root=None, *, primary=PRIMARY, check=False):
    config = settings()
    root = Path(root or config['workspace_root']).resolve()
    primary = Path(primary).resolve()
    source_paths = [primary / 'runtime.json', *sorted((primary / 'rules').glob('*.md')),
                    primary / 'platforms/codex.md', primary / 'agents/worker.md',
                    *sorted((primary / 'skills').glob('*/SKILL.md'))]
    source_hash = _digest(b''.join(p.read_bytes() for p in source_paths))
    native = root / '.codex/config.toml'
    current = tomllib.loads(native.read_bytes().decode('utf-8')).get('developer_instructions', '') if native.exists() else ''
    old_block = _managed_block(current)
    restore_global = 'policy-instructions' in old_block if old_block else not bool(current.strip())
    instructions = _loader(primary, restore_global=restore_global)
    skill_source = primary / 'skills/upwork-init/SKILL.md'
    skill = ('---\nname: upwork-init\ndescription: Создаёт проект и выполняет полный анализ вакансии Upwork; продолжает его после прерывания.\n---\n'
             f'Прочитай и выполни общий навык [{skill_source.name}](<{skill_source.as_posix()}>).\n'
             'Определи текущую UI-среду по беседе и используй соответствующий платформенный адаптер общего навыка.\n')
    guidance = ('# Codex: Upwork\n\n'
                f'<!-- Generated from {primary.as_posix()}; run upwork_project.py build-native to update. -->\n\n'
                + instructions + '\n')
    outputs = {root / 'AGENTS.md': guidance,
               root / '.agents/skills/upwork-init/SKILL.md': skill}
    cleanup_source = primary / 'skills/upwork-cleanup/SKILL.md'
    if cleanup_source.is_file():
        outputs[root / '.agents/skills/upwork-cleanup/SKILL.md'] = (
            '---\nname: upwork-cleanup\ndescription: Очищает пустые проекты Upwork старше трёх суток в Antigravity и Codex, сохраняя историю на диске.\n---\n'
            f'Прочитай и выполни общий навык [{cleanup_source.name}](<{cleanup_source.as_posix()}>).\n'
            'Определи текущую UI-среду по беседе; обычный запуск выполняет очистку в обеих системах.\n')
    for other in sorted((primary / 'skills').glob('*/SKILL.md')):
        name = other.parent.name
        if name in ('upwork-init', 'upwork-cleanup'):
            continue
        description = _frontmatter(other).get('description', '')
        if not description:
            return {'valid': False, 'issues': [{'file': str(other), 'message': 'Shared skill needs a frontmatter description'}], 'written': []}
        description = json.dumps(description, ensure_ascii=False) if re.search(r':\s|\s#|^[\'"\[{>|*&!%@`]', description) else description
        outputs[root / f'.agents/skills/{name}/SKILL.md'] = (
            f'---\nname: {name}\ndescription: {description}\n---\n'
            f'Прочитай и выполни общий навык [{other.name}](<{other.as_posix()}>).\n')
    for role in ('AA', 'AF'):
        value = role_settings('codex', role)
        name = value['agent']
        purpose = 'Независимая предметная проверка пяти этапов и согласованности KB.' if role == 'AA' else 'Сбор и извлечение доказательств по назначенному вопросу.'
        instructions_role = (f'Роль: {role}. {purpose}\n' + instructions +
                             f'\nПрочитай также протокол исполнителя: {(primary / "agents/worker.md").as_posix()}')
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
        f'model: {flash["tier"]}\nsubagent: true\nmainAgent: false\n---\n'
        f'Прочитай общий протокол исполнителя: {(primary / "agents/worker.md").as_posix()}\n'
        'Среда: Antigravity. Следуй платформенному протоколу и runtime.json; tier не доказывает точную модель.\n')
    try:
        path, text, merge = _native_config(root, instructions)
        outputs[path] = text
        result = _publish(root, outputs, check=check, merge=merge, retire=[root / 'CODEX.md'])
    except ValueError as exc:
        return {'valid': False, 'issues': [{'file': str(root / '.codex/config.toml'), 'message': str(exc)}], 'written': []}
    result.update(source_sha256=source_hash, policy_bytes=len(instructions.encode('utf-8')),
                  canonical_runtime=str(primary / 'runtime.json'))
    return result
