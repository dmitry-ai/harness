# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import override
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class SafeRedirects(HTTPRedirectHandler):
	# @used-by :meth:`Df.Harness.Research.Collector.Collector.fetch()`
	def __init__(self) -> None:
		self.chain: list[dict] = []
	# @used-by :meth:`SafeRedirects.redirect_request()`
	@staticmethod
	def __origin(url: str) -> tuple[str, str | None, int]:
		value = urlsplit(url)
		return (value.scheme, value.hostname, value.port or (443 if 'https' == value.scheme else 80))
	# @used-by :meth:`urllib.request.HTTPRedirectHandler.redirect_request()`
	# @see :meth:`urllib.request.HTTPRedirectHandler.redirect_request()`
	@override
	def redirect_request(self, req, fp, code, msg, headers, newurl):
		redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
		if redirected:
			self.chain.append({'from': req.full_url, 'to': redirected.full_url, 'status': code})
			if self.__origin(req.full_url) != self.__origin(redirected.full_url):
				for key in list(redirected.headers):
					if key.lower() in ('authorization', 'cookie', 'proxy-authorization'):
						redirected.remove_header(key)
		return redirected
