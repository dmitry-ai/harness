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
# @used-by :func:`agent_tools.completion._completion_ops()`
# @used-by :func:`agent_tools.doc5_replay_audit._load_saved_turn_entry()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.native_executor_metadata()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.native_requests()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.native_review_proof()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.native_tool_trace()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.verify_native_proof()`
# @used-by :meth:`Df.Harness.Project.Registry.Registry.__attempt()`
# @used-by :meth:`Df.Harness.Review.DispositionRecorder.DispositionRecorder.record()`
# @used-by :meth:`Df.Harness.Review.ReportAuthenticator.ReportAuthenticator.__auth_self()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_future_environment_claude_code_is_supported_without_roles_or_adapters()`
# @uses :mod:`agent_tools.platforms.antigravity`
# @uses :mod:`agent_tools.platforms.codex`
# @uses :func:`agent_tools.platforms.codex.verify_native_proof()`
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
