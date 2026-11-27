# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.research import dfh_inside
from Df.Harness.lib.text_claims import dfh_text_digest
from agent_tools.storage import read_addressed_json
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class SourceIntegrityChecker:
	# @used-by :func:`agent_tools.text_sources.source_integrity()`
	# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__collect_applied_files()`
	def __init__(self, root, candidate: str, reference: str) -> None:
		self.__root = root
		self.__candidate = candidate
		self.__reference = reference
	# @used-by :func:`agent_tools.text_sources.source_integrity()`
	# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__collect_applied_files()`
	def check(self) -> dict:
		root_p = Path(self.__root).resolve()
		path = dfh_inside(root_p, self.__reference)
		raw, value = read_addressed_json(path, suffix='-source.json', error_msg='Historical source receipt is failed, changed or belongs to another candidate')
		if 1 != value.get('schema_version') or True is not value.get('valid') or value.get('candidate_sha256') != dfh_text_digest(self.__candidate.encode('utf-8')):
			raise ValueError('Historical source receipt is failed, changed or belongs to another candidate')
		inputs = value.get('inputs')
		if not isinstance(inputs, dict) or not inputs:
			raise ValueError('Historical source receipt has no admitted primary inputs')
		for name, expected in inputs.items():
			if dfh_text_digest(dfh_inside(root_p, name).read_bytes()) != expected:
				raise ValueError('Historical source evidence changed: ' + name)
		return {**value, 'source_check': self.__reference, 'inputs': {**inputs, path.relative_to(root_p).as_posix(): dfh_text_digest(raw)}}
