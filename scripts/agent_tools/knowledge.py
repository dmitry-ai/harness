# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Decompose workflow.py and knowledge.py into WorkflowStateEngine, ResearchQuestionRegistry, and ProjectHealthAuditor with shared attachment inventory":
# https://github.com/dmitry-ai/harness/issues/74
# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
# https://github.com/dmitry-ai/harness/issues/3
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-04 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Scope research questions to active turn, distinguish factual KB notes from hypotheses, and reconcile unprepared chat deliveries":
# https://github.com/dmitry-ai/harness/issues/44
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from .storage import create_bytes, replace_bytes
from .links import markdown_link
from .upwork_data import canonical_job_url, classify_attachment, detect_client_videos, extract_attachment_markdown, extract_loom_video, format_kb_project_md, markdown_fence, structure_job_description
from .analysis import SECTIONS, TITLES, validate_analysis, render_analysis, publish_owned
class AttachmentInventory:
	def __init__(self, project_root: Path | str):
		self.root = Path(project_root).resolve()
		self.kb_dir = self.root / '\ua616' / 'KB'
		self.att_root = self.kb_dir / 'Evidence' / 'Attachments'
		self.source_dir = self.root / 'source'
	def _evidence_entries(self, asset_evidence: list[dict] | None=None) -> list[tuple[Path, str | None]]:
		r: list[tuple[Path, str | None]] = []
		for item in asset_evidence or []:
			rel = item.get('file') if isinstance(item, dict) else None
			if rel and (self.kb_dir / rel).is_file():
				r.append((self.kb_dir / rel, item.get('sha256')))
		if self.att_root.is_dir():
			for sha_dir in sorted(self.att_root.iterdir()):
				if sha_dir.is_dir() and re.fullmatch('[0-9a-f]{64}', sha_dir.name):
					for f in sorted(sha_dir.iterdir()):
						if f.is_file():
							r.append((f, sha_dir.name))
		return r
	def _register_bytes(self, filename: str, payload: bytes, expected_sha: str | None, seen_digests: set[str], assets: list[dict]) -> None:
		from .upwork_extract import attachment_path
		digest = hashlib.sha256(payload).hexdigest()
		if expected_sha and digest != expected_sha:
			raise ValueError(f'Attachment changed after capture: {filename}')
		folder = self.att_root / digest
		target = attachment_path(folder, filename)
		folder.mkdir(parents=True, exist_ok=True)
		if not target.exists():
			create_bytes(target, payload)
		self.source_dir.mkdir(parents=True, exist_ok=True)
		src_target = attachment_path(self.source_dir, target.name)
		if src_target.exists() and src_target.read_bytes() != payload:
			stem, suf = (src_target.stem, src_target.suffix)
			idx = 2
			while True:
				cand = self.source_dir / f'{stem} ({idx}){suf}'
				if not cand.exists() or cand.read_bytes() == payload:
					src_target = cand
					break
				idx += 1
		if not src_target.exists():
			create_bytes(src_target, payload)
		if digest not in seen_digests:
			seen_digests.add(digest)
			assets.append({'file': target.relative_to(self.kb_dir).as_posix(), 'sha256': digest, 'filename': target.name, 'source_file': src_target.relative_to(self.root).as_posix()})
	def _source_entries(self) -> list[Path]:
		return [f for f in sorted(self.source_dir.iterdir()) if f.is_file()] if self.source_dir.is_dir() else []
	def scan(self, asset_evidence: list[dict] | None=None) -> dict:
		attachments: list[dict] = []
		seen_sha: set[str] = set()
		for target, hint_sha in self._evidence_entries(asset_evidence):
			sha = hint_sha or hashlib.sha256(target.read_bytes()).hexdigest()
			if sha not in seen_sha:
				seen_sha.add(sha)
				attachments.append({'filename': target.name, 'sha256': sha, 'evidence_path': target})
		source_by_sha: dict[str, list[Path]] = {}
		missing_evidence: list[tuple[Path, str]] = []
		for f in self._source_entries():
			sha = hashlib.sha256(f.read_bytes()).hexdigest()
			source_by_sha.setdefault(sha, []).append(f)
			if not (self.att_root / sha / f.name).is_file():
				missing_evidence.append((f, sha))
			if sha not in seen_sha:
				seen_sha.add(sha)
				attachments.append({'filename': f.name, 'sha256': sha, 'evidence_path': f})
		return {'attachments': attachments, 'missing_evidence': missing_evidence, 'source_by_sha': source_by_sha}
	def sync(self, saved_attachments: list[dict] | None=None, asset_evidence: list[dict] | None=None) -> list[dict]:
		r: list[dict] = []
		seen_digests: set[str] = set()
		for item in saved_attachments or []:
			src_path = Path(item['path'])
			fname = item.get('filename') or item.get('name') or src_path.name
			self._register_bytes(fname, src_path.read_bytes(), item.get('sha256'), seen_digests, r)
		for target, expected_sha in self._evidence_entries(asset_evidence):
			self._register_bytes(target.name, target.read_bytes(), expected_sha, seen_digests, r)
		for f in self._source_entries():
			self._register_bytes(f.name, f.read_bytes(), None, seen_digests, r)
		return r
def website_issues(value):
	from urllib.parse import urlsplit
	from .diagnostics import problem
	if 'websites' not in value:
		r = []
	else:
		sites = value['websites']
		identities = {claim['id'] for claim in value.get('identity') or [] if isinstance(claim, dict) and isinstance(claim.get('id'), str)} if isinstance(value.get('identity'), list) else set()
		if not isinstance(sites, list) or not sites:
			r = [problem('websites.list', '/websites', 'Record an evidenced website or an explicit unidentified selection')]
		else:
			issues = []
			for index, site in enumerate(sites):
				field = f'/websites/{index}'
				if not isinstance(site, dict) or not isinstance(site.get('basis_id'), str) or site['basis_id'] not in identities or (site.get('role') not in ('client', 'target')):
					issues.append(problem('websites.basis', field, 'Use client/target and a current identity claim ID'))
					continue
				url = site.get('url')
				if None is not url:
					try:
						if not isinstance(url, str):
							raise ValueError('Website URL must be a string')
						parsed = urlsplit(url)
						valid = parsed.scheme in ('https', 'http') and parsed.hostname and (not parsed.username) and (not parsed.password) and (not any((c.isspace() for c in url)))
						_ = parsed.port
					except (TypeError, ValueError):
						valid = False
					if not valid:
						issues.append(problem('websites.url', field + '/url', 'Use an HTTP(S) URL or null for an unidentified site'))
			r = issues
	return r
def sync_website_card(root, value, *, selections=None, check=False):
	from .analysis import digest
	from .project_card import sync_block
	root = Path(root).resolve()
	metadata = root / 'ꘖ/data/rendered.json'
	state = json.loads(metadata.read_bytes()) if metadata.exists() else {}
	cached = state.get(str(root / '.md'), {}).get('managed_blocks', {}).get('websites', {}).get('data')
	selected = selections if None is not selections else value.get('websites', cached)
	if None is selected:
		return {'status': 'unassessed', 'target': str(root / '.md')}
	checked = {**value, 'websites': selected}
	if website_issues(checked):
		raise ValueError(website_issues(checked))
	identities = {claim['id']: (index, claim) for index, claim in enumerate(value['identity'])}
	stored, lines = ([], ['## Client and Project Website', ''])
	for site in selected:
		index, claim = identities[site['basis_id']]
		sha = digest(json_bytes(claim))
		if site.get('basis_sha256', sha) != sha:
			return {'status': 'conflict', 'target': str(root / '.md'), 'detail': 'Website identity evidence changed; reassess its explicit selection'}
		label = 'Client website' if 'client' == site['role'] else 'Target project website'
		url = site.get('url')
		address = markdown_link(None, url) if url else '**unresolved from available data**'
		probability = claim.get('probability_percent')
		assessment = f' Identification score: {probability}%.' if None is not probability else ''
		lines.append(f"- **{label}:** {address}.{assessment} [Basis: {claim['id']}](<ꘖ/KB/Analysis.json#/identity/{index}>).")
		stored.append({'url': url, 'role': site['role'], 'basis_id': site['basis_id'], 'basis_sha256': sha})
	result = sync_block(root, root / '.md', 'websites', '\n'.join(lines) + '\n', position='after-title', check=check, source=root / 'ꘖ/KB/Analysis.json', attributes=stored)
	return result
def sync_initial_website(root, snapshot, hypothesis=None):
	from .project_card import sync_block
	root = Path(root).resolve()
	if not hypothesis:
		source = Path(snapshot).resolve()
		content = f'## Client and Project Website\n\nURL is not yet established by initial extraction; identification requires analysis. [Source job post](<{source.relative_to(root).as_posix()}#/description>).\n'
	else:
		if 'website_url' not in hypothesis:
			return {'status': 'unassessed'}
		url = hypothesis['website_url']
		site = {'url': url, 'role': 'target', 'basis_id': hypothesis.get('id')}
		issues = website_issues({'identity': [hypothesis], 'websites': [site]})
		if issues:
			raise ValueError(issues)
		address = markdown_link(None, url) if url else '**unresolved**'
		content = f"## Client and Project Website\n\n**Target project website:** {address}. Hypothesis score: {hypothesis['probability_percent']}%. [Basis: {hypothesis['id']}](KB/Project.md#13-website).\n"
		source = root / 'KB/Project.md'
	return sync_block(root, root / '.md', 'websites', content, source=source)
def json_bytes(value):
	return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
def create_once(path: Path, content: str):
	path.parent.mkdir(parents=True, exist_ok=True)
	if not path.exists():
		if path.suffix.lower() in ('.md', '.markdown', '.txt', '.html', '.htm'):
			from .links import readable_link_issues
			issues = readable_link_issues(content)
			if issues:
				raise ValueError('\n'.join(issues))
		create_bytes(path, content.encode('utf-8'))
def sync_source_folder_attachments(project_root: Path, saved_attachments: list[dict] | None=None, asset_evidence: list[dict] | None=None) -> list[dict]:
	return AttachmentInventory(project_root).sync(saved_attachments, asset_evidence)
def _load_media_descriptions(project_root: Path, overrides: dict | None=None) -> dict[str, str]:
	root = Path(project_root).resolve()
	media_dir = root / 'ꘖ' / 'data' / 'media'
	store_file = media_dir / 'descriptions.json'
	descriptions: dict[str, str] = {}
	if store_file.is_file():
		try:
			loaded = json.loads(store_file.read_text(encoding='utf-8'))
			if isinstance(loaded, dict):
				descriptions.update({str(k): str(v) for k, v in loaded.items() if isinstance(v, str) and v.strip()})
		except Exception:
			pass
	if overrides and isinstance(overrides, dict):
		for k, v in overrides.items():
			if isinstance(v, str) and v.strip():
				descriptions[str(k)] = v.strip()
		media_dir.mkdir(parents=True, exist_ok=True)
		replace_bytes(store_file, json_bytes(descriptions))
	r = descriptions
	return r
def build_project_extra_sources(project_root: Path, data: dict, assets: list[dict] | None=None, *, fetch_videos: bool=True) -> list[dict]:
	root = Path(project_root).resolve()
	kb_dir = root / 'ꘖ' / 'KB'
	if None is assets:
		assets = sync_source_folder_attachments(root, data.get('saved_attachments'), data.get('asset_evidence'))
	descriptions = _load_media_descriptions(root, data.get('media_descriptions'))
	extra_sources: list[dict] = []
	doc_markdowns: list[str] = []
	for asset in assets:
		target = kb_dir / asset['file']
		if not target.is_file():
			continue
		fname = asset.get('filename') or target.name
		sha = asset['sha256']
		payload = target.read_bytes()
		src_copy = root / 'source' / fname
		if not src_copy.exists():
			src_copy.parent.mkdir(parents=True, exist_ok=True)
			create_bytes(src_copy, payload)
		kind = classify_attachment(fname, payload)
		custom_body = descriptions.get(fname) or descriptions.get(sha)
		if 'document' == kind:
			body = custom_body or extract_attachment_markdown(target, payload)
			doc_markdowns.append(body)
			extra_sources.append({'kind': 'document', 'name': fname, 'heading': f'Description in `{fname}`', 'body': body, 'sha256': sha, 'file': asset['file'], 'source_file': asset.get('source_file') or f'source/{fname}'})
		elif 'image' == kind:
			body = custom_body or ''
			extra_sources.append({'kind': 'image', 'name': fname, 'heading': f'Description in `{fname}`', 'body': body, 'sha256': sha, 'file': asset['file'], 'source_file': asset.get('source_file') or f'source/{fname}'})
	videos = detect_client_videos(data.get('description') or '', doc_markdowns, assets)
	media_dir = root / 'ꘖ' / 'data' / 'media'
	for v in videos:
		v_key = v.get('url') or v.get('filename') or v.get('video_id') or ''
		v_key_www = re.sub('^https?://(?!www\\.)', 'https://www.', v_key) if v_key.startswith('http') else ''
		v_key_nowww = re.sub('^https?://www\\.', 'https://', v_key) if v_key.startswith('http') else ''
		custom_body = descriptions.get(v_key) or (descriptions.get(v_key_www) if v_key_www else None) or (descriptions.get(v_key_nowww) if v_key_nowww else None) or (descriptions.get(v['video_id']) if v.get('video_id') else None) or (descriptions.get(v['filename']) if v.get('filename') else None)
		body = custom_body or ''
		if not body and 'loom' == v.get('kind') and v.get('url'):
			cache_file = media_dir / f"loom-{v['video_id']}.json"
			if cache_file.is_file():
				try:
					cached = json.loads(cache_file.read_text(encoding='utf-8'))
					body = cached.get('markdown') or ''
				except Exception:
					body = ''
			if not body and fetch_videos:
				try:
					loom_info = extract_loom_video(v['url'])
					media_dir.mkdir(parents=True, exist_ok=True)
					replace_bytes(cache_file, json_bytes(loom_info))
					body = loom_info.get('markdown') or ''
				except Exception:
					body = ''
		extra_sources.append({'kind': 'video', 'name': v.get('filename') or v.get('url') or v['label'], 'url': v.get('url'), 'video_id': v.get('video_id'), 'sha256': v.get('sha256'), 'file': next((a['file'] for a in assets if a.get('sha256') == v.get('sha256')), None) if v.get('sha256') else None, 'source_file': f"source/{v['filename']}" if v.get('filename') else None, 'heading': v['heading'], 'body': body})
	r = extra_sources
	return r
def _render_projects_md(data: dict, url: str, source_link: str, extra_sources: list[dict], project_root: Path | None=None) -> str:
	fence = markdown_fence(data.get('description', ''), '`')
	projects = ['# Projects', '', '## F-PROJECT-1', f'[Current job post]({url}).', fence + 'markdown', data.get('title', ''), data.get('description', ''), fence, f'[Source text]({source_link}#/description).', '']
	for idx, extra in enumerate(extra_sources, start=1):
		ebody = (extra.get('body') or '').strip()
		efence = markdown_fence(ebody, '`')
		projects.extend([f'## F-PROJECT-ATTACHMENT-{idx}', f"### {extra['heading']}"])
		has_src = bool(extra.get('source_file') and (None is project_root or (project_root / extra['source_file']).is_file()))
		if extra.get('file') and has_src:
			projects.append(f"[Primary file](<{extra['file']}>) · [File in source](<../../{extra['source_file']}>).")
		elif extra.get('file'):
			projects.append(f"[Primary file](<{extra['file']}>).")
		elif extra.get('url'):
			projects.append(markdown_link('Video source', extra['url']) + '.')
		if ebody:
			projects.extend([efence + 'markdown', ebody, efence])
		projects.append('')
	projects.extend(['## F-PROJECT-2', 'History actually returned by the page; connection of all jobs to a single website is not established.', '```json', json.dumps({k: data.get(k) for k in ('work_history', 'open_jobs', 'related_descriptions', 'coverage')}, ensure_ascii=False, indent=2), '```', f'[Snapshot]({source_link}).', ''])
	r = '\n'.join(projects)
	return r
def _render_evidence_md(asset_evidence: list[dict], extra_sources: list[dict], project_root: Path | None=None) -> str | None:
	if not asset_evidence and (not extra_sources):
		r = None
	else:
		ev_lines = ['# Attachments', '']
		extra_by_sha = {e.get('sha256'): e for e in extra_sources if e.get('sha256')}
		for x in asset_evidence:
			fname = Path(x['file']).name
			sha = x['sha256']
			ev_lines.append(f'## {fname}')
			has_src = None is project_root or (project_root / 'source' / fname).is_file()
			if has_src:
				ev_lines.append(f"[{fname}](<{x['file']}>) · [source/{fname}](<../../source/{fname}>) — SHA-256 `{sha}`.")
			else:
				ev_lines.append(f"[{fname}](<{x['file']}>) — SHA-256 `{sha}`.")
			ext = extra_by_sha.get(sha)
			if ext and (ext.get('body') or '').strip():
				ebody = ext['body'].strip()
				bfence = markdown_fence(ebody, '`')
				ev_lines.extend(['', bfence + 'markdown', ebody, bfence])
			ev_lines.append('')
		for e in extra_sources:
			if 'video' == e.get('kind') and e.get('url') and (not e.get('sha256')):
				ev_lines.append(f"## {e['heading']}")
				ev_lines.append(markdown_link(None, e['url']) + '.')
				if (e.get('body') or '').strip():
					ebody = e['body'].strip()
					bfence = markdown_fence(ebody, '`')
					ev_lines.extend(['', bfence + 'markdown', ebody, bfence])
				ev_lines.append('')
		r = '\n'.join(ev_lines).rstrip() + '\n'
	return r
def populate_agent_kb(project_root: Path, data: dict):
	kb = project_root / 'ꘖ' / 'KB'
	evidence = kb / 'Evidence'
	evidence.mkdir(parents=True, exist_ok=True)
	source = {k: v for k, v in data.items() if k not in ('saved_attachments', 'cookies', 'extra_sources', 'media_descriptions', 'site_hypothesis')}
	if 'asset_evidence' in source and isinstance(source['asset_evidence'], list):
		source['asset_evidence'] = [{'file': x['file'], 'sha256': x['sha256']} for x in source['asset_evidence']]
	raw = json_bytes(source)
	fingerprint = hashlib.sha256(raw).hexdigest()
	snapshot = evidence / f'{fingerprint}.json'
	if not snapshot.exists():
		create_bytes(snapshot, raw)
	source_link = f'Evidence/{fingerprint}.json'
	when = data.get('observed_at') or datetime.now(timezone.utc).isoformat(timespec='seconds')
	url = canonical_job_url(data['job_id'])
	extra_sources = data.get('extra_sources')
	if None is extra_sources:
		extra_sources = build_project_extra_sources(project_root, data, data.get('asset_evidence'))
	manual = project_root / 'KB' / 'Project.md'
	if manual.is_file():
		create_once(kb / 'Project.md', manual.read_bytes().decode('utf-8'))
	else:
		create_once(kb / 'Project.md', format_kb_project_md({**data, 'extra_sources': extra_sources}))
	buyer = data.get('buyer') or {}
	client = ['# Client', '', '## F-CLIENT-1', f'Upwork card snapshot captured {when}: [job post]({url}).', '', '## F-CLIENT-2', 'Account fields in this snapshot; these are platform details rather than independent verification:', '```json', json.dumps(buyer, ensure_ascii=False, indent=2), '```', f'[Snapshot]({source_link}#/buyer).', '']
	if data.get('client_names'):
		client.extend(['## F-CLIENT-3', 'Heuristic name matches in reviews; client identity is not established:', '```json', json.dumps(data['client_names'], ensure_ascii=False, indent=2), '```', f'[Reviews]({source_link}#/client_names).', ''])
	create_once(kb / 'Client.md', '\n'.join(client))
	website = ['# Website', '', '## F-SITE-1', 'Website ownership is not established by automated extraction.', 'The folder name and discovered URLs do not confirm ownership.', '', '## F-SITE-2', 'Domains mentioned in source texts:', '```json', json.dumps(data.get('candidate_domains') or [], ensure_ascii=False, indent=2), '```', f'[Snapshot]({source_link}#/candidate_domains).', '']
	create_once(kb / 'Website.md', '\n'.join(website))
	create_once(kb / 'Projects.md', _render_projects_md(data, url, source_link, extra_sources, project_root))
	ev_md = _render_evidence_md(source.get('asset_evidence') or [], extra_sources, project_root)
	if None is not ev_md:
		create_once(kb / 'Evidence.md', ev_md)
	create_once(kb / 'Glossary.md', '# Glossary\n\nDefinitions are added when used; each term includes a link to its source.\n')
	create_once(kb / '.md', '# Knowledge Base\n\n[Client](Client.md) · [Website](Website.md) · [Projects](Projects.md) · [Glossary](Glossary.md) · [Initial Description](Project.md).\n\nF — observation or quoted source words; H — hypothesis; M — solution method.\nFor H/M: essence, for, against, score in %, assessment basis; links point to primary data.\n')
	r = snapshot
	return r
def _replace_section2_in_project_md(existing_md: str, data: dict, extra_sources: list[dict]) -> str:
	fresh_md = format_kb_project_md({**data, 'extra_sources': extra_sources})
	m_fresh = re.search('(?m)^# 2\\. (?:Current Client Project|\\u0422\\u0435\\u043a\\u0443\\u0449\\u0438\\u0439 \\u043f\\u0440\\u043e\\u0435\\u043a\\u0442 \\u043a\\u043b\\u0438\\u0435\\u043d\\u0442\\u0430)\\n(.*?)(?=^# 3\\. (?:Past Client Projects|\\u041f\\u0440\\u043e\\u0448\\u043b\\u044b\\u0435 \\u043f\\u0440\\u043e\\u0435\\u043a\\u0442\\u044b \\u043a\\u043b\\u0438\\u0435\\u043d\\u0442\\u0430)\\n|\\Z)', fresh_md, re.S)
	if not m_fresh:
		r = fresh_md
	else:
		sec2_block = '# 2. Current Client Project\n' + m_fresh.group(1)
		m_exist = re.search('(?m)^# 2\\. (?:Current Client Project|\\u0422\\u0435\\u043a\\u0443\\u0449\\u0438\\u0439 \\u043f\\u0440\\u043e\\u0435\\u043a\\u0442 \\u043a\\u043b\\u0438\\u0435\\u043d\\u0442\\u0430)\\n(.*?)(?=^# 3\\. (?:Past Client Projects|\\u041f\\u0440\\u043e\\u0448\\u043b\\u044b\\u0435 \\u043f\\u0440\\u043e\\u0435\\u043a\\u0442\\u044b \\u043a\\u043b\\u0438\\u0435\\u043d\\u0442\\u0430)\\n|\\Z)', existing_md, re.S)
		if not m_exist:
			r = fresh_md
		else:
			r = existing_md[:m_exist.start()] + sec2_block + existing_md[m_exist.end():]
	return r
# 2026-10-17 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
# https://github.com/dmitry-ai/harness/issues/7
def sync_project_attachments_and_kb(project_root: Path, media_descriptions: dict | None=None, *, fetch_videos: bool=True) -> dict:
	root = Path(project_root).resolve()
	pj_file = root / 'ꘖ' / 'project.json'
	if not pj_file.is_file():
		raise ValueError(f'Missing project.json in {root}')
	pj = json.loads(pj_file.read_text(encoding='utf-8'))
	snapshot_path = root / pj['snapshot']
	snapshot_data = json.loads(snapshot_path.read_text(encoding='utf-8'))
	source_link = snapshot_path.relative_to(root / 'ꘖ' / 'KB').as_posix()
	url = canonical_job_url(pj['job_id'])
	assets = sync_source_folder_attachments(root, asset_evidence=snapshot_data.get('asset_evidence'))
	merged_data = {**snapshot_data, 'asset_evidence': assets}
	if media_descriptions:
		merged_data['media_descriptions'] = media_descriptions
	extra_sources = build_project_extra_sources(root, merged_data, assets, fetch_videos=fetch_videos)
	manual_kb = root / 'KB' / 'Project.md'
	agent_kb_proj = root / 'ꘖ' / 'KB' / 'Project.md'
	if manual_kb.is_file():
		updated_proj_md = _replace_section2_in_project_md(manual_kb.read_text(encoding='utf-8'), merged_data, extra_sources)
	else:
		updated_proj_md = format_kb_project_md({**merged_data, 'extra_sources': extra_sources})
	replace_bytes(manual_kb, updated_proj_md.encode('utf-8'))
	replace_bytes(agent_kb_proj, updated_proj_md.encode('utf-8'))
	projects_md = _render_projects_md(merged_data, url, source_link, extra_sources)
	replace_bytes(root / 'ꘖ' / 'KB' / 'Projects.md', projects_md.encode('utf-8'))
	ev_md = _render_evidence_md([{'file': a['file'], 'sha256': a['sha256']} for a in assets], extra_sources)
	if None is not ev_md:
		replace_bytes(root / 'ꘖ' / 'KB' / 'Evidence.md', ev_md.encode('utf-8'))
	r = {'project_root': str(root), 'source_files': [a['source_file'] for a in assets], 'extra_sources': [{'kind': e['kind'], 'name': e['name'], 'heading': e['heading'], 'has_body': bool((e.get('body') or '').strip())} for e in extra_sources]}
	return r
# 2026-11-04 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Scope research questions to active turn, distinguish factual KB notes from hypotheses, and reconcile unprepared chat deliveries":
# https://github.com/dmitry-ai/harness/issues/44
def validate_kb_factual_note(path: Path | str, text: str) -> list[str]:
	issues = []
	p = Path(path)
	filename = p.name
	m_id = re.search(r'\b(?:H|M)-(?:[A-Za-z0-9]+-)*\d+\b', text)
	if m_id:
		issues.append(f"{filename}: Hypothesis/method identifier '{m_id.group(0)}' forbidden in factual research note; hypotheses must be registered in Analysis.json/Analysis.md per KB-2/DOC-1")
	m_head = re.search(r'(?im)^#{1,6}\s*(?:H-\d+|Гипотез\w*|Hypothes\w*|Причин\w*|Causes?|Misconceptions?|Заблужден\w*|Метод\w*|Methods?)\b', text)
	if m_head:
		issues.append(f"{filename}: Analytical heading '{m_head.group(0).strip()}' forbidden in factual research note per KB-2/DOC-1")
	has_pro = bool(re.search(r'(?i)(?:довод\w*\s+за|arguments?\s+for)\b', text))
	has_con = bool(re.search(r'(?i)(?:довод\w*\s+против|arguments?\s+against|counterevidence)\b', text))
	if has_pro and has_con:
		issues.append(f"{filename}: Structured pro/con arguments (DOC-2/DOC-3) forbidden in factual research note")
	from .causal_checks import unsupported_probability_claims
	for c_issue in unsupported_probability_claims(text):
		issues.append(f"{filename}: {c_issue}")
	for lineno, line in enumerate((text or '').splitlines(), 1):
		sline = line.strip()
		if not sline or sline.startswith(('#', '```', '|', '>')):
			continue
		m_cause = re.search(r'(?i)\b(?:причиной\s+(?:является|была|было|служит)|первопричина|root\s+cause)\b', sline)
		if m_cause:
			issues.append(f"{filename}:{lineno}: Causal assertion '{m_cause.group(0)}' requires H-* hypothesis in Analysis.json per DOC-2")
	return issues
