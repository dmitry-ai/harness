# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
import zlib
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class PdfLigatureRepairer:
	LIGATURE_MAP = str.maketrans({'\ufb00': 'ff', '\ufb01': 'fi', '\ufb02': 'fl', '\ufb03': 'ffi', '\ufb04': 'ffl', '\ufb05': 'st', '\ufb06': 'st'})
	# @used-by :meth:`PdfLigatureRepairer.discover_repairs()`
	@classmethod
	def __collect_stream_repairs(cls, dec: str, cid_to_uni: dict[int, str], full_map: dict[int, str], out: dict[str, str]) -> None:
		s_full: list[str] = []
		s_broken: list[str] = []
		for tj in re.findall('\\[(.*?)\\]\\s*TJ', dec, re.S):
			for h in re.findall('<([0-9A-Fa-f]+)>', tj):
				for i in range(0, len(h) - 3, 4):
					c = int(h[i:i + 4], 16)
					s_full.append(full_map.get(c, ' '))
					s_broken.append(cid_to_uni.get(c, '\ufffd'))
		full_text, broken_text = (''.join(s_full), ''.join(s_broken))
		for m in re.finditer('[A-Za-z\\ufb00-\\ufb06]+', full_text):
			b = broken_text[m.start():m.end()]
			if '\ufffd' in b:
				clean_w = m.group(0).translate(cls.LIGATURE_MAP)
				out[b.replace('\ufffd', ' ').translate(cls.LIGATURE_MAP)] = clean_w
				out[b.replace('\ufffd', '\u01af').translate(cls.LIGATURE_MAP)] = clean_w
	# @used-by :meth:`PdfLigatureRepairer.parse_streams()`
	@staticmethod
	def __infer_unmapped(cid_to_uni: dict[int, str]) -> dict[int, str]:
		r: dict[int, str] = {}
		for cid, ch in list(cid_to_uni.items()):
			if '\ufb01' == ch and '\ufb02' == cid_to_uni.get(cid + 1):
				for offset, lig_char in ((-2, '\ufb00'), (-1, '\ufb03'), (2, '\ufb04')):
					if cid + offset not in cid_to_uni:
						r[cid + offset] = lig_char
		return r
	# @used-by :func:`agent_tools.upwork_data.discover_pdf_ligature_repairs()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__init__()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_docx_pdf_xlsx_odt_and_loom_extractors()`
	@classmethod
	def discover_repairs(cls, pdf_bytes: bytes) -> dict[str, str]:
		cid_to_uni, content_streams, unmapped = cls.parse_streams(pdf_bytes, text_ops_only=True)
		r: dict[str, str] = {}
		if unmapped:
			full_map = {**cid_to_uni, **unmapped}
			for dec in content_streams:
				cls.__collect_stream_repairs(dec, cid_to_uni, full_map, r)
		return r
	# @used-by :func:`agent_tools.upwork_data.normalize_pdf_ligatures()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__clean_txt()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__extract_from_pdftotext()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__extract_from_raw_streams()`
	@classmethod
	def normalize_ligatures(cls, text: str, repairs: dict[str, str] | None=None) -> str:
		out = (text or '').translate(cls.LIGATURE_MAP)
		if repairs:
			for bad, good in repairs.items():
				out = out.replace(bad, good)
		return re.sub('(?<=[A-Za-z])\\u01af(?=[A-Za-z])', 'ff', out)
	# @used-by :func:`agent_tools.upwork_data._parse_pdf_streams()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__extract_from_raw_streams()`
	# @used-by :meth:`PdfLigatureRepairer.discover_repairs()`
	@classmethod
	def parse_streams(cls, pdf_bytes: bytes, *, text_ops_only: bool=False) -> tuple[dict[int, str], list[str], dict[int, str]]:
		cid_to_uni: dict[int, str] = {}
		content_streams: list[str] = []
		for m in re.finditer(b'stream\\s*(.*?)\\s*endstream', pdf_bytes, re.S):
			raw = m.group(1)
			try:
				dec = zlib.decompress(raw).decode('latin1', errors='ignore')
			except Exception:
				dec = raw.decode('latin1', errors='ignore')
			if 'begincmap' in dec:
				for cid_hex, uni_hex in re.findall('<([0-9A-Fa-f]{4})>\\s*<([0-9A-Fa-f]{4,8})>', dec):
					cid_to_uni[int(cid_hex, 16)] = ''.join((chr(int(uni_hex[i:i + 4], 16)) for i in range(0, len(uni_hex), 4)))
			elif 'BT' in dec and ((not text_ops_only) or 'TJ' in dec or 'Tj' in dec):
				content_streams.append(dec)
		return (cid_to_uni, content_streams, cls.__infer_unmapped(cid_to_uni))
