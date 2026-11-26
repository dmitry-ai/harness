# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec, SourceFileLoader
from importlib.util import spec_from_file_location
from pathlib import Path
import sys
# 2026-11-26 "Add Df package dot-py bootstrap and dot-py support across Harness gates": https://github.com/dmitry-ai/harness/issues/320
class DotPyFinder(MetaPathFinder):
	# @used-by :func:`_install_dotpy_finder()`
	# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_df_bootstrap_loads_dotpy_packages_and_sibling_modules()`
	def __init__(self, prefix: str, root: Path) -> None:
		self.__prefix = prefix
		self.__root = Path(root).resolve()
	# @used-by :meth:`DotPyFinder.find_spec()`
	def __resolve_target(self, fullname: str) -> tuple[Path, Path] | None:
		r: tuple[Path, Path] | None = None
		if fullname.startswith(f'{self.__prefix}.'):
			base = self.__root.joinpath(*fullname.split('.')[1:])
			dot_py = base / '.py'
			py_file = base.with_suffix('.py')
			if dot_py.is_file():
				r = (dot_py, base)
			elif py_file.is_file() and base.is_dir():
				r = (py_file, base)
		return r
	# @used-by :func:`agent_tools.tdd.diff_coverage._pytest_argv()`
	# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_doctor_and_turn_begin_exclude_addons_health()`
	def find_spec(self, fullname: str, path=None, target=None) -> ModuleSpec | None:
		hit = self.__resolve_target(fullname)
		if None is hit:
			r: ModuleSpec | None = None
		else:
			src, pkg_dir = hit
			r = spec_from_file_location(fullname, src, loader=SourceFileLoader(fullname, str(src)), submodule_search_locations=[str(pkg_dir)])
		return r
# @used-by :mod:`Df`
def _install_dotpy_finder() -> None:
	root = Path(__file__).resolve().parent
	if not any(isinstance(f, DotPyFinder) and f._DotPyFinder__root == root for f in sys.meta_path):
		sys.meta_path.insert(0, DotPyFinder('Df', root))
_install_dotpy_finder()
