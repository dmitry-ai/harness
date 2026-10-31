# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from . import journal
from .platforms import adapter
from .runtime import PRIMARY, platform_name, settings
from .storage import create_bytes, data_dir_for, locked, replace_bytes
COMMANDS = ('turn-begin', 'answer-prepare', 'recover-checkpoint', 'journal-sync', 'journal-watch', 'journal-unwatch')
RULES = {'FILE-3': ('rules/01-file-boundaries.md', 'file-3'), 'EXEC-5': ('rules/08-execution-and-tools.md', 'exec-5'), 'DOC-2': ('rules/04-statement-structure.md', 'doc-2')}
RULE_REQUIREMENTS = {'FILE-3': 'Before publication, the primary agent saves the exact request and complete final response via answer-prepare.', 'EXEC-5': 'Run read-only Git checks with `--no-optional-locks` to avoid updating the index as a side effect.', 'DOC-2': 'Frame any unknown or unproven explanation as a hypothesis with arguments for/against and an expert score in %.'}
def _now():
	return datetime.now(timezone.utc).isoformat()
def _hash(value):
	return hashlib.sha256(value).hexdigest()
def _json(value):
	return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
def _read(path):
	value = json.loads(path.read_bytes().decode('utf-8'))
	if not isinstance(value, dict):
		raise ValueError('Completion metadata must be a JSON object: ' + str(path))
	r = value
	return r
def _folder(root):
	return data_dir_for(root) / 'turns'
def _directory(root, selected=None):
	root = Path(root).resolve()
	if selected:
		r = (root / selected).resolve()
	elif (root / '_/ꙮ').is_dir():
		r = (root / '_/ꙮ').resolve()
	elif (root / 'ꙮ/1 - \u0410\u043d\u0430\u043b\u0438\u0437').is_dir() and (not (root / 'ꙮ/1 - Analysis').is_dir()):
		r = (root / 'ꙮ/1 - \u0410\u043d\u0430\u043b\u0438\u0437').resolve()
	elif (root / 'ꙮ/README.md').is_file() and (not (root / 'ꙮ/1 - Analysis').is_dir()):
		r = (root / 'ꙮ').resolve()
	else:
		r = (root / 'ꙮ/1 - Analysis').resolve()
	return r
def _key(native, turn):
	identity = [native['platform'], native['native_backend'], native['conversation_id'], turn['turn_id']]
	r = _hash(_json(identity))[:40]
	return r
def _native(root, conversation=None, *, platform=None, backend=None):
	platform = platform_name(platform)
	conversation = conversation or (os.environ.get('CODEX_THREAD_ID') if 'codex' == platform else None)
	if not conversation:
		raise ValueError('Select the actual current native conversation; no summary or neighbouring chat fallback')
	r = adapter(platform).native_answers(Path(root).resolve(), conversation, backend=backend)
	return r
def _policy():
	return {ident: {'source': relative, 'anchor': anchor, 'sha256': _hash((PRIMARY / relative).read_bytes()), 'requirement': RULE_REQUIREMENTS[ident]} for ident, (relative, anchor) in RULES.items()}
def _exec5_status(turn):
	violations = list(turn.get('exec5_violations') or [])
	r = {'verified': not violations, 'violations': violations}
	return r
def _http_fetch_status(turn):
	violations = list(turn.get('http_fetch_violations') or [])
	r = {'verified': not violations, 'violations': violations}
	return r
def _compaction_status(root, key, turn):
	comp = dict(turn.get('compaction') or {})
	occurred = bool(comp.get('occurred'))
	last_cp = comp.get('last_checkpoint_step')
	pre_steps = list(comp.get('pre_checkpoint_tool_steps') or [])
	post_rec = list(comp.get('post_checkpoint_recovery_steps') or [])
	recovered_in_trace = bool(comp.get('recovered_in_trace', True))
	receipt_path = _folder(root) / f'{key}-checkpoint-recovery.json'
	recovered_via_receipt = False
	if receipt_path.is_file():
		try:
			rec_data = _read(receipt_path)
			cov = rec_data.get('covered_checkpoint_step')
			if None is last_cp or (isinstance(cov, int) and cov >= last_cp):
				recovered_via_receipt = True
		except (OSError, ValueError):
			pass
	verified = bool(not occurred or not pre_steps or recovered_in_trace or recovered_via_receipt)
	r = {'verified': verified, 'occurred': occurred, 'checkpoint_steps': list(comp.get('checkpoint_steps') or []), 'last_checkpoint_step': last_cp, 'pre_checkpoint_tool_steps': pre_steps, 'post_checkpoint_recovery_steps': post_rec, 'recovered_in_trace': recovered_in_trace, 'recovered_via_receipt': recovered_via_receipt}
	return r
DEL_MAX_UNPERSISTED_STEPS = 40
def _delegation_status(root, turn):
	del_info = dict(turn.get('delegation') or {})
	tool_steps = int(del_info.get('tool_step_count') or 0)
	sub_steps = int(del_info.get('subagent_step_count') or 0)
	kb_steps = int(del_info.get('kb_persistence_step_count') or 0)
	is_upwork_project = (Path(root).resolve() / 'ꘖ/project.json').is_file()
	unpersisted_bulk = bool(is_upwork_project and tool_steps > DEL_MAX_UNPERSISTED_STEPS and (0 == sub_steps) and (0 == kb_steps))
	r = {'verified': not unpersisted_bulk, 'tool_step_count': tool_steps, 'subagent_step_count': sub_steps, 'kb_persistence_step_count': kb_steps, 'max_unpersisted_steps': DEL_MAX_UNPERSISTED_STEPS}
	return r
def _norm_url(url: str) -> str:
	from urllib.parse import urldefrag
	r = urldefrag(url.strip())[0].rstrip('/')
	return r
def _discourse_topic_key(url: str):
	m = re.match('^https?://([^/:?#]+)/t/(?:[^/?#]+/)?(\\d+)(?:$|[/?#])', url.strip(), re.I)
	r = (m.group(1).lower(), m.group(2)) if m else None
	return r
def _is_descriptive_title_label(label: str, href: str) -> bool:
	from urllib.parse import urlsplit
	text = (label or '').strip()
	if not text or text.lower().startswith(('http://', 'https://', 'file:')):
		r = False
	else:
		host = (urlsplit(href).hostname or '').lower()
		if text.lower() in (host, f'www.{host}'):
			r = False
		else:
			words = re.findall('[A-Za-z\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u04510-9]{2,}', text)
			if len(words) < 3 or len(text) < 15:
				r = False
			else:
				r = True
	return r
def _titles_compatible(claimed: str, observed: str) -> bool:
	c_tokens = [w for w in re.findall('[a-z\\u0430-\\u044f\\u04510-9]+', claimed.lower()) if len(w) >= 3]
	o_tokens = [w for w in re.findall('[a-z\\u0430-\\u044f\\u04510-9]+', observed.lower()) if len(w) >= 3]
	if not c_tokens or not o_tokens:
		r = True
	else:
		c_str = ' '.join(c_tokens)
		o_str = ' '.join(o_tokens)
		if c_str in o_str or o_str in c_str:
			r = True
		else:
			c_set, o_set = (set(c_tokens), set(o_tokens))
			overlap = len(c_set & o_set) / max(1, len(c_set))
			r = overlap >= 0.6
	return r
def _ingest_json_observations(parsed, default_host, observed_urls, observed_topics, observed_titles, observed_topic_titles):
	from urllib.parse import urlsplit
	if not isinstance(parsed, dict):
		return
	if isinstance(parsed.get('title'), str) and parsed['title'].strip():
		t = ' '.join(parsed['title'].split())
		u = parsed.get('url')
		if isinstance(u, str) and u.startswith(('http://', 'https://')):
			nu = _norm_url(u)
			observed_urls.add(nu)
			observed_titles.setdefault(nu, t)
		if default_host and isinstance(parsed.get('id'), int):
			tk = (default_host.lower(), str(parsed['id']))
			observed_topics.add(tk)
			observed_topic_titles.setdefault(tk, t)
	topics = []
	if isinstance(parsed.get('topic_list'), dict) and isinstance(parsed['topic_list'].get('topics'), list):
		topics.extend(parsed['topic_list']['topics'])
	if isinstance(parsed.get('topics'), list):
		topics.extend(parsed['topics'])
	for topic in topics:
		if not isinstance(topic, dict) or not isinstance(topic.get('id'), int) or (not isinstance(topic.get('title'), str)):
			continue
		t = ' '.join(topic['title'].split())
		tid = str(topic['id'])
		host = default_host
		u = topic.get('url')
		if isinstance(u, str) and u.startswith(('http://', 'https://')):
			nu = _norm_url(u)
			observed_urls.add(nu)
			observed_titles.setdefault(nu, t)
			host = host or (urlsplit(nu).hostname or '')
		if host:
			tk = (host.lower(), tid)
			observed_topics.add(tk)
			observed_topic_titles.setdefault(tk, t)
			short_u = f'https://{host.lower()}/t/{tid}'
			observed_urls.add(short_u)
			observed_titles.setdefault(short_u, t)
			slug = topic.get('slug')
			if isinstance(slug, str) and slug:
				slug_u = f'https://{host.lower()}/t/{slug}/{tid}'
				observed_urls.add(slug_u)
				observed_titles.setdefault(slug_u, t)
def response_source_and_kb_issues(root: Path, response: str, requests: list[dict]) -> list[str]:
	from urllib.parse import urlsplit
	from markdown_it import MarkdownIt
	from .links import readable_link_issues, _bare_urls
	root = Path(root).resolve()
	errors = list(readable_link_issues(response, allow_unencoded_file_uri=True))
	parser = MarkdownIt('commonmark', {'html': True})
	parser.normalizeLink = lambda value: value
	parser.validateLink = lambda value: True
	authored_links = []
	authored_urls = []
	quote_depth = 0
	for block in parser.parse(response):
		if 'blockquote_open' == block.type:
			quote_depth += 1
		elif 'blockquote_close' == block.type:
			quote_depth -= 1
		if quote_depth or block.type in ('fence', 'code_block'):
			continue
		children = block.children or []
		idx = 0
		while idx < len(children):
			token = children[idx]
			if 'link_open' == token.type:
				href = token.attrGet('href') or ''
				label_parts = []
				idx += 1
				depth = 1
				while idx < len(children) and depth > 0:
					inner = children[idx]
					if 'link_open' == inner.type:
						depth += 1
					elif 'link_close' == inner.type:
						depth -= 1
					elif depth > 0 and inner.type in ('text', 'code_inline'):
						label_parts.append(inner.content)
					idx += 1
				label = ' '.join(''.join(label_parts).split())
				if href.startswith(('http://', 'https://')):
					authored_links.append((label, href))
					authored_urls.append(href)
				continue
			elif 'text' == token.type:
				for u in _bare_urls(token.content):
					if u.startswith(('http://', 'https://')):
						authored_urls.append(u)
			idx += 1
	if not authored_urls:
		r = errors
	else:
		observed_urls = set()
		observed_topics = set()
		observed_titles = {}
		observed_topic_titles = {}
		ev_dir = root / 'ꘖ/KB/Evidence'
		if ev_dir.is_dir():
			for jfile in ev_dir.rglob('*.json'):
				try:
					if jfile.stat().st_size > 4 * 1024 * 1024:
						continue
					data = json.loads(jfile.read_text(encoding='utf-8'))
				except (OSError, ValueError):
					continue
				if 'observation.json' == jfile.name and isinstance(data, dict):
					urls_here = [u for u in (data.get('url'), data.get('final_url')) if isinstance(u, str) and u.startswith(('http://', 'https://'))]
					host = (urlsplit(urls_here[0]).hostname or '').lower() if urls_here else ''
					for u in urls_here:
						nu = _norm_url(u)
						observed_urls.add(nu)
						tk = _discourse_topic_key(nu)
						if tk:
							observed_topics.add(tk)
					for ext_file in jfile.parent.glob('extracted-*.json'):
						try:
							ext = json.loads(ext_file.read_text(encoding='utf-8'))
						except (OSError, ValueError):
							continue
						t = (ext.get('title') or '').strip() if isinstance(ext, dict) else ''
						if not t and isinstance(ext, dict) and isinstance(ext.get('headings'), list):
							h1s = [h.get('text', '').strip() for h in ext['headings'] if isinstance(h, dict) and 1 == h.get('level') and h.get('text')]
							if h1s:
								t = h1s[0]
						if t:
							for u in urls_here:
								nu = _norm_url(u)
								observed_titles.setdefault(nu, t)
								tk = _discourse_topic_key(nu)
								if tk:
									observed_topic_titles.setdefault(tk, t)
					resp_bin = jfile.parent / 'response.bin'
					if resp_bin.is_file():
						try:
							if resp_bin.stat().st_size <= 2 * 1024 * 1024:
								raw_text = resp_bin.read_bytes().decode(data.get('charset') or 'utf-8', errors='replace')
								ctype = (data.get('content_type') or '').lower()
								if 'html' in ctype or '<title' in raw_text[:4000].lower():
									m_t = re.search('<title[^>]*>(.*?)</title>', raw_text[:16000], re.I | re.S)
									if m_t:
										t = ' '.join(m_t.group(1).split())
										if t:
											for u in urls_here:
												nu = _norm_url(u)
												observed_titles.setdefault(nu, t)
												tk = _discourse_topic_key(nu)
												if tk:
													observed_topic_titles.setdefault(tk, t)
								if 'json' in ctype or raw_text.lstrip().startswith('{'):
									_ingest_json_observations(json.loads(raw_text), host, observed_urls, observed_topics, observed_titles, observed_topic_titles)
						except (OSError, ValueError):
							pass
				elif isinstance(data, dict):
					src_u = data.get('url') or data.get('source') or ''
					host = (urlsplit(src_u).hostname or '').lower() if isinstance(src_u, str) and src_u.startswith(('http://', 'https://')) else ''
					_ingest_json_observations(data, host, observed_urls, observed_topics, observed_titles, observed_topic_titles)
		for label, href in authored_links:
			if not _is_descriptive_title_label(label, href):
				continue
			nu = _norm_url(href)
			tk = _discourse_topic_key(nu)
			obs_title = observed_titles.get(nu) or (observed_topic_titles.get(tk) if tk else None)
			if obs_title and (not _titles_compatible(label, obs_title)):
				errors.append(f'VERIFY-1 / LINK-1: Link title "{label}" for {href} contradicts saved observation title "{obs_title}"')
		is_upwork_project = (root / 'ꘖ/project.json').is_file() and (root / 'ꘖ/KB').is_dir()
		if is_upwork_project:
			kb_urls = set()
			kb_topics = set()
			client_urls = set()
			for req in requests or []:
				for u in _bare_urls(req.get('text', '') if isinstance(req, dict) else str(req)):
					nu = _norm_url(u)
					kb_urls.add(nu)
					client_urls.add(nu)
			for pfile in (root / 'ꘖ/project.json', root / 'KB/Project.md', root / 'ꘖ/KB/Project.md'):
				if pfile.is_file():
					try:
						txt = pfile.read_text(encoding='utf-8')
						for u in _bare_urls(txt):
							nu = _norm_url(u)
							kb_urls.add(nu)
							client_urls.add(nu)
					except OSError:
						pass
			for kb_file in list((root / 'ꘖ/KB').rglob('*.md')) + (list((root / 'KB').rglob('*.md')) if (root / 'KB').is_dir() else []):
				try:
					txt = kb_file.read_text(encoding='utf-8')
				except OSError:
					continue
				for u in _bare_urls(txt):
					nu = _norm_url(u)
					kb_urls.add(nu)
					tk = _discourse_topic_key(nu)
					if tk:
						kb_topics.add(tk)
			analysis_file = root / 'ꘖ/KB/Analysis.json'
			if analysis_file.is_file():
				try:
					txt = analysis_file.read_text(encoding='utf-8')
					for u in _bare_urls(txt):
						nu = _norm_url(u)
						kb_urls.add(nu)
						tk = _discourse_topic_key(nu)
						if tk:
							kb_topics.add(tk)
				except OSError:
					pass
			for u in dict.fromkeys(authored_urls):
				nu = _norm_url(u)
				tk = _discourse_topic_key(nu)
				if nu not in kb_urls and (not tk or tk not in kb_topics):
					errors.append(f'KB-1 / KB-3: External URL in response is missing from ꘖ/KB modules/Analysis.json (record verified sources in ꘖ/KB before answer-prepare): {u}')
			for label, href in authored_links:
				if not _is_descriptive_title_label(label, href):
					continue
				nu = _norm_url(href)
				tk = _discourse_topic_key(nu)
				if nu in client_urls:
					continue
				if nu not in observed_urls and (not tk or tk not in observed_topics):
					errors.append(f'VERIFY-1 / KB-3: External article link [{label}]({href}) has no saved observation in ꘖ/KB/Evidence/HTTP or ꘖ/KB/Evidence')
		r = errors
	return r
def _instruction_snapshot(root, native, *, stage):
	from .configuration import _project_rule_paths
	root = Path(root).resolve()
	sources = {path: 'canonical' for path in sorted((PRIMARY / 'rules').glob('*.md'))}
	sources.update({PRIMARY / 'runtime.json': 'runtime', PRIMARY / 'platforms' / (native['platform'] + '.md'): 'adapter'})
	errors = []
	manifest = root / '.agents/rules.json'
	if manifest.exists():
		sources[manifest] = 'project-registration'
	try:
		sources.update({path: 'project-rule' for path in _project_rule_paths(root, PRIMARY)})
	except (OSError, ValueError) as exc:
		errors.append(str(exc))
	if 'codex' == native['platform']:
		workspace = Path(settings()['workspace_root']).resolve()
		folders = [root]
		if root.is_relative_to(workspace):
			folders += [parent for parent in root.parents if parent == workspace or parent.is_relative_to(workspace)]
		folders.append(Path(native['native_backend']))
		for folder in folders:
			for name in ('AGENTS.md', 'AGENTS.override.md'):
				path = folder / name
				if path.is_file():
					sources[path] = 'native-guidance-candidate'
	files = []
	for path, kind in sorted(sources.items(), key=lambda item: str(item[0])):
		try:
			files.append({'path': str(path.resolve()), 'kind': kind, 'sha256': _hash(path.read_bytes())})
		except OSError as exc:
			errors.append(str(exc))
	r = {'captured_at': _now(), 'capture_stage': stage, 'sources': files, 'errors': errors, 'selection_verified': False, 'delivery_to_model_verified': False}
	return r
def _new(root, native, turn, *, recovered=False, journal_directory=None):
	key = _key(native, turn)
	r = {'schema_version': 1, 'key': key, 'project_root': str(Path(root).resolve()), 'platform': native['platform'], 'native_backend': native['native_backend'], 'conversation_id': native['conversation_id'], 'native_turn_id': turn['turn_id'], 'native_start_step': turn['start_step'], 'requests': turn['requests'], 'role': 'primary', 'journal_required': True, 'journal': str(_directory(root, journal_directory)), 'applicable_rules': _policy(), 'git_optional_locks_env': os.environ.setdefault('GIT_OPTIONAL_LOCKS', '0'), 'exec5_check': _exec5_status(turn), 'http_fetch_check': _http_fetch_status(turn), 'compaction_check': _compaction_status(root, key, turn), 'delegation_check': _delegation_status(root, turn), 'instruction_snapshot': _instruction_snapshot(root, native, stage='recovery' if recovered else 'turn-begin'), 'format_independent': True, 'rule_comprehension_verified': False, 'required_completion': ['answer-prepare', 'native-delivery-check'], 'status': 'open', 'prepared': None, 'delivery': None, 'recovered_after_delivery': recovered, 'created_at': _now()}
	return r
def _state(root, native, turn, *, recovered=False, allow_extended=False, journal_directory=None, strict_journal=False):
	key = _key(native, turn)
	path = _folder(root) / (key + '.json')
	value = _read(path) if path.exists() else _new(root, native, turn, recovered=recovered, journal_directory=journal_directory)
	if 'instruction_snapshot' not in value:
		value['instruction_snapshot'] = _instruction_snapshot(root, native, stage='existing-state-upgrade')
	value['applicable_rules'] = _policy()
	value['git_optional_locks_env'] = os.environ.setdefault('GIT_OPTIONAL_LOCKS', '0')
	value['exec5_check'] = _exec5_status(turn)
	value['http_fetch_check'] = _http_fetch_status(turn)
	value['compaction_check'] = _compaction_status(root, key, turn)
	value['delegation_check'] = _delegation_status(root, turn)
	saved_directory = _directory(root, value['journal'])
	if strict_journal and None is not journal_directory and (saved_directory != _directory(root, journal_directory)):
		raise ValueError('The native turn already has a different journal; preserve its original binding')
	value['journal'] = str(saved_directory)
	for name, expected in [('project_root', str(Path(root).resolve())), ('platform', native['platform']), ('native_backend', native['native_backend']), ('conversation_id', native['conversation_id']), ('native_turn_id', turn['turn_id'])]:
		if value.get(name) != expected:
			raise ValueError('Completion state has a different native owner; preserved')
	old, current = (value['requests'], turn['requests'])
	if current[:len(old)] != old:
		raise ValueError('Native requests changed before the saved boundary; preserved')
	if not (value['prepared'] and current != old):
		value['requests'] = current
		r = (path, value)
	else:
		if not allow_extended:
			raise ValueError('A prepared answer does not cover the new native request; preserve it and reconcile the turn')
		value['uncovered_requests'] = current[len(old):]
		r = (path, value)
	return r
def _persist(path, value):
	value['updated_at'] = _now()
	replace_bytes(path, _json(value))
def _active(native):
	if not native['primary']:
		r = None
	else:
		turn = next((turn for turn in native['turns'] if turn['turn_id'] == native['active_turn_id']), None)
		if None is turn or not turn['owned'] or turn['aborted']:
			raise ValueError('No active native user turn belonging entirely to this project')
		r = turn
	return r
# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
def begin(root, conversation=None, *, platform=None, backend=None, watch=True, watch_dir=None, journal_directory=None):
	root = Path(root).resolve()
	native = _native(root, conversation, platform=platform, backend=backend)
	turn = _active(native)
	if None is turn:
		r = {'role': 'child', 'journal_required': False, 'reason': 'The primary conversation owns the user journal'}
	else:
		with locked(_folder(root) / 'writer.lock'):
			path, value = _state(root, native, turn, journal_directory=journal_directory, strict_journal=True)
			_persist(path, value)
		result = {'turn_key': value['key'], 'state': path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path), 'role': 'primary', 'journal_required': True, 'status': value['status'], 'native_requests_sha256': _hash(_json(turn['requests'])), 'applicable_rules': value['applicable_rules'], 'git_optional_locks_env': value['git_optional_locks_env'], 'exec5_check': value['exec5_check'], 'http_fetch_check': value['http_fetch_check'], 'compaction_check': value['compaction_check'], 'delegation_check': value['delegation_check'], 'rule_comprehension_verified': False, 'required_completion': value['required_completion']}
		if watch:
			from .journal_watch import register, start
			register(root, native, turn['start_step'], state_dir=watch_dir, journal_directory=value['journal'])
			result['watcher'] = start(state_dir=watch_dir)
			if any((t.get('owned') and t.get('completed') and (not t.get('aborted')) and (t.get('start_step', 0) < turn['start_step']) for t in native.get('turns', []))):
				try:
					sync(root, native['conversation_id'], platform=native['platform'], backend=native['native_backend'], journal_directory=value['journal'])
				except Exception:
					pass
		r = result
	return r
# 2026-10-30 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
# https://github.com/dmitry-ai/harness/issues/21
def recover_checkpoint(root, conversation=None, *, platform=None, backend=None):
	root = Path(root).resolve()
	native = _native(root, conversation, platform=platform, backend=backend)
	turn = _active(native)
	if None is turn:
		raise ValueError('No active primary native turn to recover')
	key = _key(native, turn)
	comp = dict(turn.get('compaction') or {})
	receipt_path = _folder(root) / f'{key}-checkpoint-recovery.json'
	receipt = {'turn_key': key, 'recovered_at': _now(), 'covered_checkpoint_step': comp.get('last_checkpoint_step'), 'checkpoint_steps': list(comp.get('checkpoint_steps') or []), 'pre_checkpoint_tool_steps': list(comp.get('pre_checkpoint_tool_steps') or []), 'pre_checkpoint_records': list(comp.get('pre_checkpoint_records') or [])}
	with locked(_folder(root) / 'writer.lock'):
		replace_bytes(receipt_path, _json(receipt))
		path, value = _state(root, native, turn)
		_persist(path, value)
	r = {**receipt, 'recovery_file': receipt_path.relative_to(root).as_posix() if receipt_path.is_relative_to(root) else str(receipt_path), 'compaction_check': value['compaction_check']}
	return r
def _group(root, native, turn, response, directory):
	key = 'native-' + _key(native, turn)
	legacy = turn['turn_id']
	groups = journal.state_dir(directory) / 'answer-groups'
	native_ids = [r['id'] for r in turn['requests']]
	matches = []
	for file in groups.glob('*.json'):
		old = _read(file)
		if old.get('request_ids') == native_ids:
			if old.get('requests') != [r['text'] for r in turn['requests']] or old.get('response_sha256') != _hash(response.encode('utf-8')):
				raise ValueError('A journal for these exact native request IDs has different bytes; preserve the conflict')
			matches.append(old)
	if len(matches) > 1:
		raise ValueError('More than one journal group claims these native request IDs; preserve the ambiguity')
	if matches:
		return (matches[0]['turn'], native_ids)
	if re.fullmatch('[A-Za-z0-9_-]{1,100}', legacy) and (groups / (legacy + '.json')).exists():
		old = _read(groups / (legacy + '.json'))
		if old.get('requests') != [r['text'] for r in turn['requests']] or old.get('response_sha256') != _hash(response.encode('utf-8')):
			raise ValueError('Existing native-turn journal has different bytes; preserve the conflict')
		return (legacy, old.get('request_ids'))
	return (key, native_ids)
def _recorded(value):
	return next((receipt for receipt in (value.get('prepared'), value.get('journal_record'), value.get('delivery')) if isinstance(receipt, dict) and 'journal_steps' in receipt), None)
def _record(root, native, turn, response, directory, *, existing=None):
	directory = _directory(root, directory)
	from .text_workflow import gate_requests
	gate_requests([root, directory], [r['text'] for r in turn['requests']], response)
	token, request_ids = _group(root, native, turn, response, directory)
	group_file = journal.state_dir(directory) / 'answer-groups' / (token + '.json')
	already_complete = group_file.exists() and 'complete' == _read(group_file).get('status')
	if existing:
		if not already_complete:
			raise ValueError('Recorded answer-group receipt is missing or incomplete; preserve journal history')
		if _read(group_file).get('steps') != existing['journal_steps']:
			raise ValueError('Recorded answer-group steps changed; preserve journal history')
	steps = journal.record_answer(directory, [r['text'] for r in turn['requests']], response, token, request_ids)
	for step, request in zip(steps, turn['requests']):
		if (directory / 'req' / f'{step}.md').read_bytes() != request['text'].encode('utf-8'):
			raise ValueError('Recorded request read-back differs from native text')
		if (directory / 'res' / f'{step}.md').read_bytes() != response.encode('utf-8'):
			raise ValueError('Recorded response read-back differs from prepared text')
	return {'journal_steps': steps, 'response_sha256': _hash(response.encode('utf-8')), 'response_file': str(directory / 'res' / f'{steps[0]}.md'), 'recorded_at': _now(), 'group_file': str(group_file), 'reused_complete_journal_group': already_complete}
def _unchanged(root, native, turn):
	latest = _native(root, native['conversation_id'], platform=native['platform'], backend=native['native_backend'])
	current = _active(latest)
	if None is current or _key(latest, current) != _key(native, turn) or current['requests'] != turn['requests']:
		raise ValueError('The active native turn or requests changed during preparation; readiness was not granted')
# 2026-10-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent reviewer prompt poisoning, enforce read-only reviewer isolation, verify numerical claims, and require multi-template SEO/DNS checks":
# https://github.com/dmitry-ai/harness/issues/12
def prepare(root, response, conversation=None, *, platform=None, backend=None, watch=True, watch_dir=None, journal_directory=None):
	if not isinstance(response, str) or not response.strip():
		raise ValueError('An exact nonempty UTF-8 final response is required')
	from .causal_checks import unsupported_probability_claims
	issues = unsupported_probability_claims(response)
	if issues:
		raise ValueError('Unsupported causal probability basis: ' + '; '.join(issues))
	result = begin(root, conversation, platform=platform, backend=backend, watch=watch, watch_dir=watch_dir, journal_directory=journal_directory)
	if not result['journal_required']:
		raise ValueError('A child executor cannot prepare the primary user journal')
	root = Path(root).resolve()
	native = _native(root, conversation, platform=platform, backend=backend)
	turn = _active(native)
	if None is turn or _key(native, turn) != result['turn_key'] or _hash(_json(turn['requests'])) != result['native_requests_sha256']:
		raise ValueError('The active native turn changed during preparation; no answer was recorded')
	with locked(_folder(root) / 'writer.lock'):
		_unchanged(root, native, turn)
		path, value = _state(root, native, turn)
		if not value['exec5_check']['verified']:
			commands = [cmd for item in value['exec5_check']['violations'] for cmd in item.get('commands', [])]
			detail = 'EXEC-5 violation in active turn (git read command without --no-optional-locks): ' + '; '.join(commands)
			value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
			_persist(path, value)
			raise ValueError(detail)
		if not value['http_fetch_check']['verified']:
			commands = [cmd for item in value['http_fetch_check']['violations'] for cmd in item.get('commands', [])]
			detail = 'KB-3 / EXEC-1 violation in active turn (ad-hoc HTTP fetch in shell without persistent Evidence collection; use collect or collect-http): ' + '; '.join(commands)
			value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
			_persist(path, value)
			raise ValueError(detail)
		if not value['compaction_check']['verified']:
			detail = 'COMPACT-1 / KB-3 violation in active turn: context compaction (CHECKPOINT) occurred after tool calls without post-checkpoint recovery; run recover-checkpoint or inspect transcript_full.jsonl before answer-prepare'
			value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
			_persist(path, value)
			raise ValueError(detail)
		if not value['delegation_check']['verified']:
			detail = f"REVIEW-1 / KB-3 violation in active turn: bulk primary-agent research ({value['delegation_check']['tool_step_count']} tool steps > {value['delegation_check']['max_unpersisted_steps']}) executed without A.F/A.A subagent delegation or incremental ꘖ/KB persistence"
			value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
			_persist(path, value)
			raise ValueError(detail)
		source_issues = response_source_and_kb_issues(root, response, turn['requests'])
		value['source_kb_check'] = {'verified': not source_issues, 'issues': source_issues}
		if source_issues:
			detail = '; '.join(source_issues)
			value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
			_persist(path, value)
			raise ValueError(detail)
		sha = _hash(response.encode('utf-8'))
		if value['prepared'] and value['prepared']['response_sha256'] != sha:
			raise ValueError('Prepared response bytes are immutable; preserve the earlier version and reconcile before a corrective turn')
		if 'conflict' == value['status']:
			raise ValueError('Resolve the native delivery conflict without overwriting journal history')
		workflow = root / 'ꘖ/data/workflow.json'
		if workflow.exists():
			from .workflow import load
			state = load(root)
			identifiers = {r['id'] for r in turn['requests']}
			covered = {r['id'] for r in state['requests']} & identifiers
			if covered:
				if covered != identifiers:
					raise ValueError('Adopt all exact current requests before preparing a tracked analysis response')
				from .review import authorize
				authorize(root, state, response=response)
				pending = {r['id'] for r in state['requests'] if not r.get('response_prepared') and (r.get('native_conversation_id') in (None, native['conversation_id']) or r['id'] in identifiers)}
				if pending:
					if pending != identifiers:
						raise ValueError('Align unanswered tracked requests with the exact current native turn before preparation')
					from .workflow import record_current_answer
					record_current_answer(root, response, journal_directory=value['journal'], request_ids=identifiers)
				elif any((r['response_prepared']['sha256'] != sha for r in state['requests'] if r['id'] in identifiers)):
					raise ValueError('Tracked analysis requests already have different prepared response bytes')
			elif (root / 'ꘖ/project.json').is_file() and (not any((re.search('(?:^|\\s)/df-(?:article|proposal)\\b', r.get('text', '')) for r in turn['requests']))) and ('complete' != state.get('stages', {}).get('finalize', {}).get('status') or (bool(re.search('\\b(?:H|M)-\\d+\\b', response)) and 0 == value['delegation_check'].get('subagent_step_count', 0))):
				detail = 'REVIEW-3 / REVIEW-4: Adopt current requests (adopt-requests) and complete review authorization before preparing a substantive response in a tracked Upwork project'
				value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': detail}
				_persist(path, value)
				raise ValueError(detail)
		value['prepared'] = _record(root, native, turn, response, value['journal'], existing=_recorded(value))
		try:
			_unchanged(root, native, turn)
		except (OSError, ValueError, sqlite3.Error) as exc:
			value['status'] = 'preparation_unverified'
			value['readiness_check'] = {'verified': False, 'checked_at': _now(), 'detail': str(exc)}
			_persist(path, value)
			raise
		value['status'] = 'prepared'
		value['readiness_check'] = {'verified': True, 'checked_at': _now()}
		_persist(path, value)
	return {**result, **value['prepared'], 'ready': True, 'status': 'prepared', 'delivery_verified': False}
def _conflict(root, path, value, native, turn, response, detail, *, retryable=False):
	payload = response.encode('utf-8')
	evidence = _folder(root) / 'conflicts' / (value['key'] + '-' + _hash(payload) + '.txt')
	evidence.parent.mkdir(parents=True, exist_ok=True)
	if evidence.exists() and evidence.read_bytes() != payload:
		raise ValueError('Immutable native conflict evidence changed')
	if not evidence.exists():
		create_bytes(evidence, payload)
	if _recorded(value):
		value['journal_record'] = _recorded(value)
	value['status'] = 'conflict'
	value['delivery'] = {'verified': False, 'native_response_sha256': _hash(payload), 'source_file': native['source_file'], 'final_step': turn['final_step'], 'native_requests': turn['requests'], 'conflict_evidence': evidence.relative_to(root).as_posix(), 'detail': detail, 'retryable': retryable}
	_persist(path, value)
	r = {'turn_key': value['key'], 'status': 'conflict', 'detail': detail, 'evidence': evidence.relative_to(root).as_posix(), 'retryable': retryable}
	return r
def _strip_local_file_scheme(text: str) -> str:
	return re.sub('file:///+(?=[A-Za-z]:/)', '', text or '', flags=re.IGNORECASE).rstrip('\r\n ')
# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
def sync(root, conversation=None, *, platform=None, backend=None, from_step=0, journal_directory=None):
	if type(from_step) is not int or from_step < 0:
		raise ValueError('Native from-step must be a nonnegative integer')
	root = Path(root).resolve()
	native = _native(root, conversation, platform=platform, backend=backend)
	if not native['primary']:
		raise ValueError('A child executor has no primary user journal to synchronize')
	if not any((turn['owned'] for turn in native['turns'])):
		raise ValueError('Native conversation has no user turns owned by this project')
	eligible = [turn for turn in native['turns'] if turn['owned'] and turn['completed'] and (not turn['aborted']) and (turn['start_step'] >= from_step)]
	if not eligible:
		return {'valid': True, 'conversation_id': native['conversation_id'], 'source_file': native['source_file'], 'turns': [], 'pending_native_turn': native['active_turn_id'], 'private_reasoning_retained': False}
	results = []
	with locked(_folder(root) / 'writer.lock'):
		for turn in eligible:
			path, value = _state(root, native, turn, recovered=True, allow_extended=True, journal_directory=journal_directory)
			response = turn['response']
			sha = _hash(response.encode('utf-8'))
			if value.get('uncovered_requests'):
				results.append(_conflict(root, path, value, native, turn, response, 'Prepared answer does not cover newly received native requests'))
				continue
			effective_response = response
			if value['prepared'] and value['prepared']['response_sha256'] != sha:
				prep_file = Path(value['prepared'].get('response_file') or '')
				prep_text = prep_file.read_text(encoding='utf-8') if prep_file.is_file() else ''
				if prep_text and _strip_local_file_scheme(prep_text) == _strip_local_file_scheme(response):
					effective_response = prep_text
				else:
					results.append(_conflict(root, path, value, native, turn, response, 'Prepared and delivered response bytes differ'))
					continue
			try:
				recorded = _record(root, native, turn, effective_response, value['journal'], existing=_recorded(value))
			except (OSError, ValueError) as exc:
				results.append(_conflict(root, path, value, native, turn, response, str(exc), retryable=isinstance(exc, OSError) and (not isinstance(exc, FileNotFoundError))))
				continue
			if not _recorded(value):
				value['recovered_after_delivery'] = not bool(value['prepared']) and (not recorded['reused_complete_journal_group'])
			provenance = 'prepared' if value['prepared'] else 'recovered_native' if value['recovered_after_delivery'] else 'existing_journal'
			preparation_verified = bool(value['prepared']) and value.get('readiness_check', {}).get('verified', True)
			value['journal_record'] = recorded
			value['delivery'] = {**recorded, 'verified': True, 'source_file': native['source_file'], 'final_step': turn['final_step'], 'completion_step': turn['completion_step'], 'native_response_sha256': sha, 'verified_at': _now(), 'completion_provenance': provenance, 'preparation_verified': preparation_verified, 'exec5_check': value['exec5_check']}
			value['status'] = 'delivered'
			_persist(path, value)
			results.append({'turn_key': value['key'], 'status': 'delivered', 'delivery_verified': True, 'journal_steps': recorded['journal_steps'], 'completion_provenance': provenance, 'preparation_verified': preparation_verified, 'recovered_after_delivery': value['recovered_after_delivery'], 'exec5_check': value['exec5_check']})
	return {'valid': not any(('conflict' == r['status'] for r in results)), 'conversation_id': native['conversation_id'], 'source_file': native['source_file'], 'turns': results, 'retryable': any((r.get('retryable') for r in results)), 'pending_native_turn': native['active_turn_id'], 'private_reasoning_retained': False}
def add_parser_arguments(parser, command):
	if 'journal-watch' == command:
		parser.add_argument('--action', choices=('start', 'status', 'stop', 'once', 'run'), default='status')
		parser.add_argument('--state-dir', type=Path)
		parser.add_argument('--interval', type=float, default=5)
		parser.add_argument('--token', help='Internal watcher ownership token')
		return
	parser.add_argument('project', type=Path)
	parser.add_argument('--conversation', help='Actual current native conversation UUID; Codex can use CODEX_THREAD_ID')
	if command not in ('journal-unwatch', 'recover-checkpoint'):
		parser.add_argument('--journal', type=Path, help='User-selected journal; otherwise preserve the turn binding or use ꙮ/1 - Analysis')
	if command in ('turn-begin', 'answer-prepare'):
		parser.add_argument('--no-watch', action='store_true', help='Explicit foreground-only mode; no independent recovery')
	if 'answer-prepare' == command:
		parser.add_argument('--response-file', type=Path, required=True, help='Exact UTF-8 final response, or - for stdin')
		parser.add_argument('--consume-input', action='store_true')
	if 'journal-sync' == command:
		parser.add_argument('--from-step', type=int, default=0)
def execute(args):
	if 'turn-begin' == args.command:
		r = begin(args.project, args.conversation, watch=not args.no_watch, journal_directory=args.journal)
	elif 'recover-checkpoint' == args.command:
		r = recover_checkpoint(args.project, args.conversation)
	elif 'answer-prepare' == args.command:
		from .operations import _operation_input, _consumed
		payload = _operation_input(args, args.response_file)
		result = prepare(args.project, payload.decode('utf-8'), args.conversation, watch=not args.no_watch, journal_directory=args.journal)
		r = _consumed(args, args.response_file, payload, result)
	elif 'journal-sync' == args.command:
		r = sync(args.project, args.conversation, from_step=args.from_step, journal_directory=args.journal)
	elif 'journal-unwatch' == args.command:
		from .journal_watch import unregister
		native = _native(args.project, args.conversation)
		if not native['primary'] or not any((turn['owned'] for turn in native['turns'])):
			raise ValueError('Only the owned primary conversation can remove its watcher binding')
		r = unregister(args.project, native)
	elif 'journal-watch' != args.command:
		raise ValueError('Unknown completion operation')
	else:
		from . import journal_watch
		if 'run' == args.action:
			r = journal_watch.run(state_dir=args.state_dir, token=args.token, interval=args.interval)
		else:
			r = getattr(journal_watch, args.action)(state_dir=args.state_dir)
	return r
