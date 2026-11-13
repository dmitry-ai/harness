# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Decompose experiments.py into ExperimentPlanStore, BrowserTraceInspector, and ExperimentRunValidator classes and unify raw_decode JSON object scanning":
# https://github.com/dmitry-ai/harness/issues/72
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
# https://github.com/dmitry-ai/harness/issues/41
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
def _replace_with_retry(temp: Path, path: Path):
	for attempt in range(10):
		try:
			os.replace(temp, path)
			break
		except PermissionError:
			if 9 == attempt:
				raise
			time.sleep(0.025)
def _stage_atomic_write(path: Path, data: bytes, commit):
	fd, name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
	temp = Path(name)
	try:
		with os.fdopen(fd, 'wb') as stream:
			stream.write(data)
			stream.flush()
			os.fsync(stream.fileno())
		commit(temp, path)
	finally:
		temp.unlink(missing_ok=True)
def create_bytes(path: Path, data: bytes):
	_stage_atomic_write(Path(path), data, os.rename if 'nt' == os.name else os.link)
def data_dir_for(path: Path) -> Path:
	resolved = Path(path).resolve()
	if 'c:/work/upwork/code' == str(resolved).replace('\\', '/').rstrip('/').lower():
		r = Path('C:/work/research/provision/code/AI/harness/_/ꘖ/data/workspaces/upwork')
	else:
		start = resolved if not resolved.exists() or resolved.is_dir() else resolved.parent
		r = start / 'ꘖ' / 'data'
		for parent in (start, *start.parents):
			if 'ꘖ' == parent.name:
				r = parent / 'data'
				break
			if (parent / '_').is_dir() and ((parent / 'code').is_dir() or (parent / '_/ꙮ').is_dir() or (parent / '_/ꘖ').is_dir()):
				r = parent / '_' / 'ꘖ' / 'data'
				break
			if (parent / 'ꘖ').is_dir():
				r = parent / 'ꘖ' / 'data'
				break
			if '.agents' == parent.name:
				r = parent.parent / '_' / 'ꘖ' / 'data' if (parent.parent / '_').is_dir() and (parent.parent / 'code').is_dir() else parent.parent / 'ꘖ' / 'data'
				break
			if (parent / '.agents').is_dir():
				r = Path('C:/work/research/provision/code/AI/harness/_/ꘖ/data/workspaces/upwork') if 'c:/work/upwork/code' == str(parent).replace('\\', '/').rstrip('/').lower() else parent / 'ꘖ' / 'data'
				break
	return r
def iter_embedded_json_objects(value, *, parse_root: bool=True, recursive: bool=True):
	if isinstance(value, dict):
		yield value
		if recursive:
			for child in value.values():
				yield from iter_embedded_json_objects(child, parse_root=parse_root, recursive=recursive)
	elif isinstance(value, list):
		for child in value:
			yield from iter_embedded_json_objects(child, parse_root=parse_root, recursive=recursive)
	elif isinstance(value, str):
		parsed, loaded = (None, False)
		if parse_root:
			try:
				parsed = json.loads(value)
				loaded = True
			except ValueError:
				loaded = False
		if loaded:
			if not isinstance(parsed, str):
				yield from iter_embedded_json_objects(parsed, parse_root=parse_root, recursive=recursive)
		else:
			decoder, start = (json.JSONDecoder(), 0)
			while 0 <= (start := value.find('{', start)):
				try:
					item, size = decoder.raw_decode(value[start:])
				except ValueError:
					start += 1
				else:
					yield from iter_embedded_json_objects(item, parse_root=parse_root, recursive=recursive)
					start += size
@contextmanager
def locked(path: Path, timeout: float=15, *, create=True):
	if create:
		path.parent.mkdir(parents=True, exist_ok=True)
	with path.open('a+b' if create else 'r+b') as stream:
		stream.seek(0, os.SEEK_END)
		if create and not stream.tell():
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
def read_addressed_json(path: Path, *, suffix: str='', stem_match: bool=False, error_msg: str='Invalid immutable artifact') -> tuple[bytes, dict]:
	target = Path(path)
	raw = target.read_bytes()
	value = json.loads(raw.decode('utf-8-sig'))
	sha = hashlib.sha256(raw).hexdigest()
	expected = sha if stem_match else sha + suffix
	actual = target.stem if stem_match else target.name
	if not isinstance(value, dict) or actual != expected:
		raise ValueError(error_msg)
	return (raw, value)
def replace_bytes(path: Path, data: bytes):
	target = Path(path)
	same = False
	try:
		same = target.read_bytes() == data
	except FileNotFoundError:
		pass
	if not same:
		target.parent.mkdir(parents=True, exist_ok=True)
		_stage_atomic_write(target, data, _replace_with_retry)
def write_immutable_bytes(path: Path, payload: bytes, *, diff_error: str='Immutable artifact differs') -> Path:
	target = Path(path)
	target.parent.mkdir(parents=True, exist_ok=True)
	if target.exists():
		if target.read_bytes() != payload:
			raise ValueError(diff_error)
	else:
		try:
			create_bytes(target, payload)
		except FileExistsError:
			if target.read_bytes() != payload:
				raise ValueError(diff_error)
	return target
