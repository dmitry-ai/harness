# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from importlib import import_module
# 2026-11-18
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
from ..runtime import platform_adapter_name, platform_name, settings
# 2026-10-15
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def adapter(platform=None, surface=None):
	# 2026-11-18
	# "Externalize agent environments and per-instance system paths into runtime.json":
	# https://github.com/dmitry-ai/harness/issues/86
	cfg = settings()
	if surface:
		matches = [name for name, value in cfg['platforms'].items() if value.get('surface') == surface]
		if 1 != len(matches):
			raise ValueError('Unsupported native evidence surface')
		platform = matches[0]
	# 2026-11-18
	# "Externalize agent environments and per-instance system paths into runtime.json":
	# https://github.com/dmitry-ai/harness/issues/86
	plat = platform_name(platform)
	mod_name = platform_adapter_name(plat, config=cfg)
	try:
		r = import_module('.' + mod_name, __name__)
	except ModuleNotFoundError as exc:
		raise ValueError(f'No native adapter implemented for platform {plat!r} (adapter {mod_name!r})') from exc
	return r
