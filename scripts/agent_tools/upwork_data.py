"""Upwork identifiers, observed name/domain mentions and source formatting."""

import re


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
    """Collect literal domain mentions, without guessing client ownership or excluding vendors."""
    pattern = r'(?<![\w.-])((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,63})(?![\w.-])'
    domains = (m[4:] if m.startswith('www.') else m
               for text in texts for m in re.findall(pattern, text.lower()))
    return list(dict.fromkeys(domains))


def markdown_fence(text: str, marker: str = '~') -> str:
    return marker * max(3, 1 + max((len(m[0]) for m in re.finditer(re.escape(marker) + r'+', text)), default=0))


_SENTENCE_SPLIT_RE = re.compile(
    r'(?<!\be\.g)(?<!\bi\.e)(?<!\bvs)(?<!\betc)(?<!\bMr)(?<!\bDr)(?<!\bSt)(?<!\bNB)(?<=[.!?])\s+(?=[A-ZА-ЯЁ"«(])'
)


def split_sentences_one_per_line(text: str) -> list[str]:
    """Split a paragraph into individual sentences (one per line per DOC-4)."""
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


def format_kb_project_md(data: dict) -> str:
    """Format KB/Project.md strictly following the user's reference schema (§§23-24)."""
    buyer = data.get('buyer') or {}
    loc = buyer.get('location') or {}

    # 1.1 Имя
    client_names = data.get('client_names') or []
    if client_names:
        name_str = 'не установлено; имена из отзывов требуют проверки'
    else:
        name_str = 'неизвестно'

    # 1.2 Местоположение
    country = (loc.get('country') or 'неизвестно').strip()
    city = (loc.get('city') or '').strip()
    loc_lines = [country]
    if city:
        loc_lines.append(city)

    # 1.3 Сайт
    site_str = 'не установлен; упоминание домена и имя папки не доказывают принадлежность'
    if data.get('site_hypothesis'):
        h = data['site_hypothesis']
        from .knowledge import validate_analysis, SECTIONS
        analysis = {key: ([h] if key == 'identity' else []) for key in SECTIONS}
        analysis['notes'] = {key: 'Отдельный этап анализа.' for key in SECTIONS if key != 'identity'}
        validate_analysis(analysis)
        site_str = '\n'.join([h['essence'],
            'За: ' + '; '.join(f'{a["argument"]} «{a["quote"]}» ({a["source"]})' for a in h['for']),
            'Против: ' + '; '.join(f'{a["argument"]} «{a["quote"]}» ({a["source"]})' for a in h['against']),
            f'Экспертная правдоподобность: {h["probability_percent"]}%.', h['assessment_basis']])

    # 2. Текущий проект клиента
    job_url = canonical_job_url(data.get('job_id') or data.get('url') or '')
    job_title = (data.get('title') or '').strip()
    structured_desc = structure_job_description(data.get('description') or '', data.get('questions'))

    fence = markdown_fence(structured_desc)
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
        fence + 'markdown',
        job_title,
        '#',
        structured_desc,
        fence,
        '',
        '# 3. Прошлые проекты клиента',
        '## 3.0',
        'Проекты опубликованы тем же аккаунтом; их связь с текущим сайтом не установлена.',
        '##',
        'Используй эти проекты для понимания контекста.',
        'Работа над этими проектами — вне рамок текущей задачи.',
    ]

    for idx, pjob in enumerate(collect_unique_public_past_jobs(data), start=1):
        p_structured = structure_job_description(pjob['description'])
        fence = markdown_fence(p_structured)
        lines.extend([
            '',
            f'## 3.{idx}',
            pjob['url'],
            fence + 'markdown',
            pjob['title'],
            '#',
            p_structured,
            fence,
        ])

    return '\n'.join(lines) + '\n'


