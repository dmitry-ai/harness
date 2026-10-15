"""One editable runtime configuration; no model IDs in executable code."""

from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import json
import os
from pathlib import Path

PRIMARY = Path(__file__).resolve().parents[2]
_platform = ContextVar('upwork_platform', default=None)
_profile = ContextVar('upwork_profile', default=None)


def settings(path=None):
    value = json.loads(Path(path or PRIMARY / 'runtime.json').read_text(encoding='utf-8-sig'))
    if value.get('version') != 2 or not value.get('workspace_root') or not value.get('platforms'):
        raise ValueError('runtime.json needs version 2, workspace_root and platforms')
    return value


def platform_name(value=None):
    name = value or _platform.get() or os.environ.get('UPWORK_PLATFORM') or 'antigravity'
    if name not in settings()['platforms']:
        raise ValueError(f'Unknown Upwork platform: {name}')
    return name


def profile_name(value=None):
    if value or _profile.get() or os.environ.get('UPWORK_CODEX_PROFILE'):
        return value or _profile.get() or os.environ['UPWORK_CODEX_PROFILE']
    current = os.environ.get('CODEX_HOME')
    matches = [name for name, home in settings()['platforms']['codex']['homes'].items()
               if current and Path(home).resolve() == Path(current).resolve()]
    if len(matches) != 1:
        raise ValueError('Select --codex-profile C1/C2 or use a recognized CODEX_HOME')
    return matches[0]


def platform_settings(name=None):
    return deepcopy(settings()['platforms'][platform_name(name)])


def role_settings(platform, role, seen=()):
    if role in seen:
        raise ValueError('Cyclic model role inheritance')
    value = platform_settings(platform)['roles'][role]
    fallback = value.get('inherit') or value.get('fallback')
    if fallback:
        return {**role_settings(platform, fallback, (*seen, role)),
                **{k: v for k, v in value.items() if k != 'inherit'}}
    if value.get('selection') not in ('parent', 'inherit') and (not value.get('model') or not value.get('effort')):
        raise ValueError(f'Missing model/effort for {platform}/{role}')
    return value


@contextmanager
def using(platform=None, profile=None):
    first, second = _platform.set(platform_name(platform)), _profile.set(profile)
    try:
        yield
    finally:
        _platform.reset(first)
        _profile.reset(second)


def request_day(value=None):
    from datetime import date, datetime
    from zoneinfo import ZoneInfo
    return date.fromisoformat(value) if value else datetime.now(ZoneInfo(settings()['timezone'])).date()
