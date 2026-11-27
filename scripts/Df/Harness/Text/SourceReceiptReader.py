# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Text.SourceEvaluator import SourceEvaluator
from Df.Harness.lib.research import dfh_inside
from Df.Harness.lib.text_claims import dfh_text_digest
from agent_tools.storage import read_addressed_json
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class SourceReceiptReader:
	# @used-by :func:`Df.Harness.lib.text_review.dfh_source_reviews()`
	# @used-by :func:`agent_tools.text_sources.read_source_check()`
	# @used-by :meth:`Df.Harness.Text.SourceCheckValidator.SourceCheckValidator.__check_reference()`
	def __init__(self, root, candidate: str, reference: str) -> None:
		self.__root = root
		self.__candidate = candidate
		self.__reference = reference
	# @used-by :func:`Df.Harness.lib.text_review.dfh_source_reviews()`
	# @used-by :func:`agent_tools.text_sources.read_source_check()`
	# @used-by :meth:`Df.Harness.Text.SourceCheckValidator.SourceCheckValidator.__check_reference()`
	def read(self) -> dict:
		path = dfh_inside(self.__root, self.__reference)
		raw, value = read_addressed_json(path, suffix='-source.json', error_msg='Invalid or changed immutable source receipt')
		if 1 != value.get('schema_version'):
			raise ValueError('Invalid or changed immutable source receipt')
		if value.get('candidate_sha256') != dfh_text_digest(self.__candidate.encode('utf-8')) or True is not value.get('valid'):
			raise ValueError('Source receipt is failed or belongs to another candidate')
		actual = SourceEvaluator(self.__root, self.__candidate, value['spec']).evaluate()
		if any((value.get(key) != actual[key] for key in actual)):
			raise ValueError('Source bytes or provenance changed since the source receipt')
		return {**value, 'source_check': self.__reference, 'inputs': {**actual['inputs'], path.relative_to(Path(self.__root).resolve()).as_posix(): dfh_text_digest(raw)}}
