# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Analysis.EvidenceAuditor import EvidenceAuditor
from Df.Harness.Analysis.Validator import Validator
from agent_tools.research import inside, json_data
from agent_tools.storage import read_addressed_json
import json
_REVIEW_SCHEMA = 2
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class PackageEnvelopeReader:
	# @used-by :func:`agent_tools.review.read_package_envelope()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.read_package()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_package_and_recording_classes()`
	def __init__(self, root, reference, *, expected_kind=None, error_msg: str='Invalid immutable review package', inside_fn=None) -> None:
		self.__root = root
		self.__reference = reference
		self.__expected_kind = expected_kind
		self.__error_msg = error_msg
		self.__inside = inside if None is inside_fn else inside_fn
	# @used-by :func:`agent_tools.review._analysis()`
	# @used-by :meth:`Df.Harness.Review.ApprovedDigestCollector.ApprovedDigestCollector.__load_index()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__init__()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.__init__()`
	# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.__init__()`
	@staticmethod
	def load_analysis(root, *, evidence_issues_fn=None) -> dict:
		from agent_tools.path_registry import project_paths
		path = project_paths(root, exact_root=True).kb_dir / 'Analysis.json'
		value = json.loads(path.read_text(encoding='utf-8-sig'))
		if not isinstance(value, dict) or 3 != value.get('schema_version'):
			raise ValueError('New review and publication require Analysis schema 3; legacy files remain readable')
		ev_issues = EvidenceAuditor(root, value, skip_structural=True).issues() if None is evidence_issues_fn else evidence_issues_fn(root, value, skip_structural=True)
		if Validator(value).issues() or ev_issues:
			raise ValueError('Resolve Analysis schema 3 and evidence diagnostics before preparing or accepting review')
		return value
	# @used-by :func:`agent_tools.review.subject_digest()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__build_data()`
	# @used-by :meth:`PackageEnvelopeReader.read_envelope()`
	@staticmethod
	def subject_digest(package: dict) -> str:
		fields = ('project_root', 'job_id', 'requests', 'response', 'kb_inputs', 'evidence_inputs') if 'client_text' != package.get('kind') else ('project_root', 'job_id', 'requests', 'target', 'kb_inputs', 'evidence_inputs')
		extra = {} if 'client_text' != package.get('kind') else {'response_sha256': package['response']['sha256'], 'baseline_sha256': package['baseline']['sha256']}
		return df_sha256(json_data({k: package[k] for k in fields} | extra))
	# @used-by :func:`agent_tools.review.read_package_envelope()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.read_package()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_package_and_recording_classes()`
	def read_envelope(self) -> tuple:
		from agent_tools.path_registry import canonicalize_root_dir, same_project_root
		root_p = canonicalize_root_dir(self.__root)
		path = self.__inside(root_p, self.__reference)
		raw, data = read_addressed_json(path, suffix='-inputs.json', error_msg=self.__error_msg)
		if _REVIEW_SCHEMA != data.get('schema_version') or (None is not self.__expected_kind and data.get('kind') != self.__expected_kind) or (not same_project_root(data.get('project_root'), root_p)) or (data.get('subject_sha256') != self.subject_digest(data)):
			raise ValueError(self.__error_msg)
		resp = data.get('response') if isinstance(data.get('response'), dict) else {}
		candidate = self.__inside(root_p, resp.get('file', ''))
		cand_bytes = candidate.read_bytes() if candidate.is_file() else None
		if None is cand_bytes or df_sha256(cand_bytes) != resp.get('sha256') or (None is not resp.get('bytes') and len(cand_bytes) != resp.get('bytes')):
			raise ValueError('Reviewed candidate response bytes differ or are missing')
		return (root_p, raw, data, cand_bytes)
