# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Git.ShellSegmenter import ShellSegmenter
from Df.Harness.lib.shell import dfh_protected_browser_perimeter
import re
_CDP_PROTOCOL_RE = re.compile(r'(?:(?:https?|wss?)://(?:127\.0\.0\.1|localhost|\[::1\])(?::\d+)?(?:/json(?:/|$|["\'\s?])|/devtools/(?:page|browser)(?:/|$|["\'\s?]))|(?:/json/(?:list|version|new|activate|close|protocol)\b|/devtools/(?:page|browser)/[A-Za-z0-9_-]*)|\bDevToolsActivePort\b|\bchrome-remote-interface\b|\bchrome-devtools-mcp\b[^\r\n]*(?:--browser-url|--browserUrl|--autoConnect)\b)', re.I)
_INLINE_EXEC_RE = re.compile(r'\b(?:python(?:3)?(?:\.exe)?\s+(?:-[A-Za-z]+\s+)*-c|node(?:\.exe)?\s+(?:--[A-Za-z-]+(?:=\S+)?\s+)*-e)\b', re.I)
_NET_CLIENT_RE = re.compile(r'(?:\b(?:urlopen|urllib|requests|httpx|websockets|WebSocket|curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod|TcpClient|netstat|Get-NetTCPConnection)\b)', re.I)
_PROFILE_ASSET_RE = re.compile(r'(?:devtoolsactiveport|local\s+state|/cookies\b|/login\s+data\b|/web\s+data\b)')
_SANCTIONED_CDP_RUNNER_RE = re.compile(r'(?:harness\.py|upwork_project\.py|df_text\.py|df_article\.py|df_proposal\.py|df_github_issue\.py|validate_links\.py|safe_commit\.py|\bunittest\b|\bpytest\b)', re.I)
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class CdpBypassAudit:
	# @used-by :meth:`Df.Harness.Git.ShellInspector.ShellInspector.prohibited_cdp_bypass_commands()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def __init__(self, text: str, *, config=None) -> None:
		self.__text = text
		self.__config = config
	# @used-by :meth:`CdpBypassAudit.__is_sanctioned()`
	def __is_sanctioned_addon(self, seg_norm: str) -> bool:
		try:
			from agent_tools.runtime import sanctioned_addon_code_roots
			roots = sanctioned_addon_code_roots(self.__config)
		except Exception:
			roots = []
		r = False
		for root in roots:
			r_norm = root.as_posix().rstrip('/').casefold()
			if r_norm and (f'{r_norm}/' in seg_norm or seg_norm.endswith(r_norm)):
				r = True
				break
		return r
	# @used-by :meth:`CdpBypassAudit.detect()`
	def __is_sanctioned(self, seg: str, seg_norm: str) -> bool:
		return (not _INLINE_EXEC_RE.search(seg)) and (bool(_SANCTIONED_CDP_RUNNER_RE.search(seg)) or self.__is_sanctioned_addon(seg_norm))
	# @used-by :meth:`CdpBypassAudit.detect()`
	@staticmethod
	def __matches_bypass(seg: str, seg_norm: str, perim: dict, port_re: re.Pattern | None) -> bool:
		if _CDP_PROTOCOL_RE.search(seg):
			r = True
		elif None is not port_re and port_re.search(seg) and _NET_CLIENT_RE.search(seg):
			r = True
		elif any((apf and apf in seg_norm for apf in perim['active_port_files'])):
			r = True
		else:
			r = any((pdir and pdir in seg_norm and _PROFILE_ASSET_RE.search(seg_norm) for pdir in perim['profile_dirs']))
		return r
	# @used-by :meth:`Df.Harness.Git.ShellInspector.ShellInspector.prohibited_cdp_bypass_commands()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def detect(self) -> list[str]:
		r: list[str] = []
		if isinstance(self.__text, str) and self.__text.strip():
			perim = dfh_protected_browser_perimeter(self.__config)
			port_alt = '|'.join((str(p) for p in perim['ports']))
			port_re = re.compile(f'(?:(?:https?|wss?)://)?(?:127\\.0\\.0\\.1|localhost|\\[::1\\]):(?:{port_alt})\\b', re.I) if port_alt else None
			for seg in ShellSegmenter(self.__text).split():
				seg_norm = seg.replace('\\\\', '/').replace('\\', '/').casefold()
				if (not self.__is_sanctioned(seg, seg_norm)) and self.__matches_bypass(seg, seg_norm, perim, port_re):
					snippet = ' '.join(seg.strip().split())[:240]
					if snippet not in r:
						r.append(snippet)
		return r
