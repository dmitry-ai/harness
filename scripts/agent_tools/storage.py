# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
import time
def data_dir_for(path: Path) -> Path:
	resolved = Path(path).resolve()
	if 'c:/work/upwork/code' == str(resolved).replace('\\', '/').rstrip('/').lower():
		return Path('C:/work/research/provision/code/AI/harness/_/ꘖ/data/workspaces/upwork')
	start = resolved if not resolved.exists() or resolved.is_dir() else resolved.parent
	for parent in (start, *start.parents):
		if 'ꘖ' == parent.name:
			return parent / 'data'
		if (parent / '_').is_dir() and ((parent / 'code').is_dir() or (parent / '_/ꙮ').is_dir() or (parent / '_/ꘖ').is_dir()):
			return parent / '_' / 'ꘖ' / 'data'
		if (parent / 'ꘖ').is_dir():
			return parent / 'ꘖ' / 'data'
		if '.agents' == parent.name:
			if (parent.parent / '_').is_dir() and (parent.parent / 'code').is_dir():
				return parent.parent / '_' / 'ꘖ' / 'data'
			return parent.parent / 'ꘖ' / 'data'
		if (parent / '.agents').is_dir():
			if 'c:/work/upwork/code' == str(parent).replace('\\', '/').rstrip('/').lower():
				return Path('C:/work/research/provision/code/AI/harness/_/ꘖ/data/workspaces/upwork')
			return parent / 'ꘖ' / 'data'
	return start / 'ꘖ' / 'data'
@contextmanager
def locked(path: Path, timeout: float=15):
	path.parent.mkdir(parents=True, exist_ok=True)
	with path.open('a+b') as stream:
		stream.seek(0, os.SEEK_END)
		if not stream.tell():
			stream.write(b'\x00')
			stream.flush()
		deadline = time.monotonic() + timeout
		while True:
			try:
				stream.seek(0)
				if 'nt' == os.name:
					import msvcrt
					msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
				else:
					import fcntl
					fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
				break
			except OSError:
				if time.monotonic() >= deadline:
					raise TimeoutError(f'Lock busy: {path}')
				time.sleep(0.05)
		try:
			yield
		finally:
			stream.seek(0)
			if 'nt' == os.name:
				msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
			else:
				fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
def create_bytes(path: Path, data: bytes):
	path = Path(path)
	fd, name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
	temp = Path(name)
	try:
		with os.fdopen(fd, 'wb') as stream:
			stream.write(data)
			stream.flush()
			os.fsync(stream.fileno())
		if 'nt' == os.name:
			os.rename(temp, path)
		else:
			os.link(temp, path)
	finally:
		temp.unlink(missing_ok=True)
def replace_bytes(path: Path, data: bytes):
	path.parent.mkdir(parents=True, exist_ok=True)
	fd, name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
	temp = Path(name)
	try:
		with os.fdopen(fd, 'wb') as stream:
			stream.write(data)
			stream.flush()
			os.fsync(stream.fileno())
		for attempt in range(10):
			try:
				os.replace(temp, path)
				break
			except PermissionError:
				if 9 == attempt:
					raise
				time.sleep(0.025)
	finally:
		temp.unlink(missing_ok=True)
