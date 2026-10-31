# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from importlib import import_module
from ..runtime import platform_name, settings
def adapter(platform=None, surface=None):
	if surface:
		matches = [name for name, value in settings()['platforms'].items() if value['surface'] == surface]
		if 1 != len(matches):
			raise ValueError('Unsupported native evidence surface')
		platform = matches[0]
	r = import_module('.' + platform_name(platform), __name__)
	return r
