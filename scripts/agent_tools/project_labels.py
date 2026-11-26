# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Separate --domain and --topic init labels with kebab-case rejection":
# https://github.com/dmitry-ai/harness/issues/266
from __future__ import annotations
from urllib.parse import urlsplit
import re
_HOST_LABEL_RE = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$')
_KEBAB_SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+){2,}$')
_NON_DOMAIN_EXTS = frozenset({'css', 'csv', 'dll', 'env', 'exe', 'htm', 'html', 'jpg', 'js', 'json', 'log', 'md', 'pdf', 'php', 'png', 'ps1', 'py', 'sh', 'sql', 'svg', 'txt', 'xml', 'yaml', 'yml', 'zip'})
_TLD_RE = re.compile(r'^(?:[a-z]{2,24}|xn--[a-z0-9-]{2,59})$')
_WIN_BAD_RE = re.compile(r'[\\/:\x00-\x1f<>"|?*]')
class LabelValidationError(ValueError):
	pass
# @used-by :func:`validate_domain_label()`
# @used-by :func:`validate_label_safe()`
# @used-by :func:`validate_topic_label()`
def _check_safe_windows_label(value: str) -> str:
	if not isinstance(value, str) or (not value) or 120 < len(value) or value != value.strip().rstrip('.') or _WIN_BAD_RE.search(value):
		raise LabelValidationError('Project name must be a Windows-safe domain or short topic, without a URL scheme')
	return value
# @used-by :func:`validate_label_safe()`
# @used-by :func:`validate_topic_label()`
def _reject_kebab_slug(value: str) -> None:
	if is_kebab_slug(value):
		raise LabelValidationError(f'Machine-style lowercase kebab-case slug "{value}" is prohibited; pass a verified --domain <host> or a human-readable --topic "<Title>" (e.g., "Magento & GA4")')
# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
def attach_label_result(result: dict, label_kind: str, label_warning: str | None) -> dict:
	result['label_kind'] = label_kind
	if None is not label_warning:
		result['label_warning'] = label_warning
	return result
# @used-by :func:`_reject_kebab_slug()`
# @used-by :meth:`test_project_labels.ProjectLabelValidationTests.test_validate_label_and_helpers_enforce_slug_and_domain_rules()`
def is_kebab_slug(value: str) -> bool:
	return isinstance(value, str) and bool(_KEBAB_SLUG_RE.fullmatch(value))
# @used-by :func:`normalize_domain_host()`
# @used-by :func:`validate_domain_label()`
# @used-by :meth:`test_project_labels.ProjectLabelValidationTests.test_validate_label_and_helpers_enforce_slug_and_domain_rules()`
def is_valid_domain_label(value: str) -> bool:
	r = False
	if isinstance(value, str) and 253 >= len(value) and ('.' in value) and (not any((c.isspace() for c in value))):
		low = value.lower()
		parts = low.split('.')
		if (not low.startswith('www.')) and 2 <= len(parts) and parts[-1] not in _NON_DOMAIN_EXTS and _TLD_RE.fullmatch(parts[-1]):
			r = all((bool(_HOST_LABEL_RE.fullmatch(part)) for part in parts))
	return r
# @used-by :func:`agent_tools.upwork_project.run()`
def label_error_exit_code(exc: BaseException) -> int:
	return 2 if isinstance(exc, LabelValidationError) else 1
# @used-by :func:`agent_tools.project_rename.resolve_promotable_target_domain()`
def normalize_domain_host(url_or_host: str | None) -> str | None:
	r = None
	if isinstance(url_or_host, str) and url_or_host.strip():
		raw = url_or_host.strip()
		host = urlsplit(raw).hostname if '://' in raw else raw
		if isinstance(host, str) and host.strip():
			cand = host.strip().rstrip('.').lower()
			cand = cand[4:] if cand.startswith('www.') else cand
			if is_valid_domain_label(cand):
				r = cand
	return r
# @used-by :func:`agent_tools.project_rename._validate_rename_inputs()`
# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
# @used-by :meth:`test_project_labels.ProjectLabelValidationTests.test_validate_label_and_helpers_enforce_slug_and_domain_rules()`
def resolve_init_label(*, domain: str | None=None, topic: str | None=None, fallback_title: str | None=None, strict_domain: bool=False) -> tuple[str, str, str | None]:
	if domain and topic:
		raise LabelValidationError('Specify either --domain or --topic, not both')
	if topic:
		r = (validate_topic_label(topic), 'provisional_topic', None)
	elif domain:
		r = _resolve_domain_arg(domain, strict_domain=strict_domain)
	else:
		derived = ' '.join(re.findall(r'[\w-]+', str(fallback_title or ''))[:5]).strip()
		r = (validate_topic_label(derived), 'provisional_topic', None)
	return r
# @used-by :func:`resolve_init_label()`
def _resolve_domain_arg(domain: str, *, strict_domain: bool) -> tuple[str, str, str | None]:
	clean = validate_label_safe(domain)
	if clean.lower().startswith('www.'):
		raise LabelValidationError('Pass --domain without scheme or www. prefix (e.g., blueskypeptide.com)')
	if '.' in clean:
		r = (validate_domain_label(clean), 'domain', None)
	elif strict_domain:
		raise LabelValidationError(f'Invalid domain "{clean}"; pass a hostname with a TLD via --domain or use --topic "<Title>"')
	else:
		r = (clean, 'provisional_topic', 'Non-domain value passed via --domain; recorded as provisional_topic. Prefer --topic "<Title>" when no domain is verified.')
	return r
# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
def update_state_label(state: dict, root, snapshot, day, label_kind: str) -> None:
	state.update(initialized=True, snapshot=str(snapshot.relative_to(root)))
	state.setdefault('label', root.name.split(' - ', 1)[-1])
	state.setdefault('label_kind', label_kind)
	state.setdefault('request_date', day.isoformat())
# @used-by :func:`_resolve_domain_arg()`
def validate_domain_label(value: str) -> str:
	clean = _check_safe_windows_label(value)
	if not is_valid_domain_label(clean):
		raise LabelValidationError(f'Invalid domain label "{clean}"; expected a verified hostname with TLD without scheme or www. (e.g., blueskypeptide.com)')
	return clean.lower()
# @used-by :func:`_resolve_domain_arg()`
# @used-by :func:`agent_tools.upwork_project.validate_label()`
def validate_label_safe(value: str) -> str:
	clean = _check_safe_windows_label(value)
	_reject_kebab_slug(clean)
	return clean
# @used-by :func:`resolve_init_label()`
def validate_topic_label(value: str) -> str:
	clean = _check_safe_windows_label(value)
	_reject_kebab_slug(clean)
	return clean
