# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import nullcontext
from pathlib import Path
from urllib.parse import urlsplit
import json
import re
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Project.Diagnostics import Diagnostics
from Df.Harness.Project.OnceFileWriter import OnceFileWriter
# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
from Df.Harness.Research.UserUrlPolicy import UserUrlPolicy
from Df.Harness.lib.project import dfh_resolve_overview_md
from Df.Harness.lib.research import dfh_readable_reference
from agent_tools.storage import locked, replace_bytes
_LEGACY_START = b'<!-- upwork-init:websites:start -->'
_LEGACY_END = b'<!-- upwork-init:websites:end -->'
_JOB_LINE_RE = re.compile(b'(?:\\r?\\n)?https://(?:www\\.)?upwork\\.com/jobs/~0\\d+(?:\\r?\\n|$)')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
class WebsiteCardSyncer:
	# @used-by :func:`agent_tools.knowledge.sync_website_card()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`Df.Harness.Project.CardSyncAuditor.CardSyncAuditor.audit()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_z_project_website_and_extra_loom_coverage()`
	# @used-by :meth:`test_upwork_card_and_red_flags.UpworkCardAndRedFlagsTests.test_bare_url_website_sync_and_legacy_migration()`
	# @used-by :meth:`test_upwork_v2_root_card.UpworkV2RootCardTests.test_legacy_v2_readme_fallback_works_across_card_consumers()`
	def __init__(self, root, value: dict, *, selections=None, check: bool=False) -> None:
		self.__root, self.__value, self.__selections, self.__check = (root, value, selections, check)
	# @used-by :meth:`WebsiteCardSyncer.__compute_bare_payload()`
	@staticmethod
	def __anchor_offset(previous: bytes) -> int:
		pos = 3 if previous.startswith(b'\xef\xbb\xbf') else 0
		if previous[pos:].startswith(b'# '):
			eol = previous.find(b'\n', pos)
			pos = eol + 1 if 0 <= eol else len(previous)
		hit = _JOB_LINE_RE.match(previous[pos:])
		if None is not hit:
			pos += hit.end()
		return pos
	# @used-by :meth:`WebsiteCardSyncer.__sync_selected()`
	def __collect_selected(self, pp, selected: list[dict]) -> tuple[list[dict], list[str]] | None:
		identities = {claim['id']: claim for claim in self.__value['identity']}
		failed = UserUrlPolicy.from_evidence_dir(pp.evidence_dir).failed_apex_hosts
		stored: list[dict] = []
		lines: list[str] = []
		r: tuple[list[dict], list[str]] | None = (stored, lines)
		for site in selected:
			claim = identities[site['basis_id']]
			sha = df_sha256(OnceFileWriter.json_bytes(claim))
			if site.get('basis_sha256', sha) != sha:
				r = None
				break
			url = site.get('url')
			if url:
				formatted = self.__format_url(url, failed)
				if formatted not in lines:
					lines.append(formatted)
			stored.append({'url': url, 'role': site['role'], 'basis_id': site['basis_id'], 'basis_sha256': sha})
		return r
	# @used-by :meth:`WebsiteCardSyncer.__sync_bare_urls()`
	@classmethod
	def __commit_result(cls, target: Path, receipt_path: Path, previous: bytes, payload: bytes, block: bytes, owned: dict | None, receipts: dict, entry: dict, *, check: bool, source, attributes, url_lines: list[str]) -> dict:
		base = {'target': str(target), 'block': 'websites'}
		sha = df_sha256(block)
		meta: dict = {'format': 'bare-urls', 'lines': list(url_lines), 'sha256': sha, 'source': str(source) if None is not source else None}
		if None is not attributes:
			meta['data'] = attributes
		changed, r_changed = (payload != previous, owned != meta)
		if check:
			r = {**base, 'status': 'stale' if changed or r_changed else 'unchanged', 'sha256': sha, 'detail': 'Read-only comparison; no files written'}
		elif (target.read_bytes() if target.exists() else b'') != previous:
			r = {**base, 'status': 'conflict', 'detail': 'Target changed during publication; external edit preserved'}
		else:
			r = cls.__write_render_files(target, receipt_path, payload, changed, r_changed, meta, receipts, entry, base, sha)
		return r
	# @used-by :meth:`WebsiteCardSyncer.__sync_bare_urls()`
	@classmethod
	def __compute_bare_payload(cls, previous: bytes, url_lines: list[str], owned: dict | None, target: Path) -> tuple[bytes | None, bytes, dict | None]:
		newline = b'\r\n' if b'\r\n' in previous else b'\n'
		block = b''.join((ln.encode('utf-8') + newline for ln in url_lines))
		base, err = cls.__strip_legacy_block(previous, newline, owned, target) if _LEGACY_START in previous or _LEGACY_END in previous else (previous, None)
		if None is not err:
			r: tuple[bytes | None, bytes, dict | None] = (None, block, err)
		else:
			anchor = cls.__anchor_offset(base)
			r = cls.__splice_bare_block(base, anchor, newline, block, owned if previous == base else None, target)
		return r
	# @used-by :meth:`WebsiteCardSyncer.__collect_selected()`
	# @used-by :meth:`WebsiteCardSyncer.sync_initial()`
	@staticmethod
	def __format_url(url: str, failed_apex_hosts: frozenset[str]) -> str:
		clean = dfh_readable_reference(UserUrlPolicy.format_card_url(url, failed_apex_hosts=failed_apex_hosts))
		return f'<{clean}>' if any((c in clean for c in ' ()')) else clean
	# @used-by :meth:`WebsiteCardSyncer.website_issues()`
	@staticmethod
	def __is_valid_url(url) -> bool:
		try:
			if not isinstance(url, str):
				raise ValueError('Website URL must be a string')
			parsed = urlsplit(url)
			r = bool(parsed.scheme in ('https', 'http') and parsed.hostname and (not parsed.username) and (not parsed.password) and (not any((c.isspace() for c in url))))
			_ = parsed.port
		except (TypeError, ValueError):
			r = False
		return r
	# @used-by :meth:`WebsiteCardSyncer.__sync_bare_urls()`
	@staticmethod
	def __read_render_state(target: Path, receipt_path: Path) -> tuple[dict, dict, dict | None, bytes, dict | None]:
		receipts, entry, owned, previous, err = ({}, {}, None, b'', None)
		try:
			raw = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {}
			if not isinstance(raw, dict) or not isinstance(raw.get(str(target), {}), dict):
				err = {'target': str(target), 'block': 'websites', 'status': 'conflict', 'detail': 'Malformed publication receipt; preserved'}
			else:
				receipts = raw
				entry = receipts.get(str(target), {})
				owned = entry.get('managed_blocks', {}).get('websites') if isinstance(entry.get('managed_blocks', {}), dict) else None
				previous = target.read_bytes() if target.exists() else b''
				previous.decode('utf-8-sig')
		except (OSError, UnicodeError, json.JSONDecodeError) as exc:
			err = {'target': str(target), 'block': 'websites', 'status': 'conflict', 'detail': f'Cannot read existing publication safely: {type(exc).__name__}'}
		return (receipts, entry, owned, previous, err)
	# @used-by :meth:`WebsiteCardSyncer.__compute_bare_payload()`
	@staticmethod
	def __splice_bare_block(base: bytes, anchor: int, newline: bytes, block: bytes, owned: dict | None, target: Path) -> tuple[bytes | None, bytes, dict | None]:
		prev_lines = owned.get('lines') if isinstance(owned, dict) and 'bare-urls' == owned.get('format') else None
		if prev_lines:
			prev_block = b''.join((ln.encode('utf-8') + newline for ln in prev_lines))
			if base[anchor:anchor + len(prev_block)] == prev_block:
				r: tuple[bytes | None, bytes, dict | None] = (base[:anchor] + block + base[anchor + len(prev_block):], block, None)
			elif block and base[anchor:anchor + len(block)] == block:
				r = (base, block, None)
			else:
				r = (None, block, {'target': str(target), 'block': 'websites', 'status': 'conflict', 'detail': 'Managed website lines were manually changed; reconcile explicitly'})
		elif block and base[anchor:anchor + len(block)] == block:
			r = (base, block, None)
		else:
			prefix = base[:anchor]
			pad = newline if block and prefix and (not prefix.endswith(newline)) else b''
			r = (prefix + pad + block + base[anchor:], block, None)
		return r
	# @used-by :meth:`WebsiteCardSyncer.__compute_bare_payload()`
	@staticmethod
	def __strip_legacy_block(previous: bytes, newline: bytes, owned: dict | None, target: Path) -> tuple[bytes, dict | None]:
		if 1 != previous.count(_LEGACY_START) or 1 != previous.count(_LEGACY_END) or previous.index(_LEGACY_START) > previous.index(_LEGACY_END):
			r: tuple[bytes, dict | None] = (previous, {'target': str(target), 'block': 'websites', 'status': 'conflict', 'detail': 'Malformed or repeated managed markers; surrounding text preserved'})
		else:
			first, last = (previous.index(_LEGACY_START), previous.index(_LEGACY_END) + len(_LEGACY_END))
			if previous[last:last + len(newline)] == newline:
				last += len(newline)
			current = previous[first:last]
			if not owned or df_sha256(current) != owned.get('sha256'):
				r = (previous, {'target': str(target), 'block': 'websites', 'status': 'conflict', 'detail': 'Managed block was manually changed or is unowned; reconcile explicitly'})
			else:
				while first >= len(newline) and previous[first - len(newline):first] == newline and previous[last:last + len(newline)] == newline:
					first -= len(newline)
				r = (previous[:first] + previous[last:], None)
		return r
	# @used-by :meth:`WebsiteCardSyncer.__sync_selected()`
	# @used-by :meth:`WebsiteCardSyncer.sync_initial()`
	@classmethod
	def __sync_bare_urls(cls, pp, target: Path, url_lines: list[str], *, check: bool, source, attributes=None) -> dict:
		with nullcontext() if check else locked(pp.data_dir / 'render.lock'):
			receipts, entry, owned, previous, err = cls.__read_render_state(target, pp.rendered_json)
			if None is not err:
				r = err
			else:
				payload, block, perr = cls.__compute_bare_payload(previous, url_lines, owned, target)
				r = perr if None is not perr else cls.__commit_result(target, pp.rendered_json, previous, payload, block, owned, receipts, entry, check=check, source=source, attributes=attributes, url_lines=url_lines)
		return r
	# @used-by :meth:`WebsiteCardSyncer.sync()`
	def __sync_selected(self, pp, overview_md: Path, selected: list[dict]) -> dict:
		issues = self.website_issues({**self.__value, 'websites': selected})
		if issues:
			raise ValueError(issues)
		built = self.__collect_selected(pp, selected)
		if None is built:
			r = {'status': 'conflict', 'target': str(overview_md), 'detail': 'Website identity evidence changed; reassess its explicit selection'}
		else:
			stored, url_lines = built
			r = self.__sync_bare_urls(pp, overview_md, url_lines, check=self.__check, source=pp.kb_dir / 'Analysis.json', attributes=stored)
		return r
	# @used-by :meth:`WebsiteCardSyncer.__commit_result()`
	@staticmethod
	def __write_render_files(target: Path, receipt_path: Path, payload: bytes, changed: bool, r_changed: bool, meta: dict, receipts: dict, entry: dict, base: dict, sha: str) -> dict:
		if changed:
			replace_bytes(target, payload)
		if target.read_bytes() != payload:
			r = {**base, 'status': 'conflict', 'detail': 'Publication read-back differs; inspect the target before retrying'}
		else:
			if r_changed:
				entry.setdefault('managed_blocks', {})['websites'] = meta
				receipts[str(target)] = entry
				replace_bytes(receipt_path, (json.dumps(receipts, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
			r = {**base, 'status': 'published' if changed else 'unchanged', 'sha256': sha}
		return r
	# 2026-11-28 "Use .md root card via v2_upwork profile": https://github.com/dmitry-ai/harness/issues/415
	# @used-by :func:`agent_tools.knowledge.sync_website_card()`
	# @used-by :meth:`Df.Harness.Analysis.Publisher.Publisher.publish()`
	# @used-by :meth:`Df.Harness.Project.CardSyncAuditor.CardSyncAuditor.audit()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_z_project_website_and_extra_loom_coverage()`
	# @used-by :meth:`test_upwork_card_and_red_flags.UpworkCardAndRedFlagsTests.test_bare_url_website_sync_and_legacy_migration()`
	# @used-by :meth:`test_upwork_v2_root_card.UpworkV2RootCardTests.test_legacy_v2_readme_fallback_works_across_card_consumers()`
	def sync(self) -> dict:
		from agent_tools.path_registry import project_paths
		pp = project_paths(self.__root, exact_root=True)
		overview_md = dfh_resolve_overview_md(pp)
		state = json.loads(pp.rendered_json.read_bytes()) if pp.rendered_json.exists() else {}
		cached = state.get(str(overview_md), {}).get('managed_blocks', {}).get('websites', {}).get('data')
		selected = self.__selections if None is not self.__selections else self.__value.get('websites', cached)
		return {'status': 'unassessed', 'target': str(overview_md)} if None is selected else self.__sync_selected(pp, overview_md, selected)
	# 2026-11-28 "Use .md root card via v2_upwork profile": https://github.com/dmitry-ai/harness/issues/415
	# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
	# @used-by :func:`agent_tools.knowledge.sync_initial_website()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	# @used-by :meth:`test_upwork_card_and_red_flags.UpworkCardAndRedFlagsTests.test_sync_initial_hypothesis_writes_bare_url_and_no_markers()`
	@classmethod
	def sync_initial(cls, root, snapshot, hypothesis=None) -> dict:
		from agent_tools.path_registry import project_paths
		pp = project_paths(root, exact_root=True)
		overview_md = dfh_resolve_overview_md(pp)
		if not hypothesis or 'website_url' not in hypothesis or None is hypothesis.get('website_url'):
			r = {'status': 'unassessed', 'target': str(overview_md)}
		else:
			url = hypothesis['website_url']
			issues = cls.website_issues({'identity': [hypothesis], 'websites': [{'url': url, 'role': 'target', 'basis_id': hypothesis.get('id')}]})
			if issues:
				raise ValueError(issues)
			failed = UserUrlPolicy.from_evidence_dir(pp.evidence_dir).failed_apex_hosts
			r = cls.__sync_bare_urls(pp, overview_md, [cls.__format_url(url, failed)], check=False, source=pp.manual_kb_dir / 'Project.md')
		return r
	# @used-by :func:`agent_tools.knowledge.website_issues()`
	# @used-by :meth:`Df.Harness.Analysis.Validator.Validator.issues()`
	# @used-by :meth:`WebsiteCardSyncer.__sync_selected()`
	# @used-by :meth:`WebsiteCardSyncer.sync_initial()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_z_project_website_and_extra_loom_coverage()`
	@classmethod
	def website_issues(cls, value: dict) -> list[dict]:
		if 'websites' not in value:
			r: list[dict] = []
		else:
			sites = value['websites']
			identities = {c['id'] for c in value.get('identity') or [] if isinstance(c, dict) and isinstance(c.get('id'), str)} if isinstance(value.get('identity'), list) else set()
			if not isinstance(sites, list) or not sites:
				r = [Diagnostics().problem('websites.list', '/websites', 'Record an evidenced website or an explicit unidentified selection')]
			else:
				r = []
				for idx, site in enumerate(sites):
					field = f'/websites/{idx}'
					if not isinstance(site, dict) or not isinstance(site.get('basis_id'), str) or site['basis_id'] not in identities or (site.get('role') not in ('client', 'target')):
						r.append(Diagnostics().problem('websites.basis', field, 'Use client/target and a current identity claim ID'))
					elif None is not site.get('url') and (not cls.__is_valid_url(site.get('url'))):
						r.append(Diagnostics().problem('websites.url', field + '/url', 'Use an HTTP(S) URL or null for an unidentified site'))
		return r
