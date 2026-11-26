# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Review.ReportParser import ReportParser
from Df.Qa.lib.validation.check_strict import df_is_sne
from agent_tools.research import inside
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ReportAuthenticator:
	# @used-by :func:`agent_tools.review.authenticate_report()`
	# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.prepare()`
	def __init__(self, root, package: dict, package_path: str, data: dict, source_payload: bytes, *, parent_id: str, reviewer_id: str, native_evidence=None, allow_self: bool=True, inside_fn=None) -> None:
		self.__root = root
		self.__package = package
		self.__package_path = package_path
		self.__data = data
		self.__source_payload = source_payload
		self.__parent_id = parent_id
		self.__reviewer_id = reviewer_id
		self.__native_evidence = native_evidence
		self.__allow_self = allow_self
		self.__inside = inside if None is inside_fn else inside_fn
	# @used-by :meth:`ReportAuthenticator.authenticate()`
	def __auth_independent(self, proof_paths: list[str]) -> tuple:
		from agent_tools.metrics import verify_native_proof
		if not df_is_sne(self.__native_evidence):
			raise ValueError('Independent report requires separate native_evidence proof')
		native = json.loads(self.__inside(self.__root, self.__native_evidence).read_text(encoding='utf-8'))
		if native.get('parent_id') != self.__parent_id or native.get('reviewer_id') != self.__reviewer_id or 'completed' != native.get('status'):
			raise ValueError('Saved native reviewer identity/status differs')
		observed = verify_native_proof(self.__root, native, package=Path(self.__package_path).name)
		final_response = observed.get('final_response')
		if not df_is_sne(final_response) or df_sha256(final_response.encode('utf-8')) != observed.get('final_response_sha256'):
			raise ValueError('Native adapter must provide the actual authored final response and verified hash')
		if ReportParser(final_response).parse() != self.__data:
			raise ValueError('Submitted report differs from the actual native reviewer verdict')
		proof_paths.append(self.__native_evidence)
		return (True, proof_paths, native, final_response.encode('utf-8'))
	# @used-by :meth:`ReportAuthenticator.authenticate()`
	def __auth_self(self, proof_paths: list[str]) -> tuple:
		from agent_tools.platforms import adapter
		if 'routine' != self.__package['risk']:
			raise ValueError('Significant claims default to one independent adversarial falsifier reviewer (or two independent reviewers in standard/escalation mode); self-review is prohibited')
		if not self.__allow_self or 'routine' != self.__package['risk'] or 'self_review' != self.__data.get('review_kind'):
			raise ValueError('This subject requires an independent reviewer; only explicit routine analysis self_review is allowed')
		adapter().require_current_binding(self.__root, self.__parent_id)
		native = {'model_verification': 'parent self-review; see observed execution metadata'}
		return (False, proof_paths, native, self.__source_payload)
	# @used-by :func:`agent_tools.review.authenticate_report()`
	# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.prepare()`
	def authenticate(self) -> tuple:
		proof_paths = [self.__package_path, self.__package['response']['file']]
		if self.__reviewer_id != self.__parent_id:
			r = self.__auth_independent(proof_paths)
		else:
			r = self.__auth_self(proof_paths)
		return r
