# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
from Df.Harness.Arch.ReviewValidator import ReviewValidator
from Df.Harness.Arch.SpecValidator import SpecValidator
from Df.Harness.Arch.TriggerClassifier import TriggerClassifier
from agent_tools.path_registry import project_paths
from agent_tools.research import inside, json_data
from agent_tools.storage import locked, replace_bytes, write_immutable_bytes
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
class ReviewStore:
	__VALID_KINDS = frozenset({'code_diff', 'design', 'response'})
	# @used-by :func:`agent_tools.arch.review_store.record_arch_review()`
	# @used-by :meth:`Df.Harness.Arch.ReviewCli.ReviewCli.__exec_arch_record_review()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_enforcement_preserves_gates_and_395_participants()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_evaluator_checks_response_receipts_and_runner()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_review_store_roundtrip_auth_and_patch_seam()`
	def __init__(self, root: Path, *, auth_fn: Callable[..., dict[str, Any]] | None=None) -> None:
		self.__root = Path(root)
		self.__auth_fn = ReviewStore.authenticate_report if None is auth_fn else auth_fn
	# @used-by :meth:`ReviewStore.__index_path()`
	# @used-by :meth:`ReviewStore.__load_verified_package()`
	# @used-by :meth:`ReviewStore.prepare_package()`
	# @used-by :meth:`ReviewStore.read_review_input()`
	# @used-by :meth:`ReviewStore.record_review()`
	@staticmethod
	def __arch_dir(root: Path) -> Path:
		return project_paths(root, exact_root=True).data_dir / 'arch-reviews'
	# @used-by :meth:`ReviewStore.prepare_package()`
	@staticmethod
	def __build_package_payload(kind: str, parent_id: str, response_text: str | None, spec_text: str | None, modules: dict[str, dict[str, Any]], issue_url: str | None) -> dict[str, Any]:
		subj_sha = ReviewStore.__subject_digest(kind, response_text, spec_text, modules, issue_url)
		spec_src = spec_text if None is not spec_text else (response_text or '')
		spec_res = SpecValidator().validate(spec_src, require_full_fields='response' != kind)
		return {'schema_version': 1, 'review_mode': 'falsifier', 'subject_kind': kind, 'subject_sha256': subj_sha, 'parent_id': parent_id, 'issue_url': issue_url, 'response_text': response_text, 'response_sha256': hashlib.sha256(response_text.encode('utf-8')).hexdigest() if None is not response_text else None, 'spec_text': spec_text, 'declared_participants': list(spec_res['participants']), 'spec_validation': spec_res, 'modules': modules, 'module_hashes': {k: v['sha256'] for k, v in modules.items()}}
	# @used-by :meth:`ReviewStore.prepare_package()`
	@staticmethod
	def __collect_modules(repo: Path | None, files: list[str] | None) -> dict[str, dict[str, Any]]:
		r: dict[str, dict[str, Any]] = {}
		if None is not repo and files:
			repo_p = Path(repo).resolve()
			clf = TriggerClassifier()
			for rel in sorted({f.replace('\\', '/').lstrip('./') for f in files if f}):
				target = inside(repo_p, rel)
				if not target.is_file():
					raise ValueError(f'Target module does not exist inside repo: {rel}')
				raw = target.read_bytes()
				text = raw.decode('utf-8', errors='replace')
				raw_sym = TriggerClassifier.extract_symbols(text, rel_path=rel)
				syms = {**{k: sorted(raw_sym[k]) for k in ('classes', 'cross_imports', 'functions', 'imports', 'interfaces')}, 'sloc': raw_sym['sloc']}
				r[rel] = {'sha256': hashlib.sha256(raw).hexdigest(), 'symbols': syms, 'trigger': clf.classify_code_change(rel, None, text)}
		return r
	# @used-by :meth:`ReviewStore.__load_index()`
	# @used-by :meth:`ReviewStore.__persist_review_index()`
	# @used-by :meth:`ReviewStore.__register_package_index()`
	@staticmethod
	def __index_path(root: Path) -> Path:
		return ReviewStore.__arch_dir(root) / 'index.json'
	# @used-by :meth:`ReviewStore.prepare_package()`
	@staticmethod
	def __is_cached(index: dict[str, Any], subject_sha: str, modules: dict[str, dict[str, Any]]) -> bool:
		approved_mods = index.get('approved_modules') or {}
		by_subj = subject_sha in (index.get('approved_subjects') or {})
		by_mods = bool(modules) and all(((approved_mods.get(rel) or {}).get('sha256') == meta['sha256'] for rel, meta in modules.items()))
		return by_subj or by_mods
	# @used-by :meth:`ReviewStore.__persist_review_index()`
	# @used-by :meth:`ReviewStore.__register_package_index()`
	# @used-by :meth:`ReviewStore.inspect_status()`
	# @used-by :meth:`ReviewStore.prepare_package()`
	@staticmethod
	def __load_index(root: Path) -> dict[str, Any]:
		path = ReviewStore.__index_path(root)
		if path.is_file():
			r = json.loads(path.read_text(encoding='utf-8'))
		else:
			r = {'schema_version': 1, 'packages': {}, 'reviews': [], 'approved_modules': {}, 'approved_subjects': {}, 'open_findings': []}
		return r
	# @used-by :meth:`ReviewStore.record_review()`
	@staticmethod
	def __load_verified_package(root: Path, verdict: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
		pkg_rel = str(verdict.get('package') or '').strip()
		if not pkg_rel:
			raise ValueError('Arch-auditor verdict must specify package path')
		pp = project_paths(root, exact_root=True)
		pkg_path = inside(pp.root, pkg_rel)
		if not pkg_path.is_file() or not pkg_path.resolve().is_relative_to((ReviewStore.__arch_dir(root) / 'packages').resolve()):
			raise ValueError(f'Frozen architecture review package not found: {pkg_rel}')
		raw = pkg_path.read_bytes()
		return (pkg_rel, hashlib.sha256(raw).hexdigest(), json.loads(raw.decode('utf-8')))
	# @used-by :meth:`ReviewStore.record_review()`
	@staticmethod
	def __persist_review_index(root: Path, pkg: dict[str, Any], verdict: dict[str, Any], rev_entry: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
		idx_path = ReviewStore.__index_path(root)
		idx_path.parent.mkdir(parents=True, exist_ok=True)
		with locked(idx_path.with_suffix('.lock')):
			index = ReviewStore.__load_index(root)
			index['reviews'].append(rev_entry)
			if 'approved' == verdict['result']:
				cached = ReviewStore.__update_approved_state(index, pkg, verdict, rev_entry['review_id'], rev_entry['recorded_at'])
			else:
				cached = []
				ReviewStore.__update_rejected_state(index, pkg, verdict, rev_entry['review_id'], rev_entry['recorded_at'])
			replace_bytes(idx_path, json_data(index))
			open_f = list(index.get('open_findings') or ())
		return (cached, open_f)
	# @used-by :meth:`ReviewStore.prepare_package()`
	@staticmethod
	def __register_package_index(root: Path, pkg_rel: str, pkg_sha: str, payload: dict[str, Any]) -> None:
		idx_path = ReviewStore.__index_path(root)
		idx_path.parent.mkdir(parents=True, exist_ok=True)
		with locked(idx_path.with_suffix('.lock')):
			index = ReviewStore.__load_index(root)
			index['packages'][pkg_sha] = {'package': pkg_rel, 'subject_kind': payload['subject_kind'], 'subject_sha256': payload['subject_sha256'], 'issue_url': payload.get('issue_url'), 'module_hashes': payload['module_hashes']}
			replace_bytes(idx_path, json_data(index))
	# @used-by :meth:`ReviewStore.__build_package_payload()`
	@staticmethod
	def __subject_digest(kind: str, response_text: str | None, spec_text: str | None, modules: dict[str, dict[str, Any]], issue_url: str | None) -> str:
		basis = {'kind': kind, 'issue_url': issue_url, 'response_sha256': hashlib.sha256(response_text.encode('utf-8')).hexdigest() if None is not response_text else None, 'spec_sha256': hashlib.sha256(spec_text.encode('utf-8')).hexdigest() if None is not spec_text else None, 'module_hashes': {k: v['sha256'] for k, v in sorted(modules.items())}}
		return hashlib.sha256(json_data(basis)).hexdigest()
	# @used-by :meth:`ReviewStore.__persist_review_index()`
	@staticmethod
	def __update_approved_state(index: dict[str, Any], pkg: dict[str, Any], verdict: dict[str, Any], rev_id: str, recorded_at: str) -> list[str]:
		patterns = [c['pattern'] for c in verdict.get('pattern_checks') or () if isinstance(c, dict) and c.get('pattern')]
		subj_sha = pkg['subject_sha256']
		index['approved_subjects'][subj_sha] = {'kind': pkg['subject_kind'], 'review_id': rev_id, 'package': verdict['package'], 'response_sha256': pkg.get('response_sha256'), 'issue_url': pkg.get('issue_url'), 'patterns': patterns, 'recorded_at': recorded_at}
		cached: list[str] = []
		for rel, digest in (pkg.get('module_hashes') or {}).items():
			index['approved_modules'][rel] = {'sha256': digest, 'review_id': rev_id, 'package': verdict['package'], 'patterns': patterns, 'recorded_at': recorded_at}
			cached.append(rel)
		covered = set(cached)
		index['open_findings'] = [f for f in index.get('open_findings') or () if f.get('subject_sha256') != subj_sha and f.get('target') not in covered and (not (pkg.get('issue_url') and f.get('issue_url') == pkg.get('issue_url')))]
		return sorted(cached)
	# @used-by :meth:`ReviewStore.__persist_review_index()`
	@staticmethod
	def __update_rejected_state(index: dict[str, Any], pkg: dict[str, Any], verdict: dict[str, Any], rev_id: str, recorded_at: str) -> None:
		subj_sha = pkg['subject_sha256']
		kept = [f for f in index.get('open_findings') or () if f.get('subject_sha256') != subj_sha]
		for item in verdict.get('findings') or ():
			if isinstance(item, dict) and 'open' == item.get('status'):
				kept.append({**item, 'review_id': rev_id, 'subject_sha256': subj_sha, 'subject_kind': pkg['subject_kind'], 'issue_url': pkg.get('issue_url'), 'recorded_at': recorded_at})
		index['open_findings'] = kept
	# @used-by :func:`agent_tools.arch.review_store._authenticate_arch_report()`
	# @used-by :meth:`ReviewStore.__init__()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_review_store_roundtrip_auth_and_patch_seam()`
	@staticmethod
	def authenticate_report(root: Path, parent_id: str, reviewer_id: str, report_bytes: bytes, pkg_name: str, *, native_evidence: Path | None, wait_timeout: float, platform: str | None, instance: str | None) -> dict[str, Any]:
		from agent_tools import metrics
		if None is not native_evidence:
			raw_ev = json.loads(Path(native_evidence).read_text(encoding='utf-8'))
			proof = metrics.verify_native_proof(root, raw_ev, package=pkg_name)
		else:
			proof = metrics.native_review_proof(root, parent_id, reviewer_id, write=True, platform=platform, instance=instance, wait_timeout=wait_timeout, role='ARCH')
		if hashlib.sha256(report_bytes).hexdigest() != proof.get('final_response_sha256'):
			raise ValueError('Arch-auditor verdict bytes differ from the authenticated native final response')
		return proof
	# @used-by :func:`agent_tools.arch.review_store.inspect_arch_status()`
	# @used-by :meth:`Df.Harness.Arch.ReviewCli.ReviewCli.__exec_arch_check()`
	@staticmethod
	def inspect_status(root: Path, *, repo: Path | None=None, response_text: str | None=None, issue_url: str | None=None) -> dict[str, Any]:
		index = ReviewStore.__load_index(root)
		blocking = [f for f in index.get('open_findings') or () if 'open' == f.get('status') and f.get('severity') in ('significant', 'critical') and (None is issue_url or f.get('issue_url') == issue_url)]
		issues = [f"Open arch-auditor finding {f.get('id')} ({f.get('severity')}): {f.get('description')}" for f in blocking]
		if None is not response_text:
			spec_res = SpecValidator().validate(response_text, require_full_fields=False)
			issues.extend([f"ARCH-1 ({it['code']}): {it['message']}" for it in spec_res['issues']])
		return {'valid': not issues, 'approved_module_count': len(index.get('approved_modules') or {}), 'approved_subject_count': len(index.get('approved_subjects') or {}), 'blocking_findings': blocking, 'issues': issues, 'approved_modules': index.get('approved_modules') or {}, 'approved_subjects': index.get('approved_subjects') or {}}
	# @used-by :func:`agent_tools.arch.review_store.prepare_arch_package()`
	# @used-by :meth:`Df.Harness.Arch.ReviewCli.ReviewCli.__exec_arch_prepare()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_enforcement_preserves_gates_and_395_participants()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_evaluator_checks_response_receipts_and_runner()`
	@staticmethod
	def prepare_package(root: Path, parent_id: str, *, kind: str, response_text: str | None=None, spec_text: str | None=None, repo: Path | None=None, files: list[str] | None=None, issue_url: str | None=None) -> dict[str, Any]:
		if kind not in ReviewStore.__VALID_KINDS:
			raise ValueError(f'Unsupported architecture review subject kind: {kind}')
		modules = ReviewStore.__collect_modules(repo, files)
		payload = ReviewStore.__build_package_payload(kind, parent_id, response_text, spec_text, modules, issue_url)
		raw = json_data(payload)
		pkg_sha = hashlib.sha256(raw).hexdigest()
		subj_sha = payload['subject_sha256']
		pp = project_paths(root, exact_root=True)
		target = write_immutable_bytes(ReviewStore.__arch_dir(root) / 'packages' / f'{kind}-{subj_sha[:16]}-{pkg_sha[:16]}.json', raw, diff_error='Immutable architecture review package differs')
		pkg_rel = target.relative_to(pp.root).as_posix() if target.is_relative_to(pp.root) else target.as_posix()
		ReviewStore.__register_package_index(root, pkg_rel, pkg_sha, payload)
		cached = ReviewStore.__is_cached(ReviewStore.__load_index(root), subj_sha, modules)
		return {'valid': True, 'package': pkg_rel, 'package_sha256': pkg_sha, 'subject_kind': kind, 'subject_sha256': subj_sha, 'cached_approval': cached, 'module_hashes': payload['module_hashes']}
	# @used-by :func:`agent_tools.arch.review_store.read_arch_review_input()`
	# @used-by :meth:`Df.Harness.Arch.ReviewCli.ReviewCli.__exec_arch_review_input()`
	@staticmethod
	def read_review_input(root: Path, package_rel: str, *, parent_id: str | None=None, reviewer_id: str | None=None) -> dict[str, Any]:
		pp = project_paths(root, exact_root=True)
		target = inside(pp.root, package_rel)
		if not target.is_file() or not target.resolve().is_relative_to((ReviewStore.__arch_dir(root) / 'packages').resolve()):
			raise ValueError(f'Architecture review package is missing or outside ꘖ/data/arch-reviews/packages: {package_rel}')
		raw = target.read_bytes()
		pkg = json.loads(raw.decode('utf-8'))
		return {'arch_review_input': 1, 'verified': True, 'project_root': pp.root.as_posix(), 'package': target.relative_to(pp.root).as_posix(), 'package_sha256': hashlib.sha256(raw).hexdigest(), 'parent_id': parent_id or pkg.get('parent_id'), 'reviewer_id': reviewer_id, 'content': pkg}
	# @used-by :func:`agent_tools.arch.review_store.record_arch_review()`
	# @used-by :meth:`Df.Harness.Arch.ReviewCli.ReviewCli.__exec_arch_record_review()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_enforcement_preserves_gates_and_395_participants()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_evaluator_checks_response_receipts_and_runner()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_review_store_roundtrip_auth_and_patch_seam()`
	def record_review(self, report_bytes: bytes, *, parent_id: str, reviewer_id: str, native_evidence: Path | None=None, wait_timeout: float=0.0, platform: str | None=None, instance: str | None=None) -> dict[str, Any]:
		verdict = json.loads(report_bytes.decode('utf-8'))
		pkg_rel, pkg_sha, pkg = ReviewStore.__load_verified_package(self.__root, verdict)
		issues = ReviewValidator().validate(verdict, pkg, package_rel=pkg_rel, package_sha256=pkg_sha)
		if issues:
			raise ValueError('Invalid arch-auditor verdict: ' + '; '.join(issues))
		proof = self.__auth_fn(self.__root, parent_id, reviewer_id, report_bytes, Path(pkg_rel).name, native_evidence=native_evidence, wait_timeout=wait_timeout, platform=platform, instance=instance)
		v_sha = hashlib.sha256(report_bytes).hexdigest()
		pp = project_paths(self.__root, exact_root=True)
		v_path = write_immutable_bytes(ReviewStore.__arch_dir(self.__root) / 'verdicts' / f'{reviewer_id}-{v_sha[:16]}.json', report_bytes, diff_error='Immutable arch-auditor verdict differs')
		v_rel = v_path.relative_to(pp.root).as_posix() if v_path.is_relative_to(pp.root) else v_path.as_posix()
		rec_at = datetime.now(timezone.utc).isoformat()
		rev_id = f'{reviewer_id}:{v_sha[:12]}'
		cached, open_f = ReviewStore.__persist_review_index(self.__root, pkg, verdict, {'review_id': rev_id, 'parent_id': parent_id, 'reviewer_id': reviewer_id, 'package': pkg_rel, 'package_sha256': pkg_sha, 'verdict': v_rel, 'verdict_sha256': v_sha, 'result': verdict['result'], 'subject_kind': pkg['subject_kind'], 'subject_sha256': pkg['subject_sha256'], 'recorded_at': rec_at})
		return {'valid': True, 'review_id': rev_id, 'result': verdict['result'], 'verdict': v_rel, 'verdict_sha256': v_sha, 'package': pkg_rel, 'package_sha256': pkg_sha, 'cached_modules': cached, 'open_findings': open_f, 'native_proof': proof.get('proof')}
