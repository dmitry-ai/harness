# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.sha256 import df_sha256
from agent_tools.research import inside
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class NativeProofVerifier:
	# @used-by :func:`agent_tools.review.verify_entry_native_proof()`
	# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.__validate_entry()`
	def __init__(self, root, entry: dict, *, error_msg: str='Saved report differs from the actual native authored final response') -> None:
		self.__root = root
		self.__entry = entry
		self.__error_msg = error_msg
	# @used-by :func:`agent_tools.review.verify_entry_native_proof()`
	# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.__validate_entry()`
	def verify(self) -> dict:
		from agent_tools.metrics import verify_native_proof
		native = json.loads(inside(self.__root, self.__entry['native_evidence']).read_text(encoding='utf-8'))
		observed = verify_native_proof(self.__root, native, package=Path(self.__entry['package']).name)
		if df_sha256(inside(self.__root, self.__entry['authored_response']).read_bytes()) != observed.get('final_response_sha256'):
			raise ValueError(self.__error_msg)
		return observed
