# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.storage import data_dir_for, locked, replace_bytes
from datetime import datetime
from Df.Harness.Project.Context.ContextAssembler import ContextAssembler
from Df.Harness.Project.Context.LetterDiscoverer import LetterDiscoverer
import json
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ContextGenerator:
	# @used-by :func:`agent_tools.context.generate()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_context_classes()`
	def __init__(self, root: Path, config: Path | dict | None=None, output: Path | None=None, dry_run: bool=False, now: datetime | None=None) -> None:
		self.__root, self.__config, self.__output = (root, config, output)
		self.__dry_run, self.__now = (dry_run, now)
	# @used-by :meth:`ContextGenerator.generate()`
	def __build(self, root: Path, pp, manifest: dict, default_out: str) -> tuple[Path, str, list[Path]]:
		content, sources = ContextAssembler(root, manifest, now=self.__now).assemble()
		raw_out = self.__output if None is not self.__output else LetterDiscoverer.expand_entry(pp, manifest.get('output', default_out))
		target = LetterDiscoverer.inside(root, raw_out)
		cfg = self.__config
		if target in sources or (isinstance(cfg, (str, Path)) and target == (Path(cfg).resolve() if Path(cfg).is_absolute() else (root / cfg).resolve())):
			raise ValueError('Context output would overwrite an input')
		if not self.__dry_run:
			replace_bytes(target, content.encode('utf-8'))
		return (target, content, sources)
	# @used-by :meth:`ContextGenerator.generate()`
	def __load_manifest(self, root: Path) -> dict:
		if None is self.__config:
			r = LetterDiscoverer.default_config(root)
		elif isinstance(self.__config, dict):
			r = self.__config
		else:
			cfg_path = Path(self.__config).resolve() if Path(self.__config).is_absolute() else (root / self.__config).resolve()
			if not cfg_path.is_file():
				raise FileNotFoundError(cfg_path)
			r = json.loads(cfg_path.read_text(encoding='utf-8-sig'))
		return r
	# @used-by :func:`agent_tools.context.generate()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_context_classes()`
	def generate(self) -> tuple[Path, str, list[Path]]:
		from agent_tools.path_registry import canonicalize_root_dir, project_paths
		root = canonicalize_root_dir(self.__root)
		pp = project_paths(root, exact_root=True)
		manifest = self.__load_manifest(root)
		default_out = pp.context_output.relative_to(root).as_posix() if pp.context_output.is_relative_to(root) else 'ꙮ/0/Context.md'
		if self.__dry_run:
			r = self.__build(root, pp, manifest, default_out)
		else:
			with locked(data_dir_for(root) / 'context.lock'):
				r = self.__build(root, pp, manifest, default_out)
		return r
