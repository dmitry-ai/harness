# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Project.LabelError import LabelError
from Df.Harness.Project.LabelValidator import LabelValidator
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class InitLabelResolver:
	# @used-by :func:`agent_tools.project_labels.resolve_init_label()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__validate_inputs()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.initialize()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_diagnostics_and_label_classes()`
	def __init__(self, *, domain: str | None=None, topic: str | None=None, fallback_title: str | None=None, strict_domain: bool=False) -> None:
		self.__domain = domain
		self.__topic = topic
		self.__fallback_title = fallback_title
		self.__strict_domain = strict_domain
	# @used-by :meth:`InitLabelResolver.resolve()`
	def __resolve_domain(self) -> tuple[str, str, str | None]:
		clean = LabelValidator(str(self.__domain)).validate(kind='safe')
		if clean.lower().startswith('www.'):
			raise LabelError('Pass --domain without scheme or www. prefix (e.g., blueskypeptide.com)')
		if '.' in clean:
			r = (LabelValidator(clean).validate(kind='domain'), 'domain', None)
		elif self.__strict_domain:
			raise LabelError(f'Invalid domain "{clean}"; pass a hostname with a TLD via --domain or use --topic "<Title>"')
		else:
			r = (clean, 'provisional_topic', 'Non-domain value passed via --domain; recorded as provisional_topic. Prefer --topic "<Title>" when no domain is verified.')
		return r
	# @used-by :func:`agent_tools.project_labels.resolve_init_label()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__validate_inputs()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.initialize()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_diagnostics_and_label_classes()`
	def resolve(self) -> tuple[str, str, str | None]:
		if self.__domain and self.__topic:
			raise LabelError('Specify either --domain or --topic, not both')
		if self.__topic:
			r = (LabelValidator(self.__topic).validate(kind='topic'), 'provisional_topic', None)
		elif self.__domain:
			r = self.__resolve_domain()
		else:
			derived = ' '.join(re.findall(r'[\w-]+', str(self.__fallback_title or ''))[:5]).strip()
			r = (LabelValidator(derived).validate(kind='topic'), 'provisional_topic', None)
		return r