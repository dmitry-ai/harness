"""Deterministic Upwork project initializer, CDP extractor, .agents linker, and KB scaffolder."""

from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request

import uuid

from .context import generate as generate_context
from .storage import replace_bytes


PRIMARY_AGENTS_DIR = Path(r'C:\work\upwork\code\AI\primary\result\.agents')
DAILY_PROPOSALS_ROOT = Path(r'C:\work\upwork\code\proposals\daily')
ANTIGRAVITY_PROJECTS_DIR = Path.home() / '.gemini' / 'config' / 'projects'
ANTIGRAVITY_FOLDERS_JSON = Path(
    r'C:\work\research\provision\code\Software\Google\AI\Antigravity\primary\tools\Folders\code\folders.json'
)

IGNORED_CANDIDATE_DOMAINS = {
    'upwork.com',
    'www.upwork.com',
    'youtube.com',
    'www.youtube.com',
    'youtu.be',
    'linkedin.com',
    'www.linkedin.com',
    'facebook.com',
    'www.facebook.com',
    'instagram.com',
    'www.instagram.com',
    'google.com',
    'www.google.com',
    'docs.google.com',
    'drive.google.com',
    'loom.com',
    'www.loom.com',
    'figma.com',
    'www.figma.com',
    'canva.com',
    'www.canva.com',
    'speedtest.net',
    'www.speedtest.net',
    'stape.io',
    'www.stape.io',
    'adbeacon.com',
    'www.adbeacon.com',
    'klaviyo.com',
    'www.klaviyo.com',
    'shopify.com',
    'www.shopify.com',
    'webflow.com',
    'www.webflow.com',
    'wordpress.org',
    'wordpress.com',
    'zendesk.com',
    'www.zendesk.com',
}


def normalize_job_id(url_or_id: str) -> str:
    """Extract canonical Upwork job ciphertext (~02... or ~01...) from URL or string."""
    match = re.search(r'(~0[12][0-9a-zA-Z]+)', url_or_id.strip())
    if not match:
        raise ValueError(f'Cannot extract Upwork job ID (~02...) from: {url_or_id}')
    return match.group(1)


def canonical_job_url(url_or_id: str) -> str:
    """Return canonical https://upwork.com/jobs/~... URL for a job."""
    return f'https://upwork.com/jobs/{normalize_job_id(url_or_id)}'


def resolve_nuxt_devalue(arr: list, idx: int = 0, seen: set[int] | None = None):
    """Decode Nuxt 3 __NUXT_DATA__ devalue array into plain Python dicts/lists."""
    if seen is None:
        seen = set()
    if not isinstance(idx, int) or idx < 0 or idx >= len(arr) or idx in seen:
        return arr[idx] if isinstance(idx, int) and 0 <= idx < len(arr) else idx
    seen = seen | {idx}
    val = arr[idx]
    if isinstance(val, list):
        if (
            len(val) == 2
            and isinstance(val[0], str)
            and val[0] in ('Reactive', 'ShallowReactive', 'Ref', 'EmptyRef', 'Set', 'ShallowRef')
        ):
            return resolve_nuxt_devalue(arr, val[1], seen)
        return [resolve_nuxt_devalue(arr, x, seen) if isinstance(x, int) else x for x in val]
    if isinstance(val, dict):
        return {k: (resolve_nuxt_devalue(arr, v, seen) if isinstance(v, int) else v) for k, v in val.items()}
    return val


def format_month_year(iso_str: str | None) -> str:
    """Convert ISO timestamp like 2026-01-07T05:06:38.752Z to Jan 2026."""
    if not iso_str:
        return 'Present'
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return dt.strftime('%b %Y')
    except ValueError:
        return iso_str[:10]


def extract_client_names(work_history: list[dict]) -> list[dict]:
    """Identify likely client names from freelancer feedback comments."""
    patterns = [
        r'\bworking with ([A-Z][a-z]{2,15})\b',
        r'\bThank you,? ([A-Z][a-z]{2,15})\b',
        r'\b([A-Z][a-z]{2,15}) is (?:a |an )?(?:very |truly |super )?(?:nice|great|wonderful|excellent|good|supportive|easy|clear|amazing|awesome|fantastic|pleasure)',
        r'\b([A-Z][a-z]{2,15}) was (?:a )?(?:great|wonderful|excellent|very|easy|clear|supportive)',
        r'\b([A-Z][a-z]{2,15}) has been (?:a )?(?:great|wonderful|excellent|very|supportive)',
        r'\b([A-Z][a-z]{2,15}) is the best\b',
    ]
    stopwords = {
        'This', 'That', 'There', 'Client', 'Working', 'Thank', 'Thanks',
        'Everything', 'Communication', 'Overall', 'Project', 'Team', 'He', 'She', 'They',
    }
    found: dict[str, list[dict]] = {}
    for idx, item in enumerate(work_history, start=1):
        comment = ((item.get('feedbackToClient') or {}).get('comment') or '').strip()
        if not comment:
            continue
        seen_in_item: set[str] = set()
        for pat in patterns:
            for match in re.finditer(pat, comment):
                name = match.group(1)
                if name in stopwords or name in seen_in_item:
                    continue
                seen_in_item.add(name)
                found.setdefault(name, []).append({
                    'project_index': idx,
                    'project_title': (item.get('jobInfo') or {}).get('title') or f'Project {idx}',
                    'quote': comment,
                })
    return [{'name': k, 'mentions': v} for k, v in sorted(found.items(), key=lambda x: -len(x[1]))]


def extract_candidate_domains(texts: list[str]) -> list[str]:
    """Extract candidate client domains from job descriptions and related texts."""
    candidates: list[str] = []
    url_re = re.compile(r'https?://([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?:/[^\s"\'<>)]*)?')
    bare_re = re.compile(r'\b([a-zA-Z0-9-]+\.(?:com|co|org|net|io|ai|de|dk|uk|eu|pt|es|fr|nl|us|ca|au|shop|store))\b')
    for text in texts:
        if not text:
            continue
        for match in url_re.finditer(text):
            host = match.group(1).lower().lstrip('.')
            base = host[4:] if host.startswith('www.') else host
            if host not in IGNORED_CANDIDATE_DOMAINS and base not in IGNORED_CANDIDATE_DOMAINS:
                if base not in candidates:
                    candidates.append(base)
        for match in bare_re.finditer(text):
            host = match.group(1).lower()
            base = host[4:] if host.startswith('www.') else host
            if host not in IGNORED_CANDIDATE_DOMAINS and base not in IGNORED_CANDIDATE_DOMAINS:
                if base not in candidates:
                    candidates.append(base)
    return candidates


class _NoCookieOnCrossDomainRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req and 'upwork.com' not in newurl:
            new_req.headers.pop('Cookie', None)
            new_req.unredirected_hdrs.pop('Cookie', None)
        return new_req


async def _cdp_extract_async(
    job_id: str,
    cdp_port: int = 9222,
    fetch_related: bool = True,
    attachments_dir: Path | None = None,
) -> dict:
    import websockets

    with urllib.request.urlopen(f'http://127.0.0.1:{cdp_port}/json', timeout=5) as resp:
        tabs = json.loads(resp.read().decode('utf-8'))

    page_tabs = [t for t in tabs if t.get('type') == 'page' and 'upwork.com' in t.get('url', '')]
    target_tab = next((t for t in page_tabs if job_id in t.get('url', '')), None)
    host_tab = target_tab or (page_tabs[0] if page_tabs else None)
    if not host_tab:
        raise RuntimeError(f'No open Upwork page tab found on CDP port {cdp_port}')

    ws_url = host_tab['webSocketDebuggerUrl']
    async with websockets.connect(ws_url, max_size=50_000_000) as ws:
        if target_tab:
            expr = 'document.getElementById("__NUXT_DATA__")?.textContent || ""'
            await ws.send(json.dumps({
                'id': 1,
                'method': 'Runtime.evaluate',
                'params': {'expression': expr, 'returnByValue': True},
            }))
            raw_nuxt = json.loads(await ws.recv())['result']['result'].get('value', '')
        else:
            fetch_url = f'https://www.upwork.com/jobs/{job_id}'
            expr = f"""(async () => {{
                const r = await fetch({json.dumps(fetch_url)}, {{credentials: "include"}});
                const html = await r.text();
                const doc = new DOMParser().parseFromString(html, "text/html");
                return doc.getElementById("__NUXT_DATA__")?.textContent || "";
            }})()"""
            await ws.send(json.dumps({
                'id': 1,
                'method': 'Runtime.evaluate',
                'params': {'expression': expr, 'awaitPromise': True, 'returnByValue': True},
            }))
            raw_nuxt = json.loads(await ws.recv())['result']['result'].get('value', '')

        if not raw_nuxt:
            raise RuntimeError(f'Could not extract __NUXT_DATA__ for job {job_id}')

        root_data = resolve_nuxt_devalue(json.loads(raw_nuxt), 0)
        jd = (root_data.get('vuex') or {}).get('jobDetails') or {}
        job = jd.get('job')
        if not job:
            raise RuntimeError(
                f'Job {job_id} returned empty jobDetails via background fetch (private or closed listing). '
                f'Open https://www.upwork.com/jobs/{job_id} in a browser tab first.'
            )
        buyer = jd.get('buyer') or {}
        work_history = jd.get('workHistory') or []
        open_jobs = jd.get('openJobs') or []
        sands = jd.get('sands') or {}

        related_descriptions: dict[str, dict] = {}
        if fetch_related:
            related_cids: list[str] = []
            for item in work_history:
                cid = (item.get('jobInfo') or {}).get('ciphertext')
                if cid and cid not in related_cids:
                    related_cids.append(cid)
            for item in open_jobs:
                cid = item.get('ciphertext')
                if cid and cid not in related_cids:
                    related_cids.append(cid)

            for req_id, cid in enumerate(related_cids, start=10):
                rel_expr = f"""(async () => {{
                    const r = await fetch("https://www.upwork.com/jobs/{cid}", {{credentials: "include"}});
                    const html = await r.text();
                    const doc = new DOMParser().parseFromString(html, "text/html");
                    return doc.getElementById("__NUXT_DATA__")?.textContent || "";
                }})()"""
                await ws.send(json.dumps({
                    'id': req_id,
                    'method': 'Runtime.evaluate',
                    'params': {'expression': rel_expr, 'awaitPromise': True, 'returnByValue': True},
                }))
                rel_raw = json.loads(await ws.recv())['result']['result'].get('value', '')
                if rel_raw:
                    try:
                        rel_jd = resolve_nuxt_devalue(json.loads(rel_raw), 0)['vuex']['jobDetails']
                        rel_job = rel_jd.get('job') or {}
                        related_descriptions[cid] = {
                            'title': rel_job.get('title'),
                            'description': rel_job.get('description'),
                        }
                    except Exception:
                        pass

        saved_attachments: list[str] = []
        attachments = job.get('attachments') or []
        if attachments and attachments_dir is not None:
            attachments_dir.mkdir(parents=True, exist_ok=True)
            await ws.send(json.dumps({
                'id': 900,
                'method': 'Network.getCookies',
                'params': {'urls': ['https://www.upwork.com']},
            }))
            cookies = json.loads(await ws.recv())['result']['cookies']
            cookie_hdr = '; '.join(f"{c['name']}={c['value']}" for c in cookies)
            await ws.send(json.dumps({
                'id': 901,
                'method': 'Runtime.evaluate',
                'params': {'expression': 'navigator.userAgent', 'returnByValue': True},
            }))
            ua = json.loads(await ws.recv())['result']['result'].get('value', 'Mozilla/5.0')
            opener = urllib.request.build_opener(_NoCookieOnCrossDomainRedirect())
            for att in attachments:
                uri = att.get('uri')
                fname = att.get('fileName')
                if not uri or not fname:
                    continue
                url = 'https://www.upwork.com' + uri if uri.startswith('/') else uri
                req = urllib.request.Request(url, headers={'Cookie': cookie_hdr, 'User-Agent': ua})
                data = opener.open(req, timeout=20).read()
                dest = attachments_dir / fname
                dest.write_bytes(data)
                saved_attachments.append(str(dest))

    skills: list[str] = []
    for group in sands.get('ontologySkills') or []:
        for child in group.get('children') or []:
            name = (child.get('name') or '').strip()
            if name and name not in skills:
                skills.append(name)
    for add in sands.get('additionalSkills') or []:
        name = (add.get('name') or '').strip()
        if name and name not in skills:
            skills.append(name)

    all_texts = [job.get('description') or '']
    for rel in related_descriptions.values():
        if rel.get('description'):
            all_texts.append(rel['description'])

    return {
        'job_id': job.get('ciphertext') or job_id,
        'title': job.get('title') or '',
        'url': canonical_job_url(job.get('ciphertext') or job_id),
        'description': job.get('description') or '',
        'posted_on': job.get('postedOn') or job.get('publishTime'),
        'workload': job.get('workload'),
        'duration_label': job.get('durationLabel'),
        'contractor_tier': job.get('contractorTier'),
        'budget': job.get('budget'),
        'extended_budget': job.get('extendedBudgetInfo'),
        'client_activity': job.get('clientActivity') or {},
        'questions': [q.get('question') for q in (job.get('questions') or []) if q.get('question')],
        'attachments': attachments,
        'saved_attachments': saved_attachments,
        'skills': skills,
        'buyer': buyer,
        'work_history': work_history,
        'open_jobs': open_jobs,
        'related_descriptions': related_descriptions,
        'client_names': extract_client_names(work_history),
        'candidate_domains': extract_candidate_domains(all_texts),
    }


def extract_upwork_job(
    url_or_id: str,
    cdp_port: int = 9222,
    fetch_related: bool = True,
    attachments_dir: Path | None = None,
) -> dict:
    """Synchronously extract full Upwork job data via CDP."""
    job_id = normalize_job_id(url_or_id)
    return asyncio.run(_cdp_extract_async(job_id, cdp_port, fetch_related, attachments_dir))


def _link_dir(link_path: Path, target_dir: Path):
    """Create a directory symlink (or Windows junction fallback) to target_dir."""
    if link_path.is_symlink():
        if link_path.resolve() == target_dir.resolve():
            return
        link_path.unlink()
    elif link_path.exists():
        shutil.rmtree(link_path)
    try:
        link_path.symlink_to(target_dir, target_is_directory=True)
    except OSError:
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(link_path), str(target_dir)], check=True, capture_output=True)


def _link_file(link_path: Path, target_file: Path):
    """Create a file symlink (or hardlink/copy fallback) to target_file."""
    if link_path.is_symlink():
        if link_path.resolve() == target_file.resolve():
            return
        link_path.unlink()
    elif link_path.exists():
        link_path.unlink()
    try:
        link_path.symlink_to(target_file)
    except OSError:
        try:
            link_path.hardlink_to(target_file)
        except OSError:
            shutil.copy2(target_file, link_path)


def default_context_config() -> dict:
    return {
        'version': 1,
        'output': 'ꙮ/0/Context.md',
        'sections': [
            {'title': 'Project Overview', 'files': ['.md'], 'optional': True},
            {'title': 'Manual Knowledge Base (KB)', 'globs': ['KB/*.md', 'KB/**/*.md'], 'optional': True},
            {'title': 'Agent Knowledge Base (ꘖ/KB)', 'globs': ['ꘖ/KB/*.md', 'ꘖ/KB/**/*.md'], 'optional': True},
            {'title': 'Analysis (ꙮ/1 - Анализ)', 'journals': ['ꙮ/1 - Анализ'], 'optional': True},
            {'title': 'Proposals (result)', 'globs': ['result/**/final/*.md', 'result/**/final.md'], 'optional': True},
            {
                'title': 'Correspondence',
                'optional': True,
                'letters': [
                    {'root': 'Letters/my', 'author': 'Consultant', 'languages': ['EN', 'RU']},
                    {'root': 'Letters/client', 'author': 'Client', 'languages': ['EN', 'RU']},
                ],
            },
        ],
    }


def link_project_agents(
    project_root: Path,
    primary_agents_dir: Path = PRIMARY_AGENTS_DIR,
    job_url: str | None = None,
    domain_or_topic: str | None = None,
):
    """Configure <project>/.agents to share universal rules/scripts/skills/agents from primary_agents_dir while supporting local 90-project.md rules."""
    project_root = Path(project_root).resolve()
    primary_agents_dir = Path(primary_agents_dir).resolve()
    agents_dir = project_root / '.agents'

    if agents_dir.is_symlink():
        agents_dir.unlink()
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Remove legacy .agents/data if empty or migrate to ꘖ/data
    legacy_data = agents_dir / 'data'
    if legacy_data.exists() and not legacy_data.is_symlink():
        shutil.rmtree(legacy_data, ignore_errors=True)

    # Migrate legacy ꙮ/1 - Анализ/.journal into ꘖ/data/.journal if present
    legacy_journal = project_root / 'ꙮ' / '1 - Анализ' / '.journal'
    if legacy_journal.is_dir():
        target_journal = project_root / 'ꘖ' / 'data' / '.journal'
        target_journal.mkdir(parents=True, exist_ok=True)
        for item in legacy_journal.iterdir():
            dest = target_journal / item.name
            if not dest.exists():
                shutil.move(str(item), str(dest))
        shutil.rmtree(legacy_journal, ignore_errors=True)

    # 1. Link shared directories
    for subdir in ('scripts', 'tests', 'skills', 'agents'):
        target = primary_agents_dir / subdir
        if target.exists():
            _link_dir(agents_dir / subdir, target)

    # 2. Link shared root files
    for fname in ('README.md', '.gitignore', 'context.example.json'):
        target = primary_agents_dir / fname
        if target.exists():
            _link_file(agents_dir / fname, target)

    # 3. Create real .agents/rules/ directory with linked global rules (00-..09-) + local 90-project.md
    rules_dir = agents_dir / 'rules'
    if rules_dir.is_symlink():
        rules_dir.unlink()
    rules_dir.mkdir(parents=True, exist_ok=True)

    primary_rules_dir = primary_agents_dir / 'rules'
    if primary_rules_dir.is_dir():
        for rule_file in sorted(primary_rules_dir.glob('*.md')):
            if not rule_file.name.startswith('9'):
                _link_file(rules_dir / rule_file.name, rule_file)

    local_rule = rules_dir / '90-project.md'
    if not local_rule.exists():
        lines = [
            '---',
            'trigger: always_on',
            'description: "Специфичные правила и параметры текущего проекта Upwork"',
            '---',
            '',
            '# Проектные правила (`90-project`)',
            '',
        ]
        if job_url:
            lines.append(f'Целевая вакансия Upwork: `{job_url}`.')
        if domain_or_topic:
            lines.append(f'Идентификатор / домен проекта: `{domain_or_topic}`.')
        lines.extend([
            'База знаний пользователя расположена в `KB/` (`KB/Project.md` заполняется только при первичном анализе и далее не изменяется).',
            'База знаний агента расположена в `ꘖ/KB/`, служебные и временные файлы — в `ꘖ/data/`, журнал анализа — в `ꙮ/1 - Анализ/`, полный контекст — в `ꙮ/0/Context.md`.',
            '',
        ])
        local_rule.write_text('\n'.join(lines), encoding='utf-8')

    # 4. Write rules.json and skills.json manifests for Antigravity 2.0
    primary_posix = primary_agents_dir.as_posix()
    rules_json = {
        'entries': [
            {'path': f'{primary_posix}/rules'},
            {'path': 'rules'},
        ]
    }
    (agents_dir / 'rules.json').write_text(json.dumps(rules_json, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    skills_json = {
        'entries': [
            {'path': f'{primary_posix}/skills'},
        ]
    }
    (agents_dir / 'skills.json').write_text(json.dumps(skills_json, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    # 5. Write or upgrade local .agents/context.json
    context_json_path = agents_dir / 'context.json'
    context_cfg = default_context_config()
    if context_json_path.exists():
        try:
            existing_cfg = json.loads(context_json_path.read_text(encoding='utf-8'))
            titles = {s.get('title') for s in existing_cfg.get('sections') or []}
            if 'Analysis (ꙮ/1 - Анализ)' not in titles:
                context_json_path.write_text(json.dumps(context_cfg, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        except Exception:
            context_json_path.write_text(json.dumps(context_cfg, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    else:
        context_json_path.write_text(json.dumps(context_cfg, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


_SENTENCE_SPLIT_RE = re.compile(
    r'(?<!\be\.g)(?<!\bi\.e)(?<!\bvs)(?<!\betc)(?<!\bMr)(?<!\bDr)(?<!\bSt)(?<!\bNB)(?<=[.!?])\s+(?=[A-ZА-ЯЁ"«(])'
)


def split_sentences_one_per_line(text: str) -> list[str]:
    """Split a paragraph into individual sentences (one per line per DOC-6)."""
    parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(text.strip()) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def structure_job_description(description: str, questions: list[str] | None = None) -> str:
    """Format a raw Upwork job description into clean structured Markdown (headings, lists, one sentence per line)."""
    raw = (description or '').replace('\r\n', '\n').replace('\r', '\n').strip()
    lines = [line.strip() for line in raw.split('\n')]
    out_lines: list[str] = []

    for idx, line in enumerate(lines):
        if not line:
            if out_lines and out_lines[-1] != '':
                out_lines.append('')
            continue

        # Normalize bullet points: "• foo", "* foo", "-foo" -> "- foo"
        bullet_match = re.match(r'^(?:[•*]|\-(?=[A-Za-zА-ЯЁа-яё0-9"\'`])|\-\s+)\s*(.+)$', line)
        if bullet_match:
            body = bullet_match.group(1).strip()
            sentences = split_sentences_one_per_line(body)
            if sentences:
                out_lines.append(f'- {sentences[0]}')
                for extra in sentences[1:]:
                    out_lines.append(extra)
            continue

        # Check if standalone section header line
        prev_empty = (idx == 0) or (not lines[idx - 1])
        words = line.split()
        is_heading = (
            prev_empty
            and 1 <= len(words) <= 8
            and len(line) <= 70
            and line[0].isupper()
            and not line.startswith(('http://', 'https://', '#', '-'))
            and not re.match(r'^\d+[.)]\s', line)
            and (
                line.endswith(':')
                or (
                    not line.endswith(('.', '!', '?', ';', ','))
                    and idx + 1 < len(lines)
                )
            )
        )
        # Avoid turning short normal sentences starting with "We ", "I ", "The ", "This ", "Please ", "See " into headings
        if is_heading and words[0].lower() in ('we', "we're", 'i', 'the', 'this', 'there', 'please', 'see', 'as', 'and', 'so', 'if', 'in', 'for', 'most', 'all'):
            if not line.endswith(':'):
                is_heading = False

        if is_heading:
            if out_lines and out_lines[-1] != '':
                out_lines.append('')
            heading_text = line[:-1].strip() if line.endswith(':') else line
            out_lines.append(f'# {heading_text}')
            continue

        # Standard paragraph line: split into one sentence per line (DOC-6)
        for sentence in split_sentences_one_per_line(line):
            out_lines.append(sentence)

    while out_lines and out_lines[-1] == '':
        out_lines.pop()

    if questions:
        clean_q = [q.strip() for q in questions if q and q.strip()]
        if clean_q:
            if out_lines:
                out_lines.append('')
            out_lines.append('# Questions')
            for q in clean_q:
                out_lines.append(f'- {q}')

    return '\n'.join(out_lines)


def collect_unique_public_past_jobs(data: dict) -> list[dict]:
    """Return unique public past/open jobs with ciphertext and description for KB/Project.md §3."""
    current_cid = data.get('job_id')
    rel_descs = data.get('related_descriptions') or {}
    seen_cids: set[str] = set()
    public_jobs: list[dict] = []

    for item in data.get('work_history') or []:
        ji = item.get('jobInfo') or {}
        cid = ji.get('ciphertext')
        if not cid or cid == current_cid or cid in seen_cids:
            continue
        rel = rel_descs.get(cid) or {}
        desc = (rel.get('description') or '').strip()
        title = (ji.get('title') or rel.get('title') or '').strip()
        if not desc:
            continue
        seen_cids.add(cid)
        public_jobs.append({
            'ciphertext': cid,
            'url': canonical_job_url(cid),
            'title': title,
            'description': desc,
        })

    for o_item in data.get('open_jobs') or []:
        cid = o_item.get('ciphertext')
        if not cid or cid == current_cid or cid in seen_cids:
            continue
        rel = rel_descs.get(cid) or {}
        desc = (rel.get('description') or '').strip()
        title = (o_item.get('title') or rel.get('title') or '').strip()
        if not desc:
            continue
        seen_cids.add(cid)
        public_jobs.append({
            'ciphertext': cid,
            'url': canonical_job_url(cid),
            'title': title,
            'description': desc,
        })

    return public_jobs


def format_kb_project_md(
    data: dict,
    domain: str | None = None,
    site_note: str | None = None,
    client_name_override: str | None = None,
) -> str:
    """Format KB/Project.md strictly following the user's reference schema (§§23-24)."""
    buyer = data.get('buyer') or {}
    loc = buyer.get('location') or {}

    # 1.1 Имя
    client_names = data.get('client_names') or []
    if client_name_override:
        name_str = client_name_override.strip()
    elif client_names:
        name_str = client_names[0]['name'].strip()
    else:
        name_str = 'неизвестно'

    # 1.2 Местоположение
    country = (loc.get('country') or 'неизвестно').strip()
    city = (loc.get('city') or '').strip()
    loc_lines = [country]
    if city:
        loc_lines.append(city)

    # 1.3 Сайт
    if domain and '.' in domain and ' ' not in domain:
        site_str = domain if domain.startswith(('http://', 'https://')) else f'https://{domain}'
    elif len(data.get('candidate_domains') or []) == 1:
        site_str = f'https://{data["candidate_domains"][0]}'
    else:
        site_str = 'неизвестно'

    # 2. Текущий проект клиента
    job_url = canonical_job_url(data.get('job_id') or data.get('url') or '')
    job_title = (data.get('title') or '').strip()
    structured_desc = structure_job_description(data.get('description') or '', data.get('questions'))

    lines = [
        '# 1. Клиент',
        '## 1.1 Имя',
        name_str,
        '',
        '## 1.2 Местоположение',
        *loc_lines,
        '',
        '## 1.3 Сайт',
        site_str,
        '',
        '# 2. Текущий проект клиента',
        job_url,
        '~~~markdown',
        job_title,
        '#',
        structured_desc,
        '~~~',
        '',
        '# 3. Прошлые проекты клиента',
        '## 3.0',
        'Эти проекты относятся к тому же сайту, что и §2.',
        '##',
        'Используй эти проекты для понимания контекста.',
        'Работа над этими проектами — вне рамок текущей задачи.',
    ]

    for idx, pjob in enumerate(collect_unique_public_past_jobs(data), start=1):
        p_structured = structure_job_description(pjob['description'])
        lines.extend([
            '',
            f'## 3.{idx}',
            pjob['url'],
            '~~~markdown',
            pjob['title'],
            '#',
            p_structured,
            '~~~',
        ])

    return '\n'.join(lines) + '\n'


def populate_agent_kb(
    project_root: Path,
    data: dict,
    domain: str | None = None,
    site_note: str | None = None,
    date_str: str | None = None,
    overwrite_curated: bool = False,
):
    """Port initial data from KB/Project.md and Upwork extraction into ꘖ/KB/ modules (§24, KB-1..KB-5, DOC-6)."""
    kb_dir = project_root / 'ꘖ' / 'KB'
    kb_dir.mkdir(parents=True, exist_ok=True)
    obs_date = date_str or datetime.now().strftime('%Y-%m-%d')
    job_url = canonical_job_url(data.get('job_id') or data.get('url') or '')

    buyer = data.get('buyer') or {}
    loc = buyer.get('location') or {}
    stats = buyer.get('stats') or {}
    jobs_stat = buyer.get('jobs') or {}
    company = (buyer.get('company') or {}).get('profile') or {}
    client_names = data.get('client_names') or []

    # 1. Client.md
    if client_names:
        top = client_names[0]
        refs = ', '.join(f'`§2.{m["project_index"]}`' for m in top['mentions'][:5])
        name_line = f'- **Имя**: `{top["name"]}` (подтверждается отзывами исполнителей в [Projects.md](Projects.md): {refs}).'
    else:
        name_line = '- **Имя**: не указано в открытых отзывах на странице вакансии.'

    country = loc.get('country') or 'Unknown'
    city = loc.get('city') or ''
    tz = loc.get('countryTimezone') or ''
    loc_str = f'{city}, {country}' if city else country
    if tz:
        loc_str += f' (часовой пояс `{tz}`)'

    posted_cnt = jobs_stat.get('postedCount') or 0
    open_cnt = jobs_stat.get('openCount') or 0
    total_hires = stats.get('totalJobsWithHires') or 0
    hire_rate = min(100, round((total_hires / posted_cnt) * 100)) if posted_cnt else 0
    total_spent = (stats.get('totalCharges') or {}).get('amount') or 0
    total_assign = stats.get('totalAssignments') or 0
    active_assign = stats.get('activeAssignmentsCount') or 0
    avg_rate = (buyer.get('avgHourlyJobsRate') or {}).get('amount') or 0
    hours_cnt = stats.get('hoursCount') or 0
    industry = company.get('industry') or 'не указана'
    comp_size = company.get('size') or 'не указан'
    contract_date = format_month_year((buyer.get('company') or {}).get('contractDate'))

    client_lines = [
        '# 1. Клиент и компания',
        '',
        '## 1.1. Контактные данные и локация',
        '- **Статус**: `подтверждено`.',
        f'- **Дата наблюдения**: `{obs_date}`.',
        f'- **Источники**: [KB/Project.md](../../KB/Project.md) и карточка вакансии {job_url}.',
        name_line,
        f'- **Локация**: {loc_str}.',
        f'- **Отрасль и размер компании**: отрасль `{industry}`, размер компании в профиле Upwork — `{comp_size}`.',
        '',
        '## 1.2. Метрики аккаунта Upwork',
        '- **Статус**: `подтверждено`.',
        f'- **Дата наблюдения**: `{obs_date}`.',
        f'- **Источник**: карточка вакансии {job_url}.',
        f'- **Дата регистрации на Upwork**: `{contract_date}`.',
        f'- **Опубликовано вакансий**: `{posted_cnt}` (`{hire_rate}% hire rate`, открытых вакансий: `{open_cnt}`).',
        f'- **Общие затраты**: `${total_spent:,.2f}` (`{total_assign}` наймов, `{active_assign}` активных).',
        f'- **Средняя почасовая ставка**: `${avg_rate:.2f}/hr` (`{hours_cnt:,.2f}` часов).',
        '',
    ]
    client_path = kb_dir / 'Client.md'
    if overwrite_curated or not client_path.exists():
        client_path.write_text('\n'.join(client_lines), encoding='utf-8')

    # 2. Website.md
    is_valid_domain = bool(domain and '.' in domain and ' ' not in domain)
    site_url = f'https://{domain}' if is_valid_domain else 'не установлен однозначно'
    site_status = 'подтверждено' if is_valid_domain else 'гипотеза'
    website_lines = [
        '# 1. Сайт и техническая инфраструктура клиента',
        '',
        '## 1.1. Основной домен',
        f'- **Статус**: `{site_status}`.',
        f'- **Дата наблюдения**: `{obs_date}`.',
        f'- **Источники**: [KB/Project.md](../../KB/Project.md) и {job_url}.',
        f'- **Целевой сайт**: {site_url}.',
    ]
    if site_note:
        for s in split_sentences_one_per_line(site_note):
            website_lines.append(f'- **Основание идентификации**: {s}')
    website_lines.extend([
        '',
        '## 1.2. Заявленный технологический стек (из текущей вакансии)',
        '- **Статус**: `подтверждено`.',
        f'- **Дата наблюдения**: `{obs_date}`.',
        f'- **Источник**: карточка вакансии {job_url}.',
        '- **Теги вакансии**: ' + (', '.join(f'`{s}`' for s in (data.get('skills') or [])) or 'не указаны') + '.',
        '',
    ])
    website_path = kb_dir / 'Website.md'
    if overwrite_curated or not website_path.exists():
        website_path.write_text('\n'.join(website_lines), encoding='utf-8')

    # 3. Projects.md — full work_history + open_jobs + current job details
    tier_map = {1: 'Entry level', 2: 'Intermediate', 3: 'Expert'}
    tier_label = tier_map.get(data.get('contractor_tier'), str(data.get('contractor_tier') or 'Not specified'))
    workload = data.get('workload') or 'Not Sure'
    duration = data.get('duration_label') or 'Not specified'
    budget_amt = (data.get('budget') or {}).get('amount')
    act = data.get('client_activity') or {}

    proj_lines = [
        '# 1. Текущий проект клиента на Upwork',
        '',
        f'- **Название**: `{data.get("title") or ""}`.',
        f'- **Ссылка**: {job_url}.',
        '- **Статус**: `подтверждено`.',
        f'- **Дата наблюдения**: `{obs_date}`.',
        f'- **Занятость, длительность и уровень**: `{workload}`, `{duration}`, `{tier_label}`.',
    ]
    if budget_amt:
        proj_lines.append(f'- **Фиксированный бюджет**: `${budget_amt:,.2f}`.')
    if act:
        proj_lines.append(
            f'- **Активность по вакансии**: откликов `{act.get("totalApplicants", "N/A")}`, '
            f'интервью `{act.get("totalInvitedToInterview", 0)}`, '
            f'приглашений отправлено `{act.get("invitationsSent", 0)}`, '
            f'неотвеченных `{act.get("unansweredInvites", 0)}`.'
        )
    if data.get('skills'):
        proj_lines.append('- **Теги навыков**: ' + ', '.join(f'`{s}`' for s in data['skills']) + '.')
    if data.get('attachments'):
        att_str = ', '.join(f'`{a.get("fileName")}` ({a.get("length", 0)} байт)' for a in data['attachments'])
        proj_lines.append(f'- **Вложения**: {att_str}.')
    if data.get('questions'):
        proj_lines.append('- **Вопросы при подаче заявки**:')
        for q in data['questions']:
            proj_lines.append(f'  1. `{q}`')

    wh = data.get('work_history') or []
    rel_descs = data.get('related_descriptions') or {}
    proj_lines.extend([
        '',
        '# 2. Прошлые и активные контракты клиента на Upwork',
        '',
        '- **Статус**: `подтверждено`.',
        f'- **Дата наблюдения**: `{obs_date}`.',
        f'- **Источник**: блок истории клиента в карточке {job_url} (всего записей: `{len(wh)}`).',
    ])

    for idx, item in enumerate(wh, start=1):
        ji = item.get('jobInfo') or {}
        title = ji.get('title') or f'Project {idx}'
        cid = ji.get('ciphertext')
        start_s = format_month_year(item.get('startDate'))
        end_s = format_month_year(item.get('endDate')) if item.get('endDate') else 'Present (Job in progress)'
        total_charge = item.get('totalCharge')
        total_hours = item.get('totalHours')
        rate_amt = (item.get('rate') or {}).get('amount')
        if total_hours and rate_amt:
            budget_str = f'`{round(total_hours)} hrs @ ${rate_amt:.2f}/hr`, оплачено `${total_charge or 0:,.2f}`'
        elif total_charge:
            budget_str = f'Fixed-price, оплачено `${total_charge:,.2f}`'
        elif rate_amt:
            budget_str = f'Hourly `@ ${rate_amt:.2f}/hr`'
        else:
            budget_str = 'не указан'

        ci = item.get('contractorInfo') or {}
        c_name = ci.get('contractorName') or 'не указан'
        c_cid = ci.get('ciphertext')
        c_part = f'`{c_name}` (https://upwork.com/freelancers/{c_cid})' if c_cid else f'`{c_name}`'

        proj_lines.extend([
            '',
            f'## 2.{idx}. {title}',
            f'- **Ссылка**: {canonical_job_url(cid) if cid else "приватная публикация (`ciphertext: null`)"}.',
            f'- **Период и исполнитель**: `{start_s} – {end_s}`, исполнитель {c_part}.',
            f'- **Бюджет и оплата**: {budget_str}.',
        ])
        fc = ((item.get('feedbackToClient') or {}).get('comment') or '').strip()
        fc_score = (item.get('feedbackToClient') or {}).get('score')
        if fc:
            fc_one_line = ' '.join(fc.splitlines())
            proj_lines.append(f'- **Отзыв исполнителя о клиенте (`{fc_score}`)**: «{fc_one_line}».')
        cc = ((item.get('feedback') or {}).get('comment') or '').strip()
        cc_score = (item.get('feedback') or {}).get('score')
        if cc:
            cc_one_line = ' '.join(cc.splitlines())
            proj_lines.append(f'- **Отзыв клиента об исполнителе (`{cc_score}`)**: «{cc_one_line}».')
        if cid and (rel_descs.get(cid) or {}).get('description'):
            raw_d = ' '.join((rel_descs[cid]['description'] or '').split())
            proj_lines.append(f'- **Описание вакансии**: «{raw_d}».')

    open_jobs = data.get('open_jobs') or []
    if open_jobs:
        proj_lines.extend([
            '',
            '# 3. Открытые параллельные вакансии клиента на Upwork',
            '',
            '- **Статус**: `подтверждено`.',
            f'- **Дата наблюдения**: `{obs_date}`.',
            f'- **Источник**: блок `Other open jobs by this client` в карточке {job_url}.',
        ])
        for o_idx, o_item in enumerate(open_jobs, start=1):
            o_title = o_item.get('title') or f'Open Job {o_idx}'
            o_cid = o_item.get('ciphertext')
            proj_lines.extend([
                '',
                f'## 3.{o_idx}. {o_title}',
                f'- **Ссылка**: {canonical_job_url(o_cid) if o_cid else "не указана"}.',
            ])
            if o_cid and (rel_descs.get(o_cid) or {}).get('description'):
                raw_d = ' '.join((rel_descs[o_cid]['description'] or '').split())
                proj_lines.append(f'- **Описание вакансии**: «{raw_d}».')

    proj_lines.append('')
    (kb_dir / 'Projects.md').write_text('\n'.join(proj_lines), encoding='utf-8')

    # 4. Glossary.md (KB-4: alphabetical numbered headings without tables + source)
    glossary_path = kb_dir / 'Glossary.md'
    if overwrite_curated or not glossary_path.exists():
        raw_skills = [str(s).strip() for s in (data.get('skills') or []) if str(s).strip()]
        sorted_terms = sorted(set(raw_skills), key=lambda x: x.casefold()) or ['Upwork Job Ciphertext']
        g_lines = [
            '# Глоссарий предметных терминов',
            '',
            'Разделы упорядочены по алфавиту согласно правилу `KB-4`.',
        ]
        for g_idx, term in enumerate(sorted_terms, start=1):
            g_lines.extend([
                '',
                f'## {g_idx}. {term}',
                f'Предметный термин и компетенция, заявленные клиентом в карточке вакансии (`{term}`).',
                f'- **Источник**: {job_url}.',
            ])
        g_lines.append('')
        glossary_path.write_text('\n'.join(g_lines), encoding='utf-8')

    # 5. Overview .md
    overview_path = kb_dir / '.md'
    if overwrite_curated or not overview_path.exists():
        overview_md = '\n'.join([
            f'# Обзор базы знаний (`ꘖ/KB`): {domain or data.get("title") or "Проект"}',
            '',
            f'Дата актуализации: `{obs_date}`.',
            '',
            '# 1. Профильные модули',
            '',
            '1. [Клиент и компания (`Client.md`)](Client.md) — профиль клиента, локация, имена из отзывов и статистика аккаунта Upwork.',
            '1. [Сайт и техническая инфраструктура (`Website.md`)](Website.md) — основной домен клиента и технологический стек.',
            '1. [Проекты клиента на Upwork (`Projects.md`)](Projects.md) — текущий проект, полная история контрактов и открытые вакансии.',
            '1. [Глоссарий (`Glossary.md`)](Glossary.md) — определения предметных терминов в алфавитном порядке с источниками.',
            '1. [Первичное описание (`KB/Project.md`)](../../KB/Project.md) — неизменяемая выгрузка проекта при первичном анализе (`KB-1.1`).',
            '',
        ])
        overview_path.write_text(overview_md, encoding='utf-8')


def register_antigravity_project(
    project_dir: Path,
    domain_or_topic: str,
    date_str: str | None = None,
    projects_dir: Path = ANTIGRAVITY_PROJECTS_DIR,
    folders_json_path: Path = ANTIGRAVITY_FOLDERS_JSON,
) -> dict | None:
    """Register project in Antigravity (%USERPROFILE%/.gemini/config/projects/<uuid>.json) and assign it in Folders/code/folders.json (§4)."""
    project_dir = Path(project_dir).resolve()
    if date_str:
        parts = re.split(r'[-/\\.]', date_str.strip())
        yyyy, mm, dd = parts[0], f'{int(parts[1]):02d}', f'{int(parts[2]):02d}'
    else:
        try:
            dd = project_dir.parent.name
            mm = project_dir.parent.parent.name
            yyyy = project_dir.parent.parent.parent.name
            if not (yyyy.isdigit() and mm.isdigit() and dd.isdigit()):
                raise ValueError
        except Exception:
            now = datetime.now()
            yyyy, mm, dd = f'{now.year:04d}', f'{now.month:02d}', f'{now.day:02d}'

    project_name = f'{domain_or_topic} - U.P.{yyyy}.{mm}.{dd}'
    folder_uri = project_dir.as_posix()
    day_prefix = project_dir.parent.as_posix().lower() + '/'
    m_num = re.match(r'^(\d+)\s*-\s*', project_dir.name)
    num_prefix = f'{day_prefix}{m_num.group(1)} - ' if m_num else None

    projects_dir = Path(projects_dir)
    projects_dir.mkdir(parents=True, exist_ok=True)

    proj_id: str | None = None
    proj_file: Path | None = None
    proj_payload: dict | None = None

    for candidate in sorted(projects_dir.glob('*.json')):
        try:
            cdata = json.loads(candidate.read_text(encoding='utf-8'))
            resources = (cdata.get('projectResources') or {}).get('resources') or []
            for res in resources:
                uri = (res.get('folderUri') or '').replace('\\', '/')
                if uri.lower() == folder_uri.lower() or (num_prefix and uri.lower().startswith(num_prefix)):
                    proj_id = cdata.get('id') or candidate.stem
                    proj_file = candidate
                    proj_payload = cdata
                    break
            if proj_id:
                break
        except Exception:
            continue

    if proj_id is None:
        proj_id = str(uuid.uuid4())
        proj_file = projects_dir / f'{proj_id}.json'
        proj_payload = {
            'id': proj_id,
            'name': project_name,
            'projectResources': {
                'resources': [
                    {'folderUri': folder_uri}
                ]
            },
            'settings': {},
            'isWorkspaceOnly': False,
        }
    else:
        proj_payload['name'] = project_name
        proj_payload['projectResources'] = {'resources': [{'folderUri': folder_uri}]}

    replace_bytes(proj_file, (json.dumps(proj_payload, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))

    assigned_folder_id: str | None = None
    folders_json_path = Path(folders_json_path)
    if folders_json_path.is_file():
        fdata = json.loads(folders_json_path.read_text(encoding='utf-8'))
        folders_list: list[dict] = fdata.setdefault('folders', [])
        assignments: dict = fdata.setdefault('assignments', {})

        parent_id = None
        for seg in ('Upwork', 'Proposals', yyyy, mm, dd):
            found_folder = next(
                (f for f in folders_list if f.get('name') == seg and f.get('parentId') == parent_id),
                None,
            )
            if found_folder is None:
                existing_nums = [
                    int(m.group(1))
                    for f in folders_list
                    if (m := re.match(r'^folder-(\d+)$', str(f.get('id') or '')))
                ]
                next_folder_num = (max(existing_nums) + 1) if existing_nums else 1
                sibling_orders = [
                    int(f.get('order', 0))
                    for f in folders_list
                    if f.get('parentId') == parent_id
                ]
                next_order = (max(sibling_orders) + 1) if sibling_orders else 0
                found_folder = {
                    'id': f'folder-{next_folder_num}',
                    'name': seg,
                    'parentId': parent_id,
                    'order': next_order,
                }
                folders_list.append(found_folder)
            parent_id = found_folder['id']

        assigned_folder_id = parent_id
        if assignments.get(proj_id) != assigned_folder_id:
            assignments[proj_id] = assigned_folder_id
            replace_bytes(folders_json_path, (json.dumps(fdata, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))

    return {
        'project_id': proj_id,
        'project_name': project_name,
        'project_file': str(proj_file),
        'folder_id': assigned_folder_id,
    }


def resolve_or_create_project_dir(
    job_id: str,
    domain_or_topic: str,
    date_str: str | None = None,
    daily_root: Path = DAILY_PROPOSALS_ROOT,
) -> Path:
    """Find existing daily project folder for job_id or create the next <N> - <domain_or_topic> folder (§15)."""
    if date_str:
        parts = re.split(r'[-/\\]', date_str.strip())
        day_dir = Path(daily_root) / parts[0] / parts[1] / parts[2]
    else:
        now = datetime.now()
        day_dir = Path(daily_root) / f'{now.year:04d}' / f'{now.month:02d}' / f'{now.day:02d}'

    day_dir.mkdir(parents=True, exist_ok=True)

    existing_n: list[int] = []
    matched_dir: Path | None = None
    matched_n: int | None = None

    for child in sorted(day_dir.iterdir()):
        if not child.is_dir():
            continue
        m = re.match(r'^(\d+)\s*-\s*(.+)$', child.name)
        if not m:
            continue
        n = int(m.group(1))
        existing_n.append(n)
        md_file = child / '.md'
        if md_file.is_file():
            content = md_file.read_text(encoding='utf-8', errors='replace')
            if job_id in content:
                matched_dir = child
                matched_n = n

    if matched_dir is not None and matched_n is not None:
        desired_name = f'{matched_n} - {domain_or_topic}'
        if matched_dir.name != desired_name:
            target_dir = day_dir / desired_name
            if not target_dir.exists():
                matched_dir.rename(target_dir)
                return target_dir
        return matched_dir

    next_n = (max(existing_n) + 1) if existing_n else 1
    project_dir = day_dir / f'{next_n} - {domain_or_topic}'
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def initialize_upwork_project(
    url_or_id: str,
    domain_or_topic: str | None = None,
    site_note: str | None = None,
    date_str: str | None = None,
    daily_root: Path = DAILY_PROPOSALS_ROOT,
    primary_agents_dir: Path = PRIMARY_AGENTS_DIR,
    cdp_port: int = 9222,
    extracted_data: dict | None = None,
    force_kb: bool = False,
    register_antigravity: bool | None = None,
    antigravity_projects_dir: Path = ANTIGRAVITY_PROJECTS_DIR,
    antigravity_folders_json: Path = ANTIGRAVITY_FOLDERS_JSON,
) -> dict:
    """End-to-end deterministic initialization of an Upwork project directory (§§4, 15-25)."""
    job_id = normalize_job_id(url_or_id)
    data = extracted_data or extract_upwork_job(job_id, cdp_port=cdp_port, fetch_related=True)

    chosen_name = domain_or_topic
    if not chosen_name:
        if len(data.get('candidate_domains') or []) == 1:
            chosen_name = data['candidate_domains'][0]
        else:
            title_words = re.findall(r'[A-Za-z0-9]+', data.get('title') or 'Upwork Project')
            chosen_name = ' '.join(title_words[:4]) or job_id

    project_dir = resolve_or_create_project_dir(
        job_id=job_id,
        domain_or_topic=chosen_name,
        date_str=date_str,
        daily_root=daily_root,
    )

    # Create standard directories (§§17-21)
    (project_dir / 'KB').mkdir(parents=True, exist_ok=True)
    (project_dir / 'ꘖ' / 'KB').mkdir(parents=True, exist_ok=True)
    (project_dir / 'ꘖ' / 'data' / '.journal').mkdir(parents=True, exist_ok=True)
    (project_dir / 'ꘖ' / 'data' / '.draft-snapshots').mkdir(parents=True, exist_ok=True)
    (project_dir / 'ꙮ' / '0').mkdir(parents=True, exist_ok=True)
    (project_dir / 'ꙮ' / '1 - Анализ' / 'req').mkdir(parents=True, exist_ok=True)
    (project_dir / 'ꙮ' / '1 - Анализ' / 'res').mkdir(parents=True, exist_ok=True)

    # Download attachments into ꘖ/data/attachments if not already downloaded
    if (data.get('attachments') or []) and not data.get('saved_attachments') and extracted_data is None:
        att_dir = project_dir / 'ꘖ' / 'data' / 'attachments'
        try:
            att_data = extract_upwork_job(job_id, cdp_port=cdp_port, fetch_related=False, attachments_dir=att_dir)
            data['saved_attachments'] = att_data.get('saved_attachments') or []
        except Exception:
            pass

    # Write root .md (§16)
    root_md_lines = [
        f'# {data.get("title") or ""}',
        canonical_job_url(job_id),
    ]
    if chosen_name and '.' in chosen_name and ' ' not in chosen_name:
        root_md_lines.extend(['', '#', f'https://{chosen_name}'])
    (project_dir / '.md').write_text('\n'.join(root_md_lines) + '\n', encoding='utf-8')

    # Write KB/Project.md on initial analysis only (§23, §24.7)
    kb_project_path = project_dir / 'KB' / 'Project.md'
    if not kb_project_path.exists() or force_kb:
        kb_md = format_kb_project_md(data, domain=chosen_name, site_note=site_note)
        kb_project_path.write_text(kb_md, encoding='utf-8')

    # Port to ꘖ/KB/ (§24)
    populate_agent_kb(project_dir, data, domain=chosen_name, site_note=site_note, date_str=date_str)

    # Link .agents (§§10-13, 18)
    link_project_agents(
        project_root=project_dir,
        primary_agents_dir=primary_agents_dir,
        job_url=canonical_job_url(job_id),
        domain_or_topic=chosen_name,
    )

    # Register in Antigravity & Folders (§4) when operating on real daily root or explicitly requested
    should_register = (
        register_antigravity
        if register_antigravity is not None
        else (Path(daily_root).resolve() == DAILY_PROPOSALS_ROOT.resolve())
    )
    ag_info = None
    if should_register:
        ag_info = register_antigravity_project(
            project_dir=project_dir,
            domain_or_topic=chosen_name,
            date_str=date_str,
            projects_dir=antigravity_projects_dir,
            folders_json_path=antigravity_folders_json,
        )

    # Generate ꙮ/0/Context.md (§25)
    generate_context(project_dir, project_dir / '.agents' / 'context.json')

    return {
        'project_dir': str(project_dir),
        'job_id': job_id,
        'title': data.get('title'),
        'domain_or_topic': chosen_name,
        'candidate_domains': data.get('candidate_domains'),
        'client_names': data.get('client_names'),
        'saved_attachments': data.get('saved_attachments') or [],
        'context_path': str(project_dir / 'ꙮ' / '0' / 'Context.md'),
        'antigravity': ag_info,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Initialize or sync an Upwork project directory.')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_init = sub.add_parser('init', help='Extract Upwork job via CDP and initialize project folder')
    p_init.add_argument('url', help='Upwork job URL or ~02... ID')
    p_init.add_argument('--domain', help='Verified client domain or fallback topic name')
    p_init.add_argument('--site-note', help='Note explaining how the client website was identified')
    p_init.add_argument('--date', help='Date override YYYY-MM-DD')
    p_init.add_argument('--cdp-port', type=int, default=9222)
    p_init.add_argument('--force-kb', action='store_true', help='Overwrite KB/Project.md if it already exists')

    p_inspect = sub.add_parser('inspect', help='Extract Upwork job JSON via CDP without creating files')
    p_inspect.add_argument('url', help='Upwork job URL or ~02... ID')
    p_inspect.add_argument('--cdp-port', type=int, default=9222)
    p_inspect.add_argument('--attachments-dir', type=Path, help='Optional directory to save job attachments')

    p_link = sub.add_parser('link-agents', help='Link/sync .agents in an existing project directory')
    p_link.add_argument('project_dir', type=Path, help='Path to existing project directory')
    p_link.add_argument('--job-url', help='Optional canonical Upwork job URL for 90-project.md')
    p_link.add_argument('--domain', help='Optional domain or topic for 90-project.md')
    p_link.add_argument('--rebuild-context', action='store_true', help='Also rebuild ꙮ/0/Context.md')

    args = parser.parse_args(argv)
    if args.cmd == 'inspect':
        info = extract_upwork_job(args.url, cdp_port=args.cdp_port, attachments_dir=args.attachments_dir)
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == 'init':
        res = initialize_upwork_project(
            url_or_id=args.url,
            domain_or_topic=args.domain,
            site_note=args.site_note,
            date_str=args.date,
            cdp_port=args.cdp_port,
            force_kb=args.force_kb,
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == 'link-agents':
        proj = args.project_dir.resolve()
        link_project_agents(proj, job_url=args.job_url, domain_or_topic=args.domain)
        if args.rebuild_context:
            generate_context(proj, proj / '.agents' / 'context.json')
        print(json.dumps({'status': 'ok', 'project_dir': str(proj)}, ensure_ascii=False))
        return 0
    return 1


if __name__ == '__main__':
    sys.exit(main())

