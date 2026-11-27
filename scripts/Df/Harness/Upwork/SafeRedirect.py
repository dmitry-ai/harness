# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import override
from urllib.parse import urlsplit
import urllib.request
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class SafeRedirect(urllib.request.HTTPRedirectHandler):
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
	# @used-by :meth:`test_onboarding.AttachmentTests.test_redirect_cannot_keep_credentials_on_another_host()`
	# @used-by :meth:`urllib.request.HTTPRedirectHandler.redirect_request()`
	# @see :meth:`urllib.request.HTTPRedirectHandler.redirect_request()`
	@override
	def redirect_request(self, req, fp, code, msg, headers, newurl):
		if 'https' != urlsplit(newurl).scheme:
			raise ValueError('Attachment redirect must use HTTPS')
		result = super().redirect_request(req, fp, code, msg, headers, newurl)
		if result and urlsplit(req.full_url).hostname != urlsplit(newurl).hostname:
			for key in ('Cookie', 'Authorization'):
				result.remove_header(key)
		return result
