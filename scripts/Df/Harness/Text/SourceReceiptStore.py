# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Text.SourceEvaluator import SourceEvaluator
from Df.Harness.lib.research import dfh_json_data, dfh_readable_reference
from Df.Harness.lib.text_claims import dfh_text_digest
from Df.Harness.lib.text_sources import dfh_source_attempt, dfh_source_urls
from Df.Harness.lib.text_workflow import dfh_text_folder
from agent_tools.storage import write_immutable_bytes
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class SourceReceiptStore:
	# @used-by :func:`agent_tools.text_sources.save_source_check()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__review_source_handlers()`
	def __init__(self, root, candidate: str, spec) -> None:
		self.__root = root
		self.__candidate = candidate
		self.__spec = spec
	# @used-by :func:`agent_tools.text_sources.save_source_check()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__review_source_handlers()`
	def save(self) -> dict:
		result: dict = {'schema_version': 1, 'candidate_sha256': dfh_text_digest(self.__candidate.encode('utf-8')), 'spec': self.__spec}
		try:
			result.update(SourceEvaluator(self.__root, self.__candidate, self.__spec).evaluate(), valid=True, issues=[])
		except (OSError, ValueError, KeyError, TypeError) as exc:
			result.update(valid=False, issues=[str(exc)], inputs={})
		raw = dfh_json_data(result)
		path = write_immutable_bytes(dfh_text_folder(self.__root) / 'sources' / (dfh_text_digest(raw) + '-source.json'), raw, diff_error='Immutable source receipt differs')
		rel = path.relative_to(Path(self.__root).resolve()).as_posix()
		try:
			spec = self.__spec
			if isinstance(spec, dict) and isinstance(spec.get('url'), str) and isinstance(spec.get('evidence'), dict) and ('intake' != spec['evidence'].get('kind')) and spec['evidence'].get('observation') and (dfh_readable_reference(spec['url']) in dfh_source_urls(self.__candidate)):
				dfh_source_attempt(self.__root, self.__candidate, spec['url'], spec['evidence']['observation'], rel)
		except (OSError, ValueError, KeyError, TypeError):
			pass
		return {**result, 'source_check': rel}
