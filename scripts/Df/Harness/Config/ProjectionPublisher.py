# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import nullcontext
from pathlib import Path
from typing import Any
from Df.Harness.lib.config_blocks import dfh_digest, dfh_extract_managed_block, dfh_has_linked_ancestor, dfh_load_project_receipt, dfh_receipt_sha256, dfh_store_content_backup
from Df.Harness.lib.path_resolve import dfh_project_paths
from Df.Harness.lib.storage import dfh_data_dir_for, dfh_locked, dfh_replace_bytes
import json
import tomllib
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ProjectionPublisher:
	# @used-by :func:`Df.Harness.lib.config_codex._run_codex_project_publish()`
	# @used-by :func:`agent_tools.configuration._publish()`
	# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__build_codex_disabled()`
	# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__build_codex_enabled()`
	# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_native_builder_and_projection_publisher()`
	def __init__(self, root: str | Path, outputs: dict, *, check: bool=False, merge: dict | None=None, retire: Any=(), disown: Any=(), preflight: bool=False) -> None:
		self.__root = Path(root).resolve()
		self.__outputs = outputs
		self.__check = check
		self.__merge = merge or {}
		self.__retire = tuple(retire)
		self.__disown = tuple(disown)
		self.__preflight = preflight
	# @used-by :meth:`ProjectionPublisher.__commit()`
	def __finalize_codex_receipt(self, previous: dict) -> None:
		config = dfh_project_paths(self.__root, exact_root=True).codex_config_toml
		if config in self.__outputs:
			if self.__outputs[config].strip():
				value = tomllib.loads(self.__outputs[config]).get('developer_instructions', '')
				previous[str(config)] = {'block_sha256': dfh_digest(dfh_extract_managed_block(value).encode()), 'sha256': dfh_digest(self.__outputs[config].encode())}
			else:
				if config.read_bytes() != self.__outputs[config].encode('utf-8'):
					raise ValueError('Empty projection changed during retirement; external edit preserved')
				config.unlink()
				previous.pop(str(config), None)
				try:
					config.parent.rmdir()
				except OSError:
					pass
	# @used-by :meth:`ProjectionPublisher.__publish_locked()`
	def __plan_outputs(self, previous: dict, issues: list[dict], planned: dict, preimages: dict) -> None:
		for raw_target, text in self.__outputs.items():
			target = Path(raw_target)
			if dfh_has_linked_ancestor(target):
				issues.append({'file': str(target), 'message': 'Linked native configuration preserved'})
			else:
				payload = text.encode('utf-8')
				actual = target.read_bytes() if target.exists() else None
				key = str(target.resolve())
				if actual != payload:
					owned = dfh_receipt_sha256(previous.get(key))
					if None is not actual and owned != dfh_digest(actual) and (self.__merge.get(target) != actual):
						issues.append({'file': key, 'message': 'Manual/unowned native configuration preserved'})
					elif self.__check:
						issues.append({'file': key, 'message': 'Native projection is missing or stale; run build-native'})
					else:
						planned[target] = payload
						preimages[target] = actual
	# @used-by :meth:`ProjectionPublisher.__publish_locked()`
	def __plan_retirements(self, previous: dict, issues: list[dict], removed: list[Path]) -> None:
		for raw_target in self.__retire:
			target = Path(raw_target)
			if dfh_has_linked_ancestor(target):
				issues.append({'file': str(target), 'message': 'Linked legacy file preserved'})
			else:
				resolved = target.resolve()
				if not resolved.is_relative_to(self.__root):
					raise ValueError('Retirement must stay inside the configured root')
				if resolved.exists():
					if dfh_receipt_sha256(previous.get(str(resolved))) != dfh_digest(resolved.read_bytes()):
						issues.append({'file': str(resolved), 'message': 'Manual/unowned legacy file preserved'})
					elif self.__check:
						issues.append({'file': str(resolved), 'message': 'Owned legacy file needs migration'})
					else:
						removed.append(resolved)
	# @used-by :meth:`ProjectionPublisher.__publish_locked()`
	def __commit(self, manifest: Path, receipt_bytes: bytes | None, previous: dict, disowned: set[str], planned: dict, preimages: dict, removed: list[Path]) -> None:
		self.__write_backups_and_planned(previous, planned, preimages, removed)
		for key in disowned:
			previous.pop(key, None)
		previous.update({str(Path(p).resolve()): dfh_digest(text.encode('utf-8')) for p, text in self.__outputs.items()})
		for target in removed:
			if dfh_digest(target.read_bytes()) != dfh_receipt_sha256(previous[str(target)]):
				raise ValueError('Legacy file changed during migration')
			target.unlink()
			previous.pop(str(target), None)
		self.__finalize_codex_receipt(previous)
		if (manifest.read_bytes() if manifest.exists() else None) != receipt_bytes:
			raise ValueError('Ownership receipt changed during publication; external edit preserved')
		if previous:
			dfh_replace_bytes(manifest, (json.dumps(previous, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
		elif manifest.exists():
			manifest.unlink()
	# @used-by :meth:`ProjectionPublisher.run()`
	def __publish_locked(self) -> dict:
		manifest, receipt_bytes, previous = dfh_load_project_receipt(self.__root)
		issues: list[dict] = []
		planned: dict[Path, bytes] = {}
		removed: list[Path] = []
		preimages: dict[Path, bytes | None] = {}
		disowned = {str(Path(path).resolve()) for path in self.__disown} & set(previous)
		if self.__check:
			issues.extend(({'file': path, 'message': 'Shared definition ownership must move to the central native profile registry'} for path in sorted(disowned)))
		self.__plan_outputs(previous, issues, planned, preimages)
		self.__plan_retirements(previous, issues, removed)
		if issues:
			r: dict[str, Any] = {'issues': issues, 'valid': False, 'written': []}
		else:
			if not self.__check and (not self.__preflight):
				self.__commit(manifest, receipt_bytes, previous, disowned, planned, preimages, removed)
			r = {'issues': [], 'outputs': [str(p) for p in self.__outputs], 'removed': [] if self.__preflight else [str(p) for p in removed], 'valid': True, 'written': [] if self.__preflight else [str(p) for p in planned]}
		return r
	# @used-by :meth:`ProjectionPublisher.__commit()`
	def __write_backups_and_planned(self, previous: dict, planned: dict, preimages: dict, removed: list[Path]) -> None:
		for target in removed:
			payload = target.read_bytes()
			if dfh_digest(payload) != dfh_receipt_sha256(previous[str(target)]):
				raise ValueError('Legacy file changed before backup; external edit preserved')
			dfh_store_content_backup(dfh_data_dir_for(self.__root) / 'native-retired', target, payload, error_message='Retired native backup differs; configuration preserved')
		for target, payload in planned.items():
			if (target.read_bytes() if target.exists() else None) != preimages[target]:
				raise ValueError('Native configuration changed during publication; external edit preserved')
			dfh_replace_bytes(target, payload)
	# @used-by :func:`Df.Harness.lib.config_codex._run_codex_project_publish()`
	# @used-by :func:`agent_tools.configuration._publish()`
	# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__build_codex_disabled()`
	# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__build_codex_enabled()`
	# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_native_builder_and_projection_publisher()`
	def run(self) -> dict:
		if not self.__outputs and (not any((Path(path).exists() for path in self.__retire))):
			r: dict[str, Any] = {'issues': [], 'outputs': [], 'removed': [], 'valid': True, 'written': []}
		else:
			with nullcontext() if self.__check or self.__preflight else dfh_locked(dfh_data_dir_for(self.__root) / 'native-config.lock'):
				r = self.__publish_locked()
		return r
