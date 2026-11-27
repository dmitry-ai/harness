# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit
import os
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_local_uri_to_path()`
def _strip_win_extended_prefix(text: str) -> str:
	if text.startswith('\\\\?\\UNC\\'):
		r = '\\\\' + text[8:]
	elif text.startswith('\\\\?\\'):
		r = text[4:]
	else:
		r = text
	return r
# @used-by :func:`Df.Harness.lib.path_discovery._project_file_matches_root()`
def dfh_extract_resource_uri(res: Any) -> str | None:
	r: str | None = None
	if isinstance(res, dict):
		cand = res.get('folderUri') or (res.get('gitFolder') or {}).get('folderUri') or (res.get('folder') or {}).get('folderUri')
		if isinstance(cand, str) and cand.strip():
			r = cand
	return r
# @used-by :func:`Df.Harness.lib.path_discovery._project_file_matches_root()`
def dfh_local_uri_to_path(value: Any, *, require_absolute: bool=False) -> Path:
	raw = os.fspath(value) if isinstance(value, os.PathLike) else value
	if not isinstance(raw, str) or not raw:
		raise ValueError('Missing workspace path')
	if raw.startswith('file:'):
		uri = urlsplit(raw)
		raw, host = (unquote(uri.path), unquote(uri.netloc))
		if re.fullmatch('[A-Za-z]:', host):
			raw = host + raw
		elif host and 'localhost' != host.casefold():
			raw = '//' + host + raw
		if re.match('^/[A-Za-z]:/', raw):
			raw = raw[1:]
	raw = _strip_win_extended_prefix(raw)
	if require_absolute and (not Path(raw).is_absolute()):
		raise ValueError('Workspace path must be absolute')
	return Path(_strip_win_extended_prefix(str(Path(raw).resolve())))
