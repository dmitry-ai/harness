"""Read a specifically selected Upwork tab; bounded RPC and credential-safe assets."""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit
import urllib.request

from .storage import create_bytes
from .upwork_data import (canonical_job_url, normalize_job_id, resolve_nuxt_devalue,
                          extract_candidate_domains, extract_client_names)

MAX_ATTACHMENT = 25 * 1024 * 1024


def upwork_host(url):
    parsed = urlsplit(url)
    return (parsed.scheme == 'https' and not parsed.username and not parsed.password
            and parsed.port in (None, 443)
            and (parsed.hostname == 'upwork.com' or (parsed.hostname or '').endswith('.upwork.com')))


def attachment_path(directory: Path, filename: str) -> Path:
    if (not filename or filename in ('.', '..') or re.search(r'[\\/:\x00-\x1f<>"|?*]', filename)
            or filename.endswith((' ', '.')) or re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', filename)):
        raise ValueError(f'Unsafe attachment filename: {filename!r}')
    target = (directory / filename).resolve()
    if target.parent != directory.resolve():
        raise ValueError('Attachment path escapes its directory')
    return target


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != 'https':
            raise ValueError('Attachment redirect must use HTTPS')
        result = super().redirect_request(req, fp, code, msg, headers, newurl)
        if result and urlsplit(req.full_url).hostname != urlsplit(newurl).hostname:
            for key in ('Cookie', 'Authorization'):
                result.remove_header(key)
        return result


def download_attachment(attachment, directory: Path, cookies=(), user_agent='UpworkOnboarding/2'):
    target = attachment_path(directory, attachment['fileName'])
    url = urljoin('https://www.upwork.com', attachment['uri'])
    if not upwork_host(url):
        raise ValueError('Initial attachment URL must be an HTTPS Upwork host')
    parsed = urlsplit(url)
    allowed = []
    for cookie in cookies:
        domain = cookie.get('domain', 'www.upwork.com')
        host_matches = (parsed.hostname.endswith(domain) or parsed.hostname == domain[1:]) if domain.startswith('.') else parsed.hostname == domain
        if host_matches and parsed.path.startswith(cookie.get('path', '/')):
            allowed.append(f'{cookie["name"]}={cookie["value"]}')
    headers = {'User-Agent': user_agent}
    if allowed:
        headers['Cookie'] = '; '.join(allowed)
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.build_opener(SafeRedirect()).open(request, timeout=25) as response:
        payload = response.read(MAX_ATTACHMENT + 1)
    if len(payload) > MAX_ATTACHMENT:
        raise ValueError('Attachment exceeds 25 MiB')
    directory.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != payload:
            raise FileExistsError(f'Different attachment already exists: {target}')
    else:
        create_bytes(target, payload)
    return {'path': str(target), 'filename': target.name,
            'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)}


class RPC:
    def __init__(self, websocket, timeout=30):
        self.websocket, self.timeout, self.next_id = websocket, timeout, 0

    async def call(self, method, **params):
        self.next_id += 1
        ident = self.next_id
        await self.websocket.send(json.dumps({'id': ident, 'method': method, 'params': params}))
        async def receive():
            while True:
                message = json.loads(await self.websocket.recv())
                if message.get('id') == ident:
                    if 'error' in message:
                        raise RuntimeError(f'CDP {method}: {message["error"]}')
                    return message['result']
        return await asyncio.wait_for(receive(), timeout=self.timeout)

    async def evaluate(self, expression):
        result = await self.call('Runtime.evaluate', expression=expression,
                                 awaitPromise=True, returnByValue=True)
        if result.get('exceptionDetails'):
            raise RuntimeError(f'Browser evaluation failed: {result["exceptionDetails"]}')
        return result.get('result', {}).get('value')


def select_tab(tabs, job_id, tab_id=None):
    candidates = [t for t in tabs if t.get('type') == 'page' and upwork_host(t.get('url', ''))]
    if tab_id:
        candidates = [t for t in candidates if t.get('id') == tab_id]
    else:
        candidates = [t for t in candidates if re.search(r'/jobs/(?:[^/]+/)?' + re.escape(job_id) + r'(?:[/?#]|$)', t['url'])]
    if len(candidates) != 1:
        raise ValueError('Select one exact Upwork job tab with --tab-id; no arbitrary account fallback')
    return candidates[0]


async def _extract(job_id, cdp_port, fetch_related, attachments_dir, tab_id):
    import websockets
    with urllib.request.urlopen(f'http://127.0.0.1:{cdp_port}/json', timeout=5) as response:
        tabs = json.loads(response.read())
    tab = select_tab(tabs, job_id, tab_id)
    async with websockets.connect(tab['webSocketDebuggerUrl'], max_size=50_000_000, open_timeout=10) as websocket:
        rpc = RPC(websocket)
        raw = await rpc.evaluate('document.getElementById("__NUXT_DATA__")?.textContent || ""')
        if not raw:
            raise ValueError('The selected tab has no Upwork source data')
        details = (resolve_nuxt_devalue(json.loads(raw)).get('vuex') or {}).get('jobDetails') or {}
        job = details.get('job') or {}
        if job.get('ciphertext') != job_id:
            raise ValueError('Selected page data does not match the requested job ID')
        history, open_jobs = details.get('workHistory') or [], details.get('openJobs') or []
        related, failures = {}, []
        if fetch_related:
            ids = {(x.get('jobInfo') or {}).get('ciphertext') for x in history}
            ids |= {x.get('ciphertext') for x in open_jobs}
            for ident in sorted(ids - {None, job_id}):
                ident = normalize_job_id(ident)
                url = canonical_job_url(ident).replace('https://upwork.com', 'https://www.upwork.com')
                expression = f'''(async()=>{{const r=await fetch({json.dumps(url)},{{credentials:"include",signal:AbortSignal.timeout(20000)}});
                  if(!r.ok) throw new Error("HTTP "+r.status);
                  const d=new DOMParser().parseFromString(await r.text(),"text/html");
                  return d.getElementById("__NUXT_DATA__")?.textContent||"";}})()'''
                try:
                    text = await rpc.evaluate(expression)
                    found = resolve_nuxt_devalue(json.loads(text))['vuex']['jobDetails']['job']
                    if found.get('ciphertext') != ident:
                        raise ValueError('Related job identity mismatch')
                    related[ident] = {k: found.get(k) for k in ('title', 'description')}
                except (ValueError, KeyError, RuntimeError, TimeoutError) as exc:
                    failures.append({'job_id': ident, 'error': str(exc)})
        assets = []
        if attachments_dir is not None and job.get('attachments'):
            cookies = (await rpc.call('Network.getCookies', urls=['https://www.upwork.com']))['cookies']
            ua = await rpc.evaluate('navigator.userAgent')
            for attachment in job['attachments']:
                assets.append(download_attachment(attachment, Path(attachments_dir), cookies, ua))
        sands = details.get('sands') or {}
        skills = [child['name'] for group in sands.get('ontologySkills') or []
                  for child in group.get('children') or [] if child.get('name')]
        skills += [x['name'] for x in sands.get('additionalSkills') or [] if x.get('name')]
        texts = [job.get('description') or ''] + [x.get('description') or '' for x in related.values()]
        return {
            'schema_version': 2, 'observed_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'source_tab': {'id': tab.get('id'), 'url': tab['url']},
            'job_id': job_id, 'url': canonical_job_url(job_id), 'title': job.get('title') or '',
            'description': job.get('description') or '', 'buyer': details.get('buyer') or {},
            'work_history': history, 'open_jobs': open_jobs, 'related_descriptions': related,
            'attachments': job.get('attachments') or [], 'saved_attachments': assets,
            'questions': [q['question'] for q in job.get('questions') or [] if q.get('question')],
            'skills': list(dict.fromkeys(skills)), 'client_names': extract_client_names(history),
            'candidate_domains': extract_candidate_domains(texts),
            'coverage': {'history_records': len(history), 'history_complete': False,
                         'scope': 'records embedded in the selected page; no pagination asserted',
                         'related_failures': failures},
            **{key: job.get(src) for key, src in (('posted_on', 'postedOn'), ('workload', 'workload'),
               ('duration_label', 'durationLabel'), ('contractor_tier', 'contractorTier'), ('budget', 'budget'),
               ('extended_budget', 'extendedBudgetInfo'), ('client_activity', 'clientActivity'))},
        }


def extract_upwork_job(url_or_id, cdp_port=9222, fetch_related=True, attachments_dir=None, tab_id=None):
    return asyncio.run(_extract(normalize_job_id(url_or_id), cdp_port, fetch_related, attachments_dir, tab_id))
