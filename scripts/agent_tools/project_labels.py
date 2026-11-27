# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Project.DomainNormalizer import DomainNormalizer
from Df.Harness.Project.InitLabelResolver import InitLabelResolver
from Df.Harness.Project.LabelError import LabelError as LabelValidationError
from Df.Harness.Project.LabelStateUpdater import LabelStateUpdater
from Df.Harness.Project.LabelValidator import LabelValidator
# @used-by :mod:`agent_tools.project_labels`
def attach_label_result(result: dict, label_kind: str, label_warning: str | None) -> dict:
	result['label_kind'] = label_kind
	if None is not label_warning:
		result['label_warning'] = label_warning
	return result
# @used-by :meth:`test_project_labels.ProjectLabelValidationTests.test_validate_label_and_helpers_enforce_slug_and_domain_rules()`
# @used-by :mod:`agent_tools.project_labels`
def is_kebab_slug(value: str) -> bool:
	return LabelValidator.is_kebab(value)
# @used-by :meth:`test_project_labels.ProjectLabelValidationTests.test_validate_label_and_helpers_enforce_slug_and_domain_rules()`
# @used-by :mod:`agent_tools.project_labels`
def is_valid_domain_label(value: str) -> bool:
	return LabelValidator.is_valid_domain(value)
# @used-by :mod:`agent_tools.project_labels`
def label_error_exit_code(exc: BaseException) -> int:
	return 2 if isinstance(exc, LabelValidationError) else 1
# @used-by :mod:`agent_tools.project_labels`
def normalize_domain_host(url_or_host: str | None) -> str | None:
	return DomainNormalizer(url_or_host).normalize()
# @used-by :meth:`test_project_labels.ProjectLabelValidationTests.test_validate_label_and_helpers_enforce_slug_and_domain_rules()`
# @used-by :mod:`agent_tools.project_labels`
def resolve_init_label(*, domain: str | None=None, topic: str | None=None, fallback_title: str | None=None, strict_domain: bool=False) -> tuple[str, str, str | None]:
	return InitLabelResolver(domain=domain, topic=topic, fallback_title=fallback_title, strict_domain=strict_domain).resolve()
# @used-by :mod:`agent_tools.project_labels`
def update_state_label(state: dict, root, snapshot, day, label_kind: str) -> None:
	LabelStateUpdater(state, root, snapshot, day, label_kind).update()
# @used-by :mod:`agent_tools.project_labels`
def validate_domain_label(value: str) -> str:
	return LabelValidator(value).validate(kind='domain')
# @used-by :mod:`agent_tools.project_labels`
def validate_label_safe(value: str) -> str:
	return LabelValidator(value).validate(kind='safe')
# @used-by :mod:`agent_tools.project_labels`
def validate_topic_label(value: str) -> str:
	return LabelValidator(value).validate(kind='topic')
__all__ = ['LabelValidationError', 'attach_label_result', 'is_kebab_slug', 'is_valid_domain_label', 'label_error_exit_code', 'normalize_domain_host', 'resolve_init_label', 'update_state_label', 'validate_domain_label', 'validate_label_safe', 'validate_topic_label']
