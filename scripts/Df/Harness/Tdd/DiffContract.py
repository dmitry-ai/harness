# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
import os
import subprocess
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.diff_contract`
class DiffContract:
	DIFF_EXECUTABILITY_GATES: dict[str, str] = {
		'PreToolUse': 'agent_tools.tdd.diff_executability.is_non_executable_diff',
		'polyglot_land': 'agent_tools.tdd.diff_executability.classify_git_range',
		'pre-commit': 'agent_tools.tdd.diff_executability.is_non_executable_diff',
		'runtime_snapshot': 'agent_tools.tdd.diff_executability.should_run_snapshot_canary',
		'tdd/evaluator.py': 'agent_tools.tdd.diff_executability.is_git_path_non_executable',
		'worktree_land': 'agent_tools.tdd.diff_executability.classify_git_range',
	}
	MIXED_COMMIT_COMMENT_THRESHOLD = 20
	__NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
	__SNAPSHOT_CONFIG_FILES = frozenset({'paths.json', 'runtime.json'})
	# @used-by :meth:`DiffContract.check_staged_mixed_commit_warning()`
	# @used-by :meth:`DiffContract.check_touched_mixed_commit_warning()`
	@staticmethod
	def __git_batch_texts(repo: Path, specs: list[str]) -> dict[str, str | None]:
		r: dict[str, str | None] = {}
		if specs and (repo / '.git').exists():
			proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), 'cat-file', '--batch'], input=('\n'.join(specs) + '\n').encode('utf-8'), capture_output=True, env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}, timeout=30, check=False, creationflags=DiffContract.__NO_WINDOW)
			if 0 == proc.returncode:
				r = DiffContract.__parse_batch_blobs(proc.stdout, specs)
		return r
	# @used-by :meth:`DiffContract.__git_batch_texts()`
	@staticmethod
	def __parse_batch_blobs(raw: bytes, specs: list[str]) -> dict[str, str | None]:
		out: dict[str, str | None] = {}
		pos, total = (0, len(raw))
		for spec in specs:
			nl = raw.find(b'\n', pos)
			if 0 > nl:
				break
			hdr = raw[pos:nl].decode('utf-8', errors='replace')
			pos = nl + 1
			parts = hdr.rsplit(' ', 2)
			if 3 == len(parts) and 'blob' == parts[1] and parts[2].isdigit():
				size = int(parts[2])
				blob = raw[pos:pos + size]
				pos = min(total, pos + size + 1)
				out[spec] = None if b'\x00' in blob else blob.decode('utf-8', errors='replace')
			else:
				out[spec] = None
		return out
	# @used-by :func:`agent_tools.tdd.diff_contract.check_staged_mixed_commit_warning()`
	# @used-by :meth:`Df.Harness.Gate.StagedGates.StagedGates.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_tdd_diff_contract_coverage_and_executability()`
	@staticmethod
	def check_staged_mixed_commit_warning(repo_root: Path, staged_paths: list[str], *, use_index: bool=True, threshold: int=MIXED_COMMIT_COMMENT_THRESHOLD) -> dict[str, Any] | None:
		paths = list(staged_paths or ())
		if len(paths) <= threshold:
			r: dict[str, Any] | None = None
		else:
			from Df.Harness.Tdd.DiffExecutability import DiffExecutability
			repo = Path(repo_root).resolve()
			specs = [f'HEAD:{rel}' for rel in paths] + ([f':{rel}' for rel in paths] if use_index else [])
			blobs = DiffContract.__git_batch_texts(repo, specs)
			cats: dict[str, str] = {}
			for rel in paths:
				cur = blobs.get(f':{rel}') if use_index else ((repo / rel).read_text(encoding='utf-8', errors='replace') if (repo / rel).is_file() else None)
				cats[rel] = DiffExecutability.classify_text_diff(repo / rel, blobs.get(f'HEAD:{rel}'), cur, repo_root=repo)
			r = DiffContract.detect_mixed_commit_warning(DiffExecutability.summarize_categories(cats), threshold=threshold)
		return r
	# @used-by :func:`agent_tools.tdd.diff_contract.check_touched_mixed_commit_warning()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_tdd_diff_contract_coverage_and_executability()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov1.DfHarnessS11Wave2bTddCov1Tests.test_diff_contract_executability_and_coverage_end_to_end()`
	@staticmethod
	def check_touched_mixed_commit_warning(repo_root: Path, rel_paths: list[str], *, project_root: Path | None=None, threshold: int=MIXED_COMMIT_COMMENT_THRESHOLD) -> dict[str, Any] | None:
		paths = list(rel_paths or ())
		if len(paths) <= threshold:
			r: dict[str, Any] | None = None
		else:
			from Df.Harness.Tdd.DiffExecutability import DiffExecutability
			repo = Path(repo_root).resolve()
			blobs = DiffContract.__git_batch_texts(repo, [f'HEAD:{rel}' for rel in paths] + [f'HEAD~1:{rel}' for rel in paths])
			cats: dict[str, str] = {}
			for rel in paths:
				cur = (repo / rel).read_text(encoding='utf-8', errors='replace') if (repo / rel).is_file() else None
				head = blobs.get(f'HEAD:{rel}')
				if None is not cur and cur == head:
					old = blobs.get(f'HEAD~1:{rel}')
					cats[rel] = DiffExecutability.classify_text_diff(repo / rel, old, cur, repo_root=repo, project_root=project_root) if old != cur else DiffExecutability.classify_git_path(repo, rel, disk_text=cur, project_root=project_root)
				else:
					cats[rel] = DiffExecutability.classify_text_diff(repo / rel, head, cur, repo_root=repo, project_root=project_root)
			r = DiffContract.detect_mixed_commit_warning(DiffExecutability.summarize_categories(cats), threshold=threshold)
		return r
	# @used-by :func:`agent_tools.tdd.diff_contract.detect_mixed_commit_warning()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.format_land_diff_telemetry()`
	# @used-by :meth:`DiffContract.check_staged_mixed_commit_warning()`
	# @used-by :meth:`DiffContract.check_touched_mixed_commit_warning()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_diff_executability_and_coverage()`
	@staticmethod
	def detect_mixed_commit_warning(diff_info: dict[str, Any] | None, *, threshold: int=MIXED_COMMIT_COMMENT_THRESHOLD) -> dict[str, Any] | None:
		info = diff_info or {}
		counts = info.get('category_counts') or {}
		cmt_cnt = int(counts.get('comment_only') or 0)
		exec_cnt = len(info.get('executable_files') or ()) or int(counts.get('executable') or 0)
		if 1 > exec_cnt or threshold > cmt_cnt:
			r: dict[str, Any] | None = None
		else:
			msg = f'Mixed bulk comment-only ({cmt_cnt} files, threshold {threshold}) and executable ({exec_cnt} file(s)) changes in one commit; split executable fixes and runtime decorators (@override) from bulk comment-only annotation passes into separate child issues and commits.'
			r = {'code': 'MIXED_BULK_COMMENT_AND_EXECUTABLE_COMMIT', 'comment_only_file_count': cmt_cnt, 'executable_file_count': exec_cnt, 'message': msg, 'threshold': threshold}
		return r
	# @used-by :func:`agent_tools.tdd.diff_contract.should_run_snapshot_canary()`
	@staticmethod
	def should_run_snapshot_canary(repo_root: Path, base_ref: str | None=None, *, diff_info: dict[str, Any] | None=None, classify_range_fn=None) -> tuple[bool, str]:
		from Df.Harness.Tdd.DiffExecutability import DiffExecutability
		if None is diff_info and (not base_ref):
			r: tuple[bool, str] = (True, 'no_base_ref')
		else:
			fn = classify_range_fn if None is not classify_range_fn else DiffExecutability.classify_git_range
			info = diff_info if None is not diff_info else fn(repo_root, str(base_ref), 'HEAD')
			if info.get('is_executable'):
				r = (True, 'executable_diff')
			elif any((Path(p).name in DiffContract.__SNAPSHOT_CONFIG_FILES for p in (info.get('file_categories') or ()))):
				r = (True, 'runtime_config_changed')
			else:
				r = (False, f"non_executable_diff:{info.get('classification', 'non_code')}")
		return r
