# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.RulesManifest import RulesManifest
ALLOWED_TRIGGERS = RulesManifest.ALLOWED_TRIGGERS
# @used-by :meth:`test_rules_progressive_disclosure.RulesProgressiveDisclosureTests.test_token_estimator_is_positive_and_monotonic()`
# @used-by :mod:`agent_tools.rules_manifest`
def estimate_tokens(text: str) -> int:
	return RulesManifest.estimate_tokens(text)
# @used-by :mod:`agent_tools.rules_manifest`
def inspect_shared_rule(path: Path) -> dict:
	return RulesManifest.inspect_rule(path)
# @used-by :mod:`agent_tools.rules_manifest`
def parse_rule_frontmatter(text: str) -> dict[str, str]:
	return RulesManifest.parse_frontmatter(text)
# @used-by :func:`agent_tools.configuration._loader()`
# @used-by :mod:`agent_tools.rules_manifest`
def render_codex_loader(primary: Path, local=(), *, restore_global: bool=True, display_root: Path | None=None) -> str:
	return RulesManifest.render_codex_loader(primary, local, restore_global=restore_global, display_root=display_root)
# @used-by :func:`agent_tools.cli_registry._exec_rules_audit()`
# @used-by :meth:`Df.Harness.Upwork.DoctorAuditor.DoctorAuditor.audit()`
# @used-by :meth:`test_rules_audit.RulesAuditTests.test_doctor_and_rules_audit_default_to_active_checkout_rules()`
# @used-by :mod:`agent_tools.rules_manifest`
def resolve_rules_primary(primary: str | Path | None, fallback: Path) -> Path:
	return RulesManifest.resolve_primary(primary, fallback)
# @used-by :mod:`agent_tools.rules_manifest`
def scan_shared_rules(primary: Path) -> list[dict]:
	return RulesManifest.scan_rules(primary)
# @used-by :meth:`Df.Harness.Upwork.DoctorAuditor.DoctorAuditor.audit()`
# @used-by :mod:`agent_tools.rules_manifest`
def validate_shared_rules_for_doctor(primary: Path, *, max_file_bytes: int=6000, max_always_on_bytes: int | None=24000, max_always_on_tokens: int | None=7000) -> tuple[list[Path], dict[str, int], dict]:
	return RulesManifest(primary, max_file_bytes=max_file_bytes, max_always_on_bytes=max_always_on_bytes, max_always_on_tokens=max_always_on_tokens).validate_for_doctor()
__all__ = ['ALLOWED_TRIGGERS', 'estimate_tokens', 'inspect_shared_rule', 'parse_rule_frontmatter', 'render_codex_loader', 'resolve_rules_primary', 'scan_shared_rules', 'validate_shared_rules_for_doctor']
