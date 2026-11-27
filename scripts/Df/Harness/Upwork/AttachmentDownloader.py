# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.storage import create_bytes
from Df.Harness.Upwork.SafeRedirect import SafeRedirect
import hashlib
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit
import urllib.request
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class AttachmentDownloader:
	MAX_ATTACHMENT = 25 * 1024 * 1024
	# @used-by :func:`agent_tools.upwork_extract.download_attachment()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__download_assets()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
	def __init__(self, attachment: dict, directory: Path, cookies=(), user_agent: str='UpworkOnboarding/2') -> None:
		self.__attachment = attachment
		self.__directory = Path(directory)
		self.__cookies = cookies
		self.__user_agent = user_agent
	# @used-by :meth:`AttachmentDownloader.download()`
	def __build_headers(self, parsed) -> dict[str, str]:
		allowed: list[str] = []
		for cookie in self.__cookies:
			domain = cookie.get('domain', 'www.upwork.com')
			host_ok = parsed.hostname.endswith(domain) or parsed.hostname == domain[1:] if domain.startswith('.') else parsed.hostname == domain
			cpath = cookie.get('path') or '/'
			path_ok = parsed.path == cpath or parsed.path.startswith(cpath if cpath.endswith('/') else cpath + '/')
			if host_ok and path_ok:
				allowed.append(f"{cookie['name']}={cookie['value']}")
		r = {'User-Agent': self.__user_agent}
		if allowed:
			r['Cookie'] = '; '.join(allowed)
		return r
	# @used-by :func:`agent_tools.upwork_extract.attachment_path()`
	# @used-by :meth:`AttachmentDownloader.download()`
	# @used-by :meth:`Df.Harness.Project.AttachmentInventory.AttachmentInventory.__register_bytes()`
	# @used-by :meth:`Df.Harness.Project.AttachmentInventory.AttachmentInventory.__resolve_source_target()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
	@staticmethod
	def attachment_path(directory: Path, filename: str) -> Path:
		bad = not filename or filename in ('.', '..') or re.search('[\\\\/:\\x00-\\x1f<>"|?*]', filename) or filename.endswith((' ', '.')) or re.match('(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\\.|$)', filename)
		if bad:
			raise ValueError(f'Unsafe attachment filename: {filename!r}')
		target = (directory / filename).resolve()
		if target.parent != directory.resolve():
			raise ValueError('Attachment path escapes its directory')
		return target
	# @used-by :func:`agent_tools.upwork_extract.download_attachment()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__download_assets()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
	def download(self) -> dict:
		target = self.attachment_path(self.__directory, self.__attachment['fileName'])
		url = urljoin('https://www.upwork.com', self.__attachment['uri'])
		if not self.upwork_host(url):
			raise ValueError('Initial attachment URL must be an HTTPS Upwork host')
		request = urllib.request.Request(url, headers=self.__build_headers(urlsplit(url)))
		with urllib.request.build_opener(SafeRedirect()).open(request, timeout=25) as response:
			payload = response.read(self.MAX_ATTACHMENT + 1)
		if len(payload) > self.MAX_ATTACHMENT:
			raise ValueError('Attachment exceeds 25 MiB')
		self.__directory.mkdir(parents=True, exist_ok=True)
		if not target.exists():
			create_bytes(target, payload)
		elif target.read_bytes() != payload:
			raise FileExistsError(f'Different attachment already exists: {target}')
		return {'path': str(target), 'filename': target.name, 'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)}
	# @used-by :func:`agent_tools.upwork_extract.upwork_host()`
	# @used-by :meth:`AttachmentDownloader.download()`
	# @used-by :meth:`Df.Harness.Upwork.TabSelector.TabSelector.select()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
	@staticmethod
	def upwork_host(url: str) -> bool:
		parsed = urlsplit(url)
		return 'https' == parsed.scheme and (not parsed.username) and (not parsed.password) and (parsed.port in (None, 443)) and ('upwork.com' == parsed.hostname or (parsed.hostname or '').endswith('.upwork.com'))
