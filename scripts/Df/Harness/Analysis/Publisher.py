# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Analysis.EvidenceAuditor import EvidenceAuditor
from Df.Harness.Analysis.OwnedPublisher import OwnedPublisher
from Df.Harness.Analysis.RedFlagSyncer import RedFlagSyncer
from Df.Harness.Analysis.Renderer import Renderer
from Df.Harness.Analysis.Validator import Validator
from Df.Harness.Project.IssueValidator import IssueValidator
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class Publisher:
	# @used-by :func:`agent_tools.analysis.publish_analysis()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__emit_validation_result()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_analysis_merger_and_lifecycle_classes()`
	def __init__(self, source, target=None) -> None:
		self.__source = Path(source).resolve()
		self.__target = target
	# @used-by :meth:`Publisher.publish()`
	def __resolve_project_root(self) -> Path:
		from agent_tools.path_registry import project_paths, resolve_project_root
		proj_root = resolve_project_root(self.__source)
		pp = project_paths(proj_root, exact_root=True)
		expected_source = (pp.kb_dir / 'Analysis.json').resolve()
		is_standard = 'Analysis.json' == self.__source.name and 'KB' == self.__source.parent.name and ('\ua616' == self.__source.parent.parent.name)
		if self.__source != expected_source and (not is_standard):
			raise ValueError('Publish a reconciled schema 3 candidate from its project \ua616/KB/Analysis.json')
		return self.__source.parents[2] if self.__source != expected_source and is_standard else proj_root
	# @used-by :func:`agent_tools.analysis.publish_analysis()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__emit_validation_result()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_analysis_merger_and_lifecycle_classes()`
	def publish(self) -> dict:
		from Df.Harness.Project.WebsiteCardSyncer import WebsiteCardSyncer
		value = json.loads(self.__source.read_text(encoding='utf-8-sig'))
		Validator.require_current_contract(value)
		proj_root = self.__resolve_project_root()
		IssueValidator(Validator(value).issues()).require_valid()
		IssueValidator(EvidenceAuditor(proj_root, value, skip_structural=True).issues()).require_valid()
		result = OwnedPublisher(self.__target or self.__source.with_suffix('.md'), Renderer(value).render(), source=self.__source).publish()
		if 'conflict' != result['status']:
			result['website_card'] = WebsiteCardSyncer(proj_root, value).sync()
			card = RedFlagSyncer(proj_root, value).sync()
			result['project_card'] = card
			if 'conflict' == card['status'] or 'conflict' == result['website_card']['status']:
				result['status'] = 'conflict'
		return result