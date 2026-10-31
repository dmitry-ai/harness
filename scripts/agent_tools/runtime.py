# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import json
import os
from pathlib import Path
PRIMARY = Path(__file__).resolve().parents[2]
HARNESS_ROOT = PRIMARY.parent if (PRIMARY.parent / '_').is_dir() else PRIMARY.parent.parent
HARNESS_META = HARNESS_ROOT / '_' if (HARNESS_ROOT / '_').is_dir() else HARNESS_ROOT
LEGACY_PRIMARY = Path('C:/work/upwork/code/AI/primary') / 'result/.agents'
os.environ.setdefault('GIT_OPTIONAL_LOCKS', '0')
_SHIM_DIR = str((PRIMARY / 'scripts/shim').resolve())
if _SHIM_DIR not in os.environ.get('PATH', '').split(os.pathsep):
	os.environ['PATH'] = _SHIM_DIR + os.pathsep + os.environ.get('PATH', '')
_platform = ContextVar('upwork_platform', default=None)
_profile = ContextVar('upwork_profile', default=None)
def settings(path=None):
	value = json.loads(Path(path or PRIMARY / 'runtime.json').read_text(encoding='utf-8-sig'))
	if 2 != value.get('version') or not value.get('workspace_root') or (not value.get('platforms')):
		raise ValueError('runtime.json needs version 2, workspace_root and platforms')
	r = value
	return r
def platform_name(value=None):
	name = value or _platform.get() or os.environ.get('UPWORK_PLATFORM') or 'antigravity'
	if name not in settings()['platforms']:
		raise ValueError(f'Unknown Upwork platform: {name}')
	r = name
	return r
def profile_name(value=None):
	if value or _profile.get() or os.environ.get('UPWORK_CODEX_PROFILE'):
		r = value or _profile.get() or os.environ['UPWORK_CODEX_PROFILE']
	else:
		current = os.environ.get('CODEX_HOME')
		matches = [name for name, home in settings()['platforms']['codex']['homes'].items() if current and Path(home).resolve() == Path(current).resolve()]
		if 1 != len(matches):
			raise ValueError('Select --codex-profile C1/C2 or use a recognized CODEX_HOME')
		r = matches[0]
	return r
def registration_profile_name(value=None):
	config = settings()['platforms']['codex']
	if value or _profile.get() or os.environ.get('UPWORK_CODEX_PROFILE') or os.environ.get('CODEX_HOME'):
		name = profile_name(value)
	else:
		name = config.get('registration_profile')
		if not name:
			raise ValueError('Select a Codex registration profile or configure registration_profile')
	if name not in config['homes']:
		raise ValueError(f'Unknown Codex registration profile: {name}')
	r = name
	return r
def platform_settings(name=None):
	return deepcopy(settings()['platforms'][platform_name(name)])
def role_settings(platform, role, seen=()):
	if role in seen:
		raise ValueError('Cyclic model role inheritance')
	value = platform_settings(platform)['roles'][role]
	fallback = value.get('inherit') or value.get('fallback')
	if fallback:
		r = {**role_settings(platform, fallback, (*seen, role)), **{k: v for k, v in value.items() if 'inherit' != k}}
	else:
		if value.get('selection') not in ('parent', 'inherit') and (not value.get('model') or not value.get('effort')):
			raise ValueError(f'Missing model/effort for {platform}/{role}')
		r = value
	return r
@contextmanager
def using(platform=None, profile=None):
	first, second = (_platform.set(platform_name(platform)), _profile.set(profile))
	try:
		yield
	finally:
		_platform.reset(first)
		_profile.reset(second)
def request_day(value=None):
	from datetime import date, datetime
	from zoneinfo import ZoneInfo
	r = date.fromisoformat(value) if value else datetime.now(ZoneInfo(settings()['timezone'])).date()
	return r
