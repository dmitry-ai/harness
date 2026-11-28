# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urldefrag, urlsplit
import hashlib
import html as html_lib
import json
import re
import socket
import ssl
import sys
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
BROWSER_MODES = ('auto', 'always', 'never')
HTTP_DEFAULT_ACCEPT = 'text/html,application/xhtml+xml,text/markdown;q=0.9,*/*;q=0.8'
MAX_BYTES = 16 * 1024 * 1024
METRIC_KEYS = ('uses', 'cache_hits', 'fresh_attempts', 'failed_attempts', 'http_unavailable')
PROFILES = ('html', 'shopify', 'tracking', 'document')
VOID_ELEMENTS = ('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr')
_ALLOWED_CTX_KEYS = frozenset({'session', 'egress', 'url_country', 'language', 'selected_country', 'currency', 'session_id', 'state_fingerprint'})
# @used-by :func:`dfh_extract_github_blob_lines()`
def _blob_lines_from_embedded(raw_text: str) -> list[str]:
	r: list[str] = []
	for m in re.finditer('<script[^>]*data-target=["\\\']react-app\\.embeddedData["\\\'][^>]*>(.*?)</script>', raw_text, re.I | re.S):
		try:
			emb = json.loads(m.group(1))
		except ValueError:
			continue
		payload = emb.get('payload') if isinstance(emb, dict) else None
		if isinstance(payload, dict):
			route = payload.get('codeViewBlobLayoutRoute')
			cands = (payload.get('blob'), route.get('blob') if isinstance(route, dict) else None)
			found = next((c['rawLines'] for c in cands if isinstance(c, dict) and isinstance(c.get('rawLines'), list)), None)
			if None is not found:
				r = [str(ln) for ln in found]
				break
	return r
# @used-by :func:`dfh_extract_github_blob_lines()`
def _blob_lines_from_lc(raw_text: str) -> list[str]:
	by_ln: dict[int, str] = {}
	for pat in ('<(td|div)\\b[^>]*\\bid=["\\\']LC(\\d+)["\\\'][^>]*>(.*?)</\\1>', '<(span)\\b[^>]*\\bid=["\\\']LC(\\d+)["\\\'][^>]*>(.*?)</\\1>'):
		for m_lc in re.finditer(pat, raw_text, re.I | re.S):
			ln_no = int(m_lc.group(2))
			if 1 <= ln_no <= 200000 and ln_no not in by_ln:
				by_ln[ln_no] = html_lib.unescape(re.sub('<[^>]+>', '', m_lc.group(3))).replace('\xa0', ' ').rstrip('\r\n')
		if by_ln:
			break
	return [by_ln.get(idx, '') for idx in range(1, max(by_ln) + 1)] if by_ln else []
# @used-by :func:`dfh_readable_reference()`
def _decode_readable_match(match) -> str:
	encoded = match.group()
	raw = bytes.fromhex(encoded.replace('%', ''))
	result, offset = ([], 0)
	for char in raw.decode('utf-8', errors='surrogateescape'):
		size = len(char.encode('utf-8', errors='surrogateescape')) * 3
		original = encoded[offset:offset + size]
		offset += size
		safe_ascii = char.isascii() and (char.isalnum() or char in ' -._~')
		safe_unicode = 160 <= ord(char) < 55296 or 57344 <= ord(char) <= 1114111
		result.append(char if safe_ascii or safe_unicode else original)
	return ''.join(result)
# @used-by :func:`dfh_inside()`
def _resolve_relocated_target(root: Path, target: Path) -> Path | None:
	from agent_tools.path_registry import _path_key, load_registry, same_project_root
	reg = load_registry()
	r: Path | None = None
	for anc in target.parents:
		if _path_key(anc) in reg.relocations and same_project_root(anc, root, registry=reg):
			tail = target.relative_to(anc)
			if 2 <= len(tail.parts) and '_' == tail.parts[0] and '\ua616' == tail.parts[1] and (not (root / '_').exists()):
				tail = Path(*tail.parts[1:])
			mapped = (root / tail).resolve()
			if mapped.is_relative_to(root):
				r = mapped
				break
	return r
# @used-by :func:`dfh_request_context()`
def _validate_ctx_conditions(session, egress) -> None:
	if not isinstance(session, dict) or set(session) - {'mode', 'verification', 'evidence'} or session.get('mode') not in ('normal', 'incognito', 'isolated', 'unknown'):
		raise ValueError('Session mode must distinguish normal, incognito, isolated and unknown')
	if not isinstance(egress, dict) or set(egress) - {'country', 'verification', 'evidence'} or (None is not egress.get('country') and (not re.fullmatch('[A-Z]{2}', str(egress.get('country'))))):
		raise ValueError('Egress country must be an explicit ISO country or null; URL country is separate')
	for condition in (session, egress):
		if condition.get('verification', 'unverified') not in ('verified', 'unverified'):
			raise ValueError('Context verification must be verified or unverified')
		if 'verified' == condition.get('verification') and (not condition.get('evidence')):
			raise ValueError('Verified conditions require recorded evidence; empty cookies prove no browser mode')
# @used-by :func:`agent_tools.links._bare_urls()`
# @used-by :func:`dfh_document_urls()`
# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__collect_kb_urls()`
# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__record_client_text_urls()`
# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__record_text_urls()`
# @used-by :meth:`Df.Harness.Research.LinkAuditor.LinkAuditor.__collect_block_refs()`
# @used-by :meth:`Df.Harness.Text.MechanicalProjector.MechanicalProjector.__project_links()`
def dfh_bare_urls(text: str):
	for match in re.finditer('https?://[^\\s<>`"\\x00-\\x1f]+', text):
		url = match.group().rstrip('.,;!?')
		for left, right in [('(', ')'), ('[', ']')]:
			while url.endswith(right) and url.count(right) > url.count(left):
				url = url[:-1]
		yield url
# @used-by :func:`agent_tools.research.bounded_metrics()`
# @used-by :func:`dfh_observed_use()`
def dfh_bounded_metrics(value):
	if isinstance(value, list):
		r = {'version': 2, 'totals': dfh_metric_counts(value), 'recent': value[-32:]}
	else:
		if not isinstance(value, dict) or 2 != value.get('version') or set(value.get('totals', {})) != set(METRIC_KEYS):
			raise ValueError('Unknown collector metrics format; preserve and inspect')
		r = value
	return r
# @used-by :func:`agent_tools.research.classify_network_error()`
# @used-by :meth:`Df.Harness.Research.Collector.Collector.__execute_fetch()`
# @used-by :meth:`test_df_harness_s11_wave2c_cov_research.DfHarnessS11Wave2CCovResearchTests.test_research_lib_blob_errors_relocation_and_tab()`
def dfh_classify_network_error(exc):
	cause = exc.reason if isinstance(exc, URLError) and None is not getattr(exc, 'reason', None) else exc
	if isinstance(cause, socket.gaierror):
		r = ('dns_error', False)
	elif isinstance(cause, (TimeoutError, socket.timeout)):
		r = ('tcp_timeout', None)
	elif isinstance(cause, ConnectionRefusedError):
		r = ('connection_refused', True)
	elif isinstance(cause, ssl.SSLError):
		r = ('tls_error', True)
	elif isinstance(exc, ValueError):
		r = ('value_error', None)
	else:
		r = ('network_error', None)
	return r
# @used-by :func:`agent_tools.research.compact_extraction_for_disk()`
# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.extract_file()`
# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.extract_observation()`
def dfh_compact_extraction_for_disk(data):
	out = {k: v for k, v in data.items() if 'anchor_content' != k}
	if isinstance(out.get('sections'), list):
		out['sections'] = [{k: v for k, v in h.items() if 'content' != k} for h in out['sections'] if isinstance(h, dict)]
	if 'paragraphs' in out and isinstance(out.get('text'), str) and (out.get('paragraphs') == out['text'].splitlines()):
		del out['paragraphs']
	return out
# @used-by :func:`agent_tools.links._document_urls()`
# @used-by :meth:`Df.Harness.Research.HtmlReferences.HtmlReferences.handle_data()`
# @used-by :meth:`Df.Harness.Research.LinkAuditor.LinkAuditor.__collect_authored_tokens()`
def dfh_document_urls(text: str):
	yield from dfh_bare_urls(text)
	for match in re.finditer('(?:file://|[A-Za-z]:[/\\\\])[^\\s<>`"\\x00-\\x1f]+', text):
		yield match.group().rstrip('.,;!?)')
# @used-by :func:`agent_tools.research.extract_github_blob_lines()`
# @used-by :meth:`Df.Harness.Research.ObservationBundleScanner.ObservationBundleScanner.__scan_raw_html()`
# @used-by :meth:`test_df_harness_s11_wave2c_cov_research.DfHarnessS11Wave2CCovResearchTests.test_research_lib_blob_errors_relocation_and_tab()`
def dfh_extract_github_blob_lines(raw_text: str) -> list[str]:
	r: list[str] = []
	if raw_text:
		if 'react-app.embeddedData' in raw_text:
			r = _blob_lines_from_embedded(raw_text)
		if not r and 'LC' in raw_text:
			r = _blob_lines_from_lc(raw_text)
	return r
# @used-by :func:`agent_tools.research.extractor_version()`
# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__write_cached()`
# @used-by :meth:`Df.Harness.Research.ObservationBundleScanner.ObservationBundleScanner.__scan_ext_files()`
def dfh_extractor_version() -> str:
	return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
# @used-by :func:`agent_tools.research._fingerprint()`
# @used-by :func:`dfh_request_key()`
# @used-by :meth:`Df.Harness.Research.Collector.Collector.__build_meta()`
def dfh_fingerprint(value) -> str:
	return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
# @used-by :func:`Df.Harness.lib.text_claims._collect_ref_inputs()`
# @used-by :func:`Df.Harness.lib.text_claims.dfh_registry_path()`
# @used-by :func:`agent_tools.research.inside()`
# @used-by :meth:`Df.Harness.Research.Collector.Collector.load_observation()`
# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.extract_file()`
# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.extract_observation()`
# @used-by :meth:`Df.Harness.Text.ApprovalIntegrityChecker.ApprovalIntegrityChecker.__check_entry()`
# @used-by :meth:`Df.Harness.Text.ApprovalIntegrityChecker.ApprovalIntegrityChecker.__check_native_proof()`
# @used-by :meth:`Df.Harness.Text.ApprovalIntegrityChecker.ApprovalIntegrityChecker.check()`
# @used-by :meth:`Df.Harness.Text.IntakeSourceEvaluator.IntakeSourceEvaluator.__resolve_local_source()`
# @used-by :meth:`Df.Harness.Text.IntakeSourceEvaluator.IntakeSourceEvaluator.__verify_source_file()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__add_artifact()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__collect_applied()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__verify_target_artifacts()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.reconciled_integrity()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.verify_applied_successor()`
# @used-by :meth:`Df.Harness.Text.ReviewAuthorizer.ReviewAuthorizer.__check_entry()`
# @used-by :meth:`Df.Harness.Text.ReviewAuthorizer.ReviewAuthorizer.authorize()`
# @used-by :meth:`Df.Harness.Text.ReviewPackageReader.ReviewPackageReader.read()`
# @used-by :meth:`Df.Harness.Text.SourceEvaluator.SourceEvaluator.__verify_dom_identity()`
# @used-by :meth:`Df.Harness.Text.SourceIntegrityChecker.SourceIntegrityChecker.check()`
# @used-by :meth:`Df.Harness.Text.SourceReceiptReader.SourceReceiptReader.read()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__check_gate_response()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__collect_protected()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__gate_applied_receipt()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__gate_target()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__validate_target_and_protected()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.document()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.read_check()`
# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__check_replay()`
# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__collect_target_and_lint_issues()`
# @used-by :meth:`test_df_harness_s11_wave2c_cov_research.DfHarnessS11Wave2CCovResearchTests.test_research_lib_blob_errors_relocation_and_tab()`
def dfh_inside(root, relative) -> Path:
	root_p = Path(root).resolve()
	target = (root_p / relative).resolve()
	if target.is_relative_to(root_p):
		r = target
	else:
		rel_p = Path(relative)
		mapped = _resolve_relocated_target(root_p, target) if rel_p.is_absolute() and (not target.exists()) else None
		if None is mapped:
			raise ValueError(f'Path escapes project: {relative}')
		r = mapped
	return r
# @used-by :func:`Df.Harness.lib.text_sources._write_attempt_if_newer()`
# @used-by :func:`agent_tools.research.json_data()`
# @used-by :func:`dfh_observed_use()`
# @used-by :meth:`Df.Harness.Research.Collector.Collector.__persist_fresh()`
# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__write_cached()`
# @used-by :meth:`Df.Harness.Text.ClaimRegistryStore.ClaimRegistryStore.save()`
# @used-by :meth:`Df.Harness.Text.ReviewPreparer.ReviewPreparer.prepare()`
# @used-by :meth:`Df.Harness.Text.ReviewRecorder.ReviewRecorder.record()`
# @used-by :meth:`Df.Harness.Text.SourceProber.SourceProber.probe()`
# @used-by :meth:`Df.Harness.Text.SourceReceiptStore.SourceReceiptStore.save()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__ensure_workspace_identity()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__persist_applied()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__reconcile_if_changed()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.begin()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.save_index()`
# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__check_replay()`
# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.__persist_check()`
def dfh_json_data(value) -> bytes:
	return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
# @used-by :func:`agent_tools.links.markdown_link()`
def dfh_markdown_link(label: str | None, target: str | Path) -> str:
	target_s = dfh_readable_reference(target)
	if any((char in target_s for char in '\r\n<>')):
		raise ValueError('A document link cannot contain line endings or literal angle brackets')
	text = (target_s if None is label else label).replace('\\', '\\\\').replace('[', '\\[').replace(']', '\\]')
	destination = f'<{target_s}>' if any((char.isspace() or char in '()' for char in target_s)) else target_s
	return f'[{text}]({destination})'
# @used-by :func:`agent_tools.research.metric_counts()`
# @used-by :func:`dfh_bounded_metrics()`
# @used-by :func:`dfh_observed_use()`
def dfh_metric_counts(events) -> dict[str, int]:
	return dict(zip(METRIC_KEYS, (len(events), sum((True is x.get('cached') for x in events)), sum((False is x.get('cached') for x in events)), sum((bool(x.get('error')) for x in events)), sum(('http' == x.get('kind') and 400 <= (x.get('status') or 0) for x in events)))))
# @used-by :func:`agent_tools.research.observation_capabilities()`
def dfh_observation_capabilities(meta) -> set[str]:
	if meta.get('error'):
		r: set[str] = set()
	elif 'http' == meta.get('kind') and 'GET' == meta.get('method') and (200 <= (meta.get('status') or 0) < 300):
		r = {'content', 'markup', 'platform_capability'}
	elif 'dom' == meta.get('kind') and 'READ_DOM' == meta.get('method'):
		r = {'content', 'markup', 'dom', 'platform_capability'}
	else:
		r = set()
	return r
# @used-by :func:`agent_tools.research.observed_use()`
# @used-by :meth:`Df.Harness.Research.Collector.Collector.__persist_fresh()`
# @used-by :meth:`Df.Harness.Research.Collector.Collector.__try_cached()`
def dfh_observed_use(root, result):
	from agent_tools.path_registry import project_paths
	from agent_tools.storage import locked, replace_bytes
	pp = project_paths(root, exact_root=True)
	path = pp.metrics_json
	event = {k: result.get(k) for k in ('url', 'cached', 'observation', 'status', 'error', 'kind', 'request_key')}
	event['time'] = datetime.now(timezone.utc).isoformat(timespec='microseconds')
	with locked(pp.data_dir / 'research-metrics.lock'):
		value = dfh_bounded_metrics(json.loads(path.read_text(encoding='utf-8')) if path.exists() else [])
		counts = dfh_metric_counts([event])
		value['totals'] = {key: value['totals'][key] + counts[key] for key in METRIC_KEYS}
		value['recent'] = (value['recent'] + [event])[-32:]
		replace_bytes(path, dfh_json_data(value))
	return result
# @used-by :func:`Df.Harness.lib.markdown.dfh_display_address()`
# @used-by :func:`Df.Harness.lib.text_sources.dfh_source_attempt()`
# @used-by :func:`Df.Harness.lib.text_sources.dfh_source_urls()`
# @used-by :func:`agent_tools.links.readable_reference()`
# @used-by :func:`dfh_markdown_link()`
# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.__format_url()`
# @used-by :meth:`Df.Harness.Research.LinkAuditor.LinkAuditor.readable_link_issues()`
# @used-by :meth:`Df.Harness.Text.IntakeSourceEvaluator.IntakeSourceEvaluator.__resolve_local_source()`
# @used-by :meth:`Df.Harness.Text.IntakeSourceEvaluator.IntakeSourceEvaluator.evaluate()`
# @used-by :meth:`Df.Harness.Text.SourceEvaluator.SourceEvaluator.__check_freshness()`
# @used-by :meth:`Df.Harness.Text.SourceEvaluator.SourceEvaluator.__validate_http_ref()`
# @used-by :meth:`Df.Harness.Text.SourceEvaluator.SourceEvaluator.__validate_spec()`
# @used-by :meth:`Df.Harness.Text.SourceEvaluator.SourceEvaluator.evaluate()`
# @used-by :meth:`Df.Harness.Text.SourceReceiptStore.SourceReceiptStore.save()`
def dfh_readable_reference(value: str | Path) -> str:
	text = value.as_posix() if isinstance(value, Path) else value
	base, fragment_sep, fragment = text.partition('#')
	path, query_sep, query = base.partition('?')
	if path.lower().startswith('file:'):
		parsed = urlsplit(path)
		path = parsed.path
		if parsed.netloc and 'localhost' != parsed.netloc:
			path = '//' + parsed.netloc + path
		elif re.match('^/[A-Za-z]:/', path):
			path = path[1:]
	return re.sub('(?:%[0-9a-fA-F]{2})+', _decode_readable_match, path) + query_sep + query + fragment_sep + re.sub('(?:%[0-9a-fA-F]{2})+', _decode_readable_match, fragment)
# @used-by :func:`agent_tools.research.request_context()`
# @used-by :func:`dfh_request_key()`
# @used-by :meth:`Df.Harness.Research.Collector.Collector.__prepare_headers_and_keys()`
def dfh_request_context(value=None) -> dict:
	if None is value:
		r = {'session': {'mode': 'unknown', 'verification': 'unverified'}, 'egress': {'country': None, 'verification': 'unverified'}}
	else:
		if not isinstance(value, dict):
			raise ValueError('Request context must be an object')
		if set(value) - _ALLOWED_CTX_KEYS:
			raise ValueError('Context accepts explicit session/geography/state conditions, not credentials')
		result = json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
		session = result.setdefault('session', {'mode': 'unknown', 'verification': 'unverified'})
		egress = result.setdefault('egress', {'country': None, 'verification': 'unverified'})
		_validate_ctx_conditions(session, egress)
		for key in _ALLOWED_CTX_KEYS - {'session', 'egress'}:
			if key in result and (not isinstance(result[key], str) or not result[key].strip()):
				raise ValueError('Explicit context fields must be nonempty strings')
		r = result
	return r
# @used-by :func:`agent_tools.research.request_key()`
# @used-by :meth:`Df.Harness.Research.Collector.Collector.__prepare_headers_and_keys()`
def dfh_request_key(url, headers, scope, context=None) -> tuple[str, str]:
	clean_url = urldefrag(url)[0]
	parsed = urlsplit(clean_url)
	if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or any((c.isspace() for c in clean_url)):
		raise ValueError('A valid HTTP(S) URL without embedded credentials is required')
	_ = parsed.port
	normalized = {k.lower(): str(v) for k, v in headers.items()}
	return (clean_url, dfh_fingerprint({'url': clean_url, 'method': 'GET', 'headers': normalized, 'scope': scope, 'context': dfh_request_context(context)}))
# @used-by :meth:`Df.Harness.Research.Collector.Collector.__execute_fetch()`
# @used-by :meth:`Df.Harness.Research.Collector.Collector.fetch()`
# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__extract_docx()`
# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__write_cached()`
# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.extract_file()`
# @used-by :meth:`Df.Harness.Research.ObservationBundleScanner.ObservationBundleScanner.__scan_raw_response()`
def dfh_research_max_bytes() -> int:
	mod = sys.modules.get('agent_tools.research')
	val = getattr(mod, 'MAX_BYTES', MAX_BYTES) if None is not mod else MAX_BYTES
	return int(val)
# @used-by :meth:`Df.Harness.Research.Collector.Collector.__execute_fetch()`
# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__write_cached()`
# @used-by :meth:`Df.Harness.Research.ObservationBundleScanner.ObservationBundleScanner.__scan_ext_files()`
def dfh_research_seam(name: str, default_fn, *, module_name: str='agent_tools.research'):
	mod = sys.modules.get(module_name)
	cand = getattr(mod, name, None) if None is not mod else None
	return cand if callable(cand) and (True is not getattr(cand, '_df_default_research_facade', False)) else default_fn
# @used-by :func:`agent_tools.research.select_dom_tab()`
# @used-by :meth:`test_df_harness_s11_wave2c_cov_research.DfHarnessS11Wave2CCovResearchTests.test_research_lib_blob_errors_relocation_and_tab()`
def dfh_select_dom_tab(tabs, url, tab_id):
	matches = [t for t in tabs if 'page' == t.get('type') and t.get('id') == tab_id and (urldefrag(t.get('url', ''))[0] == urldefrag(url)[0])]
	if 1 != len(matches):
		raise ValueError('Explicit tab ID must match the exact requested URL; no navigation or account fallback')
	return matches[0]
