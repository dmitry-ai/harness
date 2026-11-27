# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.ag_inputs import ANTIGRAVITY_MODEL_TIERS, dfh_antigravity_paths
from Df.Harness.lib.ag_metadata import dfh_apply_requested_config, dfh_model_metadata, dfh_native_invocation
from Df.Harness.lib.ag_wire import dfh_configuration, dfh_generation_matches_executor
from Df.Harness.lib.trace_review import dfh_finalize_executor_checks
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ExecutorMetadataReader:
	# @used-by :func:`agent_tools.platforms.antigravity.native_executor_metadata()`
	# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.__build_extra_fields()`
	def __init__(self, root, conversation_id: str, *, role: str='primary', parent_id: str | None=None, backend=None, instance=None, _ops: dict[str, Any] | None=None) -> None:
		self.__root = root
		self.__conversation_id = conversation_id
		self.__role = role
		self.__parent_id = parent_id
		self.__backend = backend
		self.__instance = instance
		self.__ops = _ops or {}
	# @used-by :meth:`ExecutorMetadataReader.run()`
	def __resolve_child_requested(self, backend: Path, paths: dict, observed: dict, requested: dict) -> None:
		if not self.__parent_id or self.__parent_id == self.__conversation_id:
			raise ValueError('Exact parent required for AA/AF metadata')
		invocation, source = dfh_native_invocation(backend, self.__parent_id, self.__conversation_id, self.__role, paths=paths, platform_settings_fn=self.__ops.get('platform_settings'), settings_fn=self.__ops.get('settings'))
		raw_model = invocation.get('Model')
		selection = raw_model.strip() if isinstance(raw_model, str) and raw_model.strip() else 'inherit'
		if 'inherit' == selection.lower():
			parent_obs, parent_hist, _ = dfh_model_metadata(backend, self.__parent_id, paths=paths)
			if 1 == len({item['value'] for item in parent_hist['generations']}):
				requested['model'], requested['generation_model'] = (parent_obs['model'], parent_obs['generation_model'])
			if 1 == len({item['value'] for item in parent_hist['configurations']}):
				requested['effort'], requested['executor_model'] = (parent_obs['effort'], parent_obs['executor_model'])
			requested.update(selection='inherit', source=source)
		elif selection.lower() in ANTIGRAVITY_MODEL_TIERS:
			requested.update(tier=selection.lower(), selection='explicit-parent-invocation', source=source)
		else:
			dfh_apply_requested_config(requested, observed, selection, 'explicit-parent-invocation', source)
	# @used-by :func:`agent_tools.platforms.antigravity.native_executor_metadata()`
	# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.__build_extra_fields()`
	def run(self) -> dict[str, Any]:
		if self.__role not in ('primary', 'AA', 'AF', 'ARCH'):
			raise ValueError('Unknown executor role')
		paths = dfh_antigravity_paths(backend=self.__backend, instance=self.__instance, conversation_id=self.__conversation_id, settings_fn=self.__ops.get('settings'))
		backend = Path(paths['backend_dir'])
		observed, history, sources = dfh_model_metadata(backend, self.__conversation_id, paths=paths)
		requested: dict[str, Any] = {'model': None, 'generation_model': None, 'executor_model': None, 'effort': None, 'selection': 'unavailable', 'source': None}
		if 'primary' == self.__role and observed['configuration']:
			dfh_apply_requested_config(requested, observed, observed['configuration'], 'native-executor-configuration', next((item for item in reversed(sources) if 'executor_metadata' == item.get('table')), None))
		elif 'primary' != self.__role:
			self.__resolve_child_requested(backend, paths, observed, requested)
		force_mismatch = ('inherit' == requested.get('selection') and bool(requested.get('executor_model') and observed.get('executor_model') and requested['executor_model'] != observed['executor_model'])) or bool(observed['configuration'] and observed['model'] and (not dfh_generation_matches_executor(observed['model'], dfh_configuration(observed['configuration'])['model'])))
		return dfh_finalize_executor_checks('antigravity-ui', self.__role, self.__conversation_id, self.__parent_id, requested, observed, history, sources, 'Native generation model and executor configuration fields; exact API execution internals and missing modes are not inferred from runtime', force_model_mismatch=force_mismatch)
