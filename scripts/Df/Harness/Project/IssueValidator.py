# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Project.ValidationError import ValidationError
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class IssueValidator:
	# @used-by :func:`agent_tools.diagnostics.require_valid()`
	# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.__validate_partial()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.sync()`
	# @used-by :meth:`Df.Harness.Analysis.Renderer.Renderer.render()`
	# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.save()`
	# @used-by :meth:`Df.Harness.Analysis.Validator.Validator.require_current_contract()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_diagnostics_and_label_classes()`
	def __init__(self, issues) -> None:
		self.__issues = issues
	# @used-by :func:`agent_tools.diagnostics.require_valid()`
	# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.__validate_partial()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.sync()`
	# @used-by :meth:`Df.Harness.Analysis.Renderer.Renderer.render()`
	# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.save()`
	# @used-by :meth:`Df.Harness.Analysis.Validator.Validator.require_current_contract()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_diagnostics_and_label_classes()`
	def require_valid(self) -> None:
		errors = [x for x in self.__issues if 'error' == x.get('severity', 'error')]
		if errors:
			raise ValidationError(errors)