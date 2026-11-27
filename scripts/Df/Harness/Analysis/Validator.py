# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Analysis.ClaimGraph import ClaimGraph
from Df.Harness.Analysis.RedFlagValidator import RedFlagValidator
from Df.Harness.Project.Diagnostics import Diagnostics
from Df.Harness.Project.IssueValidator import IssueValidator
import re
SECTIONS = ('identity', 'concerns', 'misconceptions', 'causes', 'methods')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class Validator:
	# @used-by :func:`agent_tools.analysis.analysis_issues()`
	# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.__validate_partial()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.sync()`
	# @used-by :meth:`Df.Harness.Analysis.Renderer.Renderer.render()`
	# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.save()`
	# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.__default_analysis()`
	# @used-by :meth:`Df.Harness.Review.PackageEnvelopeReader.PackageEnvelopeReader.load_analysis()`
	# @used-by :meth:`Df.Harness.Workflow.AnalysisCardAuditor.AnalysisCardAuditor.__init__()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_analysis_merger_and_lifecycle_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def __init__(self, value) -> None:
		self.__value = value
		self.__issues: list[dict] = []
		self.__claims: dict[str, str] = {}
		self.__references: list[tuple[str, object, str, list]] = []
	# @used-by :meth:`Validator.__check_argument()`
	# @used-by :meth:`Validator.__check_claim()`
	# @used-by :meth:`Validator.__check_claim_arguments()`
	# @used-by :meth:`Validator.__check_claim_fields()`
	# @used-by :meth:`Validator.__check_header()`
	# @used-by :meth:`Validator.__check_legacy_argument()`
	# @used-by :meth:`Validator.__check_references()`
	# @used-by :meth:`Validator.__check_section()`
	def __add(self, code: str, field: str, message: str, ident=None, hint=None) -> None:
		self.__issues.append(Diagnostics().problem(code, field, message, claim_id=ident, hint=hint))
	# @used-by :meth:`Validator.__check_claim_arguments()`
	def __check_argument(self, af: str, arg, ident, registry: dict) -> None:
		if not isinstance(arg, dict):
			self.__add('argument.object', af, 'Each argument must be an object', ident)
		elif 3 == self.__value.get('schema_version') and (arg.get('claim_id') or arg.get('evidence_id')):
			if not isinstance(arg.get('argument'), str) or not arg['argument'].strip():
				self.__add('argument.required', af + '/argument', 'argument is required', ident)
			if arg.get('claim_id') and arg.get('evidence_id'):
				self.__add('argument.source', af, 'Use one claim_id or evidence_id reference', ident)
		else:
			self.__check_legacy_argument(af, arg, ident, registry)
	# @used-by :meth:`Validator.__check_section()`
	def __check_claim(self, field: str, section: str, item, registry: dict) -> None:
		if not isinstance(item, dict):
			self.__add('claim.object', field, 'Each claim must be an object')
		else:
			ident = item.get('id')
			if not isinstance(ident, str) or not re.fullmatch('[A-Z][A-Z0-9-]*', ident) or ident in self.__claims:
				self.__add('claim.id', field + '/id', 'Invalid or duplicate claim ID', str(ident))
			else:
				self.__claims[ident] = section
			self.__check_claim_fields(field, section, item, ident)
			self.__check_claim_arguments(field, item, ident, registry)
	# @used-by :meth:`Validator.__check_claim()`
	def __check_claim_arguments(self, field: str, item: dict, ident, registry: dict) -> None:
		for side in ('for', 'against'):
			arguments = item.get(side)
			if not isinstance(arguments, list):
				self.__add('argument.list', field + '/' + side, f'{side} must be a list', ident)
			else:
				if not arguments:
					gap = item.get('counterevidence', {}) if 'against' == side else {}
					if 'against' != side or not self.__valid_gap(gap):
						self.__add('argument.empty', field + '/' + side, 'Concrete arguments required; empty against needs documented counterevidence status', ident)
				for number, arg in enumerate(arguments):
					self.__check_argument(f'{field}/{side}/{number}', arg, ident, registry)
	# @used-by :meth:`Validator.__check_claim()`
	def __check_claim_fields(self, field: str, section: str, item: dict, ident) -> None:
		for key in ('essence', 'assessment_basis') + (('criterion',) if 'methods' == section else ()):
			if not isinstance(item.get(key), str) or not item[key].strip():
				self.__add('claim.required', field + '/' + key, f'{key} is required', ident)
		score_key = 'score_percent' if 'methods' == section else 'probability_percent'
		score = item.get(score_key)
		if int is not type(score) or not 0 <= score <= 100:
			self.__add('claim.score', field + '/' + score_key, 'Assessment must be an integer from 0 to 100', ident)
		addresses = item.get('addresses', [])
		if not isinstance(addresses, list) or any((not isinstance(x, str) for x in addresses)):
			self.__add('claim.addresses', field + '/addresses', 'addresses must be a list of claim IDs', ident)
		else:
			self.__references.append((field, ident, section, addresses))
			if section in ('causes', 'methods') and (not addresses):
				self.__add('claim.addresses', field + '/addresses', 'Link causes to concerns, methods to causes/tasks', ident)
	# @used-by :meth:`Validator.issues()`
	def __check_header(self) -> tuple[dict, dict]:
		if int is not type(self.__value.get('schema_version', 1)) or self.__value.get('schema_version', 1) not in (1, 2, 3):
			self.__add('analysis.version', '/schema_version', 'Supported versions: legacy 1/2 (read only), 3 (current)')
		notes = self.__value.get('notes', {})
		if not isinstance(notes, dict):
			self.__add('analysis.notes', '/notes', 'Analysis notes must be an object')
			notes = {}
		registry = self.__value.get('sources', {})
		if not isinstance(registry, dict):
			self.__add('source.registry', '/sources', 'Sources must be an object')
			registry = {}
		for source_id, source in registry.items():
			if not isinstance(source, str) or not source.strip():
				self.__add('source.registry', f'/sources/{source_id}', 'Source ID must resolve to a nonempty source URI')
		return (notes, registry)
	# @used-by :meth:`Validator.__check_argument()`
	def __check_legacy_argument(self, af: str, arg: dict, ident, registry: dict) -> None:
		for key in ('argument', 'quote'):
			if not isinstance(arg.get(key), str) or not arg[key].strip():
				self.__add('argument.required', af + '/' + key, f'{key} is required', ident)
		source = self.__source_uri(arg, registry)
		if not isinstance(source, str) or not source.strip():
			self.__add('argument.source', af + '/source', 'Needs a source or a resolvable source_id', ident)
		if arg.get('source') and arg.get('source_id'):
			self.__add('argument.source', af, 'Use source or source_id, not two competing references', ident)
		if arg.get('documentation') and isinstance(source, str) and ('#' not in source or not source.split('#', 1)[1]):
			locator = arg.get('anchor_exception')
			if not isinstance(locator, dict) or not all((isinstance(locator.get(k), str) and locator[k].strip() for k in ('section', 'observation'))):
				self.__add('documentation.locator', af + '/anchor_exception', 'Documentation needs a section anchor or section + saved observation', ident, 'collect the page; record its section and observation URI; verify evidence')
	# @used-by :meth:`Validator.issues()`
	def __check_references(self) -> None:
		for field, ident, section, addresses in self.__references:
			for target in addresses:
				if target not in self.__claims:
					self.__add('claim.reference', field + '/addresses', f'Unknown claim reference: {target}', ident)
			allowed = ('concerns',) if 'causes' == section else ('concerns', 'causes')
			if section in ('causes', 'methods') and addresses and (not any((self.__claims.get(x) in allowed for x in addresses))):
				self.__add('claim.reference_kind', field + '/addresses', 'Reference must address a concern or applicable cause', ident)
	# @used-by :meth:`Validator.issues()`
	def __check_section(self, section: str, notes: dict, registry: dict) -> None:
		items = self.__value.get(section)
		if not isinstance(items, list):
			self.__add('analysis.section', '/' + section, f'Analysis requires list: {section}')
		else:
			if not items and (not (isinstance(notes.get(section), str) and notes[section].strip())):
				self.__add('analysis.empty', '/' + section, 'Explain what is unknown/not established in notes')
			for index, item in enumerate(items):
				self.__check_claim(f'/{section}/{index}', section, item, registry)
	# @used-by :meth:`Validator.__check_legacy_argument()`
	def __source_uri(self, argument: dict, registry: dict):
		if 'source_id' not in argument:
			r = argument.get('source')
		else:
			ident = argument.get('source_id')
			r = registry.get(ident) if isinstance(ident, str) and ident else None
		return r
	# @used-by :meth:`Validator.__check_claim_arguments()`
	def __valid_gap(self, gap) -> bool:
		return isinstance(gap, dict) and gap.get('status') in ('not_found', 'unavailable') and isinstance(gap.get('reviewed_sources'), list) and bool(gap['reviewed_sources']) and all((isinstance(x, str) and x.strip() for x in gap['reviewed_sources'])) and isinstance(gap.get('limitations'), str) and bool(gap['limitations'].strip())
	# @used-by :meth:`Validator.iter_arguments()`
	@staticmethod
	def __iter_item_args(section: str, index: int, item: dict, registry: dict):
		for side in ('for', 'against'):
			args = item.get(side)
			if isinstance(args, list):
				for number, arg in enumerate(args):
					if isinstance(arg, dict):
						yield (item.get('id'), f'/{section}/{index}/{side}/{number}', arg, Validator.source_uri(arg, registry))
	# @used-by :func:`agent_tools.analysis.analysis_issues()`
	# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.__validate_partial()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.sync()`
	# @used-by :meth:`Df.Harness.Analysis.Renderer.Renderer.render()`
	# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.save()`
	# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.__default_analysis()`
	# @used-by :meth:`Df.Harness.Review.PackageEnvelopeReader.PackageEnvelopeReader.load_analysis()`
	# @used-by :meth:`Df.Harness.Workflow.AnalysisCardAuditor.AnalysisCardAuditor.__init__()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_analysis_merger_and_lifecycle_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def issues(self) -> list[dict]:
		if not isinstance(self.__value, dict):
			r = [Diagnostics().problem('analysis.object', '/', 'Analysis must be a JSON object')]
		else:
			notes, registry = self.__check_header()
			for section in SECTIONS:
				self.__check_section(section, notes, registry)
			self.__check_references()
			from agent_tools.knowledge import website_issues
			self.__issues.extend(RedFlagValidator(self.__value, self.__claims).issues())
			self.__issues.extend(website_issues(self.__value))
			self.__issues.extend(ClaimGraph(self.__value).structural_issues())
			r = self.__issues
		return r
	# @used-by :func:`agent_tools.analysis.iter_arguments()`
	# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.__check_arguments()`
	@staticmethod
	def iter_arguments(value):
		raw_reg = value.get('sources', {})
		registry = raw_reg if isinstance(raw_reg, dict) else {}
		for section in SECTIONS:
			items = value.get(section)
			if isinstance(items, list):
				for index, item in enumerate(items):
					if isinstance(item, dict):
						yield from Validator.__iter_item_args(section, index, item, registry)
	# @used-by :func:`agent_tools.analysis.require_current_contract()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.save()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__check_prereqs()`
	@staticmethod
	def require_current_contract(value) -> None:
		IssueValidator([] if isinstance(value, dict) and 3 == value.get('schema_version') else [Diagnostics().problem('analysis.current_contract', '/schema_version', 'New saved/published analyses require schema_version 3 and explicit provenance; preserve legacy files and reconcile a candidate')]).require_valid()
	# @used-by :func:`agent_tools.analysis.source_uri()`
	# @used-by :meth:`Df.Harness.Analysis.Renderer.Renderer.__render_arg()`
	# @used-by :meth:`Validator.__iter_item_args()`
	@staticmethod
	def source_uri(argument: dict, registry: dict):
		if 'source_id' not in argument:
			r = argument.get('source')
		else:
			ident = argument.get('source_id')
			r = registry.get(ident) if isinstance(ident, str) and ident else None
		return r