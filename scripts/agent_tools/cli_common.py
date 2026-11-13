# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify declarative CLI routers, scratch-verified --consume-input/stdin loading, and read-back mutations in cli_common.py":
# https://github.com/dmitry-ai/harness/issues/69
import hashlib
import json
from pathlib import Path
import sys
def add_arg_specs(parser, specs: tuple | list) -> None:
	for flags, kwargs in specs:
		names = flags if isinstance(flags, tuple) else (flags,)
		parser.add_argument(*names, **kwargs)
def consume_scratch_input(args, path, payload: bytes, result: dict) -> dict:
	if not getattr(args, 'consume_input', False) or '-' == str(path):
		r = result
	else:
		target = verify_scratch_input_path(args.project, path)
		if 'conflict' == result.get('status') or False is result.get('complete') or False is result.get('valid'):
			r = result
		else:
			if target.exists() and target.read_bytes() == payload:
				target.unlink()
				result['consumed_input'] = str(target)
			r = result
	return r
def consume_unchanged_files(files: list[tuple[Path, bytes]]) -> list[str]:
	r: list[str] = []
	for path, expected_bytes in files:
		if path.exists() and path.read_bytes() == expected_bytes:
			path.unlink()
			r.append(str(path))
	return r
def dump_json(payload, *, stream=None) -> None:
	print(json.dumps(payload, ensure_ascii=False, indent=2), file=stream or sys.stdout)
def load_operation_input(args, path) -> bytes:
	if getattr(args, 'consume_input', False) and '-' != str(path):
		verify_scratch_input_path(args.project, path)
	if 'answer-prepare' == getattr(args, 'command', None) and '-' != str(path):
		from .storage import data_dir_for
		target = Path(path).resolve()
		if 'answer.md' == target.name.lower():
			turns_dir = data_dir_for(args.project) / 'turns'
			cur_conv = getattr(args, 'conversation', None)
			if turns_dir.is_dir():
				for tf in turns_dir.glob('*.json'):
					if '-' in tf.stem:
						continue
					try:
						tdata = json.loads(tf.read_text(encoding='utf-8'))
					except (OSError, ValueError):
						continue
					if isinstance(tdata, dict) and tdata.get('status') in ('open', 'prepared', 'preparation_unverified') and (None is cur_conv or tdata.get('conversation_id') != cur_conv):
						raise ValueError('Shared \ua616/data/scratch/answer.md is prohibited when parallel turns are active; write to \ua616/data/scratch/answer-<turn_key>.md')
	r = read_input_bytes(path)
	expected_sha = getattr(args, 'expected_sha256', None)
	if expected_sha and 'save-analysis' != getattr(args, 'command', None):
		actual_sha = hashlib.sha256(r).hexdigest().lower()
		if actual_sha != str(expected_sha).strip().lower():
			raise ValueError(f'Input SHA-256 mismatch against --expected-sha256: expected {expected_sha}, got {actual_sha}')
	return r
def read_input_bytes(path) -> bytes:
	return sys.stdin.buffer.read() if '-' == str(path) else Path(path).read_bytes()
def read_input_json(path, *, encoding: str='utf-8-sig'):
	return json.loads(read_input_text(path, encoding=encoding)) if None is not path else None
def read_input_text(path, *, encoding: str='utf-8-sig') -> str:
	return read_input_bytes(path).decode(encoding)
def result_exit_code(result: dict, *, extra_failures: tuple=()) -> int:
	failed = False is result.get('valid') or False is result.get('complete') or 'conflict' == result.get('status') or any(extra_failures)
	return 2 if failed else 0
def verify_scratch_input_path(project, path) -> Path:
	from .storage import data_dir_for
	r = Path(path).resolve()
	scratch_dirs = [data_dir_for(project) / 'scratch', Path(project).resolve() / '\ua616/data/scratch']
	if not any((r.is_relative_to(s) for s in scratch_dirs)) or Path(path).is_symlink() or any((p.is_junction() for p in (r, *r.parents) if p.exists())):
		raise ValueError('Consumed input must be an ordinary file inside project \ua616/data/scratch')
	return r
