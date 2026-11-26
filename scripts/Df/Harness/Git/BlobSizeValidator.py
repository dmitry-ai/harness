# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
EXTRACTED_MAX_BYTES = 16 * 1024 * 1024
GITHUB_MAX_BLOB_BYTES = 100 * 1024 * 1024
_EXTRACTED_DERIVED_RE = re.compile(r'(?:^|/)(?:Evidence/HTTP/[^/]+/[^/]+/extracted-[^/]+\.json|Evidence/Extracted/[0-9a-f]{64}/[^/]+\.json|extracted-(?:html|text|json)(?:-[0-9a-f]{16})?\.json)$')
_ZERO_SHA_RE = re.compile(r'^0+$')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class BlobSizeValidator:
	# @used-by :func:`agent_tools.git_gate._check_blob_size_limits()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_push_blob_sizes()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_staged_blob_sizes()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	def __init__(self, gate, *, extracted_max: int | None=None, github_max: int | None=None) -> None:
		self.__gate = gate
		self.__extracted_max = int(extracted_max) if None is not extracted_max else EXTRACTED_MAX_BYTES
		self.__github_max = int(github_max) if None is not github_max else GITHUB_MAX_BLOB_BYTES
	# @used-by :meth:`BlobSizeValidator.__verify_push()`
	# @used-by :meth:`BlobSizeValidator.__verify_staged()`
	# @used-by :meth:`BlobSizeValidator.validate()`
	def __check_limit(self, rel_posix: str, size: int, *, kind: str, sha: str='') -> None:
		if rel_posix and _EXTRACTED_DERIVED_RE.search(rel_posix) and self.__extracted_max < size:
			label = f'{rel_posix} ({sha[:12]})' if sha else rel_posix
			noun = 'derived extraction blob' if sha else 'derived extraction file'
			raise ValueError(f'{kind} {noun} {label} is {size} bytes, exceeding MAX_BYTES ({self.__extracted_max} bytes)')
		if self.__github_max < size:
			label = (f'{rel_posix} ({sha[:12]})' if rel_posix else sha[:12]) if sha else rel_posix
			raise ValueError(f'{kind} Git blob {label} is {size} bytes, exceeding GitHub GH001 hard limit ({self.__github_max} bytes)')
	# @used-by :meth:`BlobSizeValidator.__verify_push()`
	def __collect_push_revs(self, stdin_lines: list[str] | None) -> list[str]:
		rev_args: list[str] = []
		if None is stdin_lines:
			if 0 == self.__gate.run_read(['rev-parse', '--verify', 'HEAD'], check=False).returncode:
				rev_args = ['HEAD', '--not', '--remotes']
		else:
			for raw_line in stdin_lines:
				parts = raw_line.strip().split()
				if 4 <= len(parts) and (not _ZERO_SHA_RE.match(parts[1])):
					rev_args.append(f'{parts[3]}..{parts[1]}') if not _ZERO_SHA_RE.match(parts[3]) else rev_args.extend([parts[1], '--not', '--remotes'])
		return rev_args
	# @used-by :meth:`BlobSizeValidator.validate()`
	def __verify_push(self, stdin_lines: list[str] | None) -> None:
		rev_args = self.__collect_push_revs(stdin_lines)
		if rev_args:
			rev_proc = self.__gate.run_read(['rev-list', '--objects', *rev_args], check=False)
			if 0 == rev_proc.returncode and rev_proc.stdout.strip():
				cat_proc = self.__gate.run_read(['cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize) %(rest)'], check=False, input_bytes=rev_proc.stdout)
				if 0 == cat_proc.returncode:
					for line in cat_proc.stdout.decode('utf-8', errors='replace').splitlines():
						parts = line.strip().split(' ', 3)
						if 3 <= len(parts) and 'blob' == parts[1] and parts[2].isdigit():
							self.__check_limit((parts[3] if 3 < len(parts) else '').replace('\\', '/'), int(parts[2]), kind='Unpushed', sha=parts[0])
	# @used-by :meth:`BlobSizeValidator.validate()`
	def __verify_staged(self, staged_paths: list[str] | None) -> None:
		paths = list(staged_paths) if None is not staged_paths else self.__gate.staged_paths()
		if paths:
			batch_in = ''.join((f':{p}\n' for p in paths)).encode('utf-8')
			proc = self.__gate.run_read(['cat-file', '--batch-check=%(objecttype) %(objectsize)'], check=False, input_bytes=batch_in)
			if 0 == proc.returncode:
				for rel_raw, line in zip(paths, proc.stdout.decode('utf-8', errors='replace').splitlines()):
					parts = line.strip().split()
					if 2 <= len(parts) and 'blob' == parts[0] and parts[1].isdigit():
						self.__check_limit(rel_raw.replace('\\', '/'), int(parts[1]), kind='Staged')
	# @used-by :func:`agent_tools.git_gate._check_blob_size_limits()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_push_blob_sizes()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_staged_blob_sizes()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	def validate(self, *, mode: str='staged', staged_paths: list[str] | None=None, stdin_lines: list[str] | None=None, single: tuple[str, int, str, str] | None=None) -> None:
		if None is not single:
			self.__check_limit(single[0], single[1], kind=single[2], sha=single[3])
		elif (self.__gate.root / '.git').exists():
			if 'push' == mode:
				self.__verify_push(stdin_lines)
			else:
				self.__verify_staged(staged_paths)
