# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Project.LabelError import LabelError
import re
_HOST_LABEL_RE = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$')
_KEBAB_SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+){2,}$')
_NON_DOMAIN_EXTS = frozenset({'css', 'csv', 'dll', 'env', 'exe', 'htm', 'html', 'jpg', 'js', 'json', 'log', 'md', 'pdf', 'php', 'png', 'ps1', 'py', 'sh', 'sql', 'svg', 'txt', 'xml', 'yaml', 'yml', 'zip'})
_TLD_RE = re.compile(r'^(?:[a-z]{2,24}|xn--[a-z0-9-]{2,59})$')
_WIN_BAD_RE = re.compile(r'[\\/:\x00-\x1f<>"|?*]')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class LabelValidator:
	# @used-by :func:`agent_tools.project_labels.validate_domain_label()`
	# @used-by :func:`agent_tools.project_labels.validate_label_safe()`
	# @used-by :func:`agent_tools.project_labels.validate_topic_label()`
	# @used-by :func:`agent_tools.upwork_project.validate_label()`
	# @used-by :meth:`Df.Harness.Project.InitLabelResolver.InitLabelResolver.__resolve_domain()`
	# @used-by :meth:`Df.Harness.Project.InitLabelResolver.InitLabelResolver.resolve()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectDirResolver.ProjectDirResolver.resolve_or_create()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_diagnostics_and_label_classes()`
	def __init__(self, value: str) -> None:
		self.__value = value
	# @used-by :meth:`LabelValidator.validate()`
	def __check_safe(self) -> str:
		v = self.__value
		if not isinstance(v, str) or (not v) or 120 < len(v) or v != v.strip().rstrip('.') or _WIN_BAD_RE.search(v):
			raise LabelError('Project name must be a Windows-safe domain or short topic, without a URL scheme')
		return v
	# @used-by :meth:`LabelValidator.validate()`
	def __reject_kebab(self, clean: str) -> None:
		if self.is_kebab(clean):
			raise LabelError(f'Machine-style lowercase kebab-case slug "{clean}" is prohibited; pass a verified --domain <host> or a human-readable --topic "<Title>" (e.g., "Magento & GA4")')
	# @used-by :func:`agent_tools.project_labels.is_kebab_slug()`
	# @used-by :meth:`LabelValidator.__reject_kebab()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_diagnostics_and_label_classes()`
	@staticmethod
	def is_kebab(value: str) -> bool:
		return isinstance(value, str) and bool(_KEBAB_SLUG_RE.fullmatch(value))
	# @used-by :func:`agent_tools.project_labels.is_valid_domain_label()`
	# @used-by :meth:`Df.Harness.Project.DomainNormalizer.DomainNormalizer.normalize()`
	# @used-by :meth:`LabelValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_diagnostics_and_label_classes()`
	@staticmethod
	def is_valid_domain(value: str) -> bool:
		r = False
		if isinstance(value, str) and 253 >= len(value) and ('.' in value) and (not any((c.isspace() for c in value))):
			low = value.lower()
			parts = low.split('.')
			if (not low.startswith('www.')) and 2 <= len(parts) and parts[-1] not in _NON_DOMAIN_EXTS and _TLD_RE.fullmatch(parts[-1]):
				r = all((bool(_HOST_LABEL_RE.fullmatch(part)) for part in parts))
		return r
	# @used-by :func:`agent_tools.project_labels.validate_domain_label()`
	# @used-by :func:`agent_tools.project_labels.validate_label_safe()`
	# @used-by :func:`agent_tools.project_labels.validate_topic_label()`
	# @used-by :func:`agent_tools.upwork_project.validate_label()`
	# @used-by :meth:`Df.Harness.Project.InitLabelResolver.InitLabelResolver.__resolve_domain()`
	# @used-by :meth:`Df.Harness.Project.InitLabelResolver.InitLabelResolver.resolve()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectDirResolver.ProjectDirResolver.resolve_or_create()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_diagnostics_and_label_classes()`
	def validate(self, *, kind: str='safe') -> str:
		clean = self.__check_safe()
		if 'domain' == kind:
			if not self.is_valid_domain(clean):
				raise LabelError(f'Invalid domain label "{clean}"; expected a verified hostname with TLD without scheme or www. (e.g., blueskypeptide.com)')
			r = clean.lower()
		else:
			self.__reject_kebab(clean)
			r = clean
		return r
