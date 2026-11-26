# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.state import df_is_windows
import time
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class AtomicWriter:
	# @used-by :func:`agent_tools.storage.create_bytes()`
	# @used-by :func:`agent_tools.storage.replace_bytes()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_config_and_native_profile_classes()`
	def __init__(self, path: str | Path, data: bytes, *, mode: str='replace') -> None:
		self.__path = Path(path)
		self.__data = data
		self.__mode = mode
	# @used-by :meth:`AtomicWriter.run()`
	def __commit(self, temp: Path, target: Path) -> None:
		from agent_tools import storage as st
		if 'create' == self.__mode:
			(st.os.rename if df_is_windows() else st.os.link)(temp, target)
		else:
			for attempt in range(10):
				try:
					st.os.replace(temp, target)
					break
				except PermissionError:
					if 9 == attempt:
						raise
					time.sleep(0.025)
	# @used-by :meth:`AtomicWriter.run()`
	def __should_skip_fsync(self) -> bool:
		from agent_tools import storage as st
		r = False
		if '1' == st.os.environ.get('HARNESS_TEST_NO_FSYNC'):
			try:
				r = self.__path.resolve().is_relative_to(Path(st.tempfile.gettempdir()).resolve())
			except (OSError, ValueError):
				r = False
		return r
	# @used-by :func:`agent_tools.storage.create_bytes()`
	# @used-by :func:`agent_tools.storage.replace_bytes()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_config_and_native_profile_classes()`
	def run(self) -> None:
		from agent_tools import storage as st
		self.__path.parent.mkdir(parents=True, exist_ok=True)
		if 'create' == self.__mode or (not self.__path.is_file()) or self.__path.read_bytes() != self.__data:
			fd, name = st.tempfile.mkstemp(prefix=f'.{self.__path.name}.', dir=self.__path.parent)
			temp = Path(name)
			try:
				with st.os.fdopen(fd, 'wb') as stream:
					stream.write(self.__data)
					stream.flush()
					if not self.__should_skip_fsync():
						st.os.fsync(stream.fileno())
				self.__commit(temp, self.__path)
			finally:
				temp.unlink(missing_ok=True)
