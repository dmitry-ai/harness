# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Review.PackageReader import PackageReader
from Df.Harness.Review.ReportAuthenticator import ReportAuthenticator
from Df.Harness.Review.ReportParser import ReportParser
from Df.Harness.Review.ReportValidator import ReportValidator
from Df.Qa.lib.validation.check_strict import df_is_sne
from agent_tools.research import inside, json_data
from agent_tools.storage import write_immutable_bytes
import hashlib
_DIFF_ERR = 'Immutable review artifact differs; preserve the original and create a new attempt'
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class VerdictPreparer:
	# @used-by :func:`agent_tools.review.prepare_verdict_record()`
	# @used-by :meth:`Df.Harness.Review.VerdictRecorder.VerdictRecorder.record()`
	def __init__(self, root, report, *, parent_id: str, reviewer_id: str, native_evidence=None, allow_self: bool=True, expected_risk=None, package_reader=None, issue_checker=None, reviews_dir_fn=None, artifact_prefix_fn=None, diff_error: str=_DIFF_ERR, inside_fn=None) -> None:
		self.__root = Path(root).resolve()
		self.__report = report
		self.__parent_id = parent_id
		self.__reviewer_id = reviewer_id
		self.__native_evidence = native_evidence
		self.__allow_self = allow_self
		self.__expected_risk = expected_risk
		self.__package_reader = package_reader
		self.__issue_checker = issue_checker
		self.__reviews_dir_fn = reviews_dir_fn
		self.__artifact_prefix_fn = artifact_prefix_fn
		self.__diff_error = diff_error
		self.__inside = inside if None is inside_fn else inside_fn
	# @used-by :meth:`VerdictPreparer.prepare()`
	def __load_and_check(self) -> tuple:
		if not df_is_sne(self.__parent_id) or (not df_is_sne(self.__reviewer_id)):
			raise ValueError('Observed A.A parent/reviewer IDs are required')
		source_payload = self.__report if isinstance(self.__report, bytes) else self.__inside(self.__root, self.__report).read_bytes()
		data = ReportParser(source_payload.decode('utf-8-sig')).parse()
		pkg_path = data.get('package')
		if not df_is_sne(pkg_path):
			raise ValueError('Review report must identify its immutable package')
		package = PackageReader(self.__root, pkg_path, inside_fn=self.__inside).read_package() if None is self.__package_reader else self.__package_reader(self.__root, pkg_path)
		pkg_sha = df_sha256(self.__inside(self.__root, pkg_path).read_bytes())
		self.__verify_package_match(data, package, pkg_sha)
		candidate = self.__inside(self.__root, package['response']['file']).read_text(encoding='utf-8')
		issues = ReportValidator(package, candidate=candidate).validate(data) if None is self.__issue_checker else self.__issue_checker(data, package, candidate)
		if issues:
			raise ValueError('\n'.join(issues))
		return (source_payload, data, pkg_path, package, pkg_sha, candidate)
	# @used-by :meth:`VerdictPreparer.__load_and_check()`
	def __verify_package_match(self, data: dict, package: dict, pkg_sha: str) -> None:
		if data.get('package_sha256') != pkg_sha or package.get('parent_id') != self.__parent_id:
			raise ValueError('Reviewer package hash/parent differs')
		if None is not self.__expected_risk and self.__expected_risk != package['risk']:
			raise ValueError('Risk is fixed in the reviewed package; record-review cannot change it')
	# @used-by :meth:`VerdictPreparer.prepare()`
	def __write_artifacts(self, data: dict, pkg_sha: str, raw_payload: bytes, proof_paths: list[str]) -> tuple[str, str, str]:
		from agent_tools.path_registry import project_paths
		review_id = df_sha256((pkg_sha + '\x00' + self.__reviewer_id + '\x00' + df_sha256(raw_payload)).encode())
		folder = (project_paths(self.__root, exact_root=True).evidence_dir / 'Reviews' / pkg_sha) if None is self.__reviews_dir_fn else self.__reviews_dir_fn(self.__root, pkg_sha)
		prefix = (hashlib.sha256(self.__reviewer_id.encode()).hexdigest()[:16] + '-' + review_id) if None is self.__artifact_prefix_fn else self.__artifact_prefix_fn(self.__reviewer_id, review_id)
		report_file = write_immutable_bytes(folder / f'{prefix}-report.json', json_data(data), diff_error=self.__diff_error)
		authored_file = write_immutable_bytes(folder / f'{prefix}-authored.txt', raw_payload, diff_error=self.__diff_error)
		report_rel = report_file.relative_to(self.__root).as_posix()
		authored_rel = authored_file.relative_to(self.__root).as_posix()
		proof_paths += [report_rel, authored_rel]
		for finding in data['findings']:
			if finding.get('status') in ('resolved', 'rejected'):
				ev_items = finding['evidence'] if isinstance(finding['evidence'], list) else [finding['evidence']]
				proof_paths += [self.__inside(self.__root, item).relative_to(self.__root).as_posix() for item in ev_items]
		return (review_id, report_rel, authored_rel)
	# @used-by :func:`agent_tools.review.prepare_verdict_record()`
	# @used-by :meth:`Df.Harness.Review.VerdictRecorder.VerdictRecorder.record()`
	def prepare(self) -> dict:
		source_payload, data, pkg_path, package, pkg_sha, candidate = self.__load_and_check()
		independent, proof_paths, native, raw_payload = ReportAuthenticator(self.__root, package, pkg_path, data, source_payload, parent_id=self.__parent_id, reviewer_id=self.__reviewer_id, native_evidence=self.__native_evidence, allow_self=self.__allow_self, inside_fn=self.__inside).authenticate()
		review_id, report_rel, authored_rel = self.__write_artifacts(data, pkg_sha, raw_payload, proof_paths)
		return {'root': self.__root, 'data': data, 'package': package, 'package_path': pkg_path, 'package_sha': pkg_sha, 'candidate': candidate, 'independent': independent, 'proof_paths': proof_paths, 'native': native, 'review_id': review_id, 'report_rel': report_rel, 'authored_rel': authored_rel}
