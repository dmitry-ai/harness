# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.storage import create_bytes, replace_bytes
from Df.Harness.Project.AttachmentInventory import AttachmentInventory
from Df.Harness.Project.OnceFileWriter import OnceFileWriter
from Df.Harness.Upwork.AttachmentExtractor import AttachmentExtractor
from Df.Harness.Upwork.LoomVideoExtractor import LoomVideoExtractor
from Df.Harness.Upwork.VideoDetector import VideoDetector
import json
from pathlib import Path
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ExtraSourceBuilder:
	# @used-by :func:`agent_tools.knowledge.build_project_extra_sources()`
	# @used-by :meth:`Df.Harness.Project.AttachmentKbSyncer.AttachmentKbSyncer.sync()`
	# @used-by :meth:`Df.Harness.Project.KbPopulator.KbPopulator.populate()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	def __init__(self, project_root: Path, data: dict, assets: list[dict] | None=None, *, fetch_videos: bool=True, loom_fn=None) -> None:
		self.__project_root = project_root
		self.__data = data
		self.__assets = assets
		self.__fetch_videos = fetch_videos
		self.__loom_fn = (lambda u: LoomVideoExtractor(u).extract()) if None is loom_fn else loom_fn
	# @used-by :meth:`ExtraSourceBuilder.build()`
	def __process_asset(self, pp, asset: dict, descriptions: dict[str, str], doc_markdowns: list[str], extra_sources: list[dict]) -> None:
		target = pp.kb_dir / asset['file']
		if target.is_file():
			fname, sha, payload = (asset.get('filename') or target.name, asset['sha256'], target.read_bytes())
			src_copy = pp.source_dir / fname
			if not src_copy.exists():
				src_copy.parent.mkdir(parents=True, exist_ok=True)
				create_bytes(src_copy, payload)
			src_rel = asset.get('source_file') or pp.rel_to_root(src_copy)
			kind, custom_body = (AttachmentExtractor.classify(fname, payload), descriptions.get(fname) or descriptions.get(sha))
			if 'document' == kind:
				body = custom_body or AttachmentExtractor.extract_markdown(target, payload)
				doc_markdowns.append(body)
				extra_sources.append({'kind': 'document', 'name': fname, 'heading': f'Description in `{fname}`', 'body': body, 'sha256': sha, 'file': asset['file'], 'source_file': src_rel})
			elif 'image' == kind:
				extra_sources.append({'kind': 'image', 'name': fname, 'heading': f'Description in `{fname}`', 'body': custom_body or '', 'sha256': sha, 'file': asset['file'], 'source_file': src_rel})
	# @used-by :meth:`ExtraSourceBuilder.build()`
	def __process_video(self, v: dict, assets: list[dict], descriptions: dict[str, str], media_dir: Path) -> dict:
		v_key = v.get('url') or v.get('filename') or v.get('video_id') or ''
		v_www = re.sub('^https?://(?!www\\.)', 'https://www.', v_key) if v_key.startswith('http') else ''
		v_nowww = re.sub('^https?://www\\.', 'https://', v_key) if v_key.startswith('http') else ''
		keys = (v_key, v_www, v_nowww, v.get('video_id') or '', v.get('filename') or '')
		body = next((descriptions[k] for k in keys if k and k in descriptions), '')
		if not body and 'loom' == v.get('kind') and v.get('url'):
			body = self.__resolve_loom_body(v, media_dir)
		return {'kind': 'video', 'name': v.get('filename') or v.get('url') or v['label'], 'url': v.get('url'), 'video_id': v.get('video_id'), 'sha256': v.get('sha256'), 'file': next((a['file'] for a in assets if a.get('sha256') == v.get('sha256')), None) if v.get('sha256') else None, 'source_file': f"source/{v['filename']}" if v.get('filename') else None, 'heading': v['heading'], 'body': body}
	# @used-by :meth:`ExtraSourceBuilder.__process_video()`
	def __resolve_loom_body(self, v: dict, media_dir: Path) -> str:
		cache_file = media_dir / f"loom-{v['video_id']}.json"
		r = ''
		if cache_file.is_file():
			try:
				r = json.loads(cache_file.read_text(encoding='utf-8')).get('markdown') or ''
			except Exception:
				r = ''
		if not r and self.__fetch_videos:
			try:
				loom_info = self.__loom_fn(v['url'])
				media_dir.mkdir(parents=True, exist_ok=True)
				replace_bytes(cache_file, OnceFileWriter.json_bytes(loom_info))
				r = loom_info.get('markdown') or ''
			except Exception:
				r = ''
		return r
	# @used-by :func:`agent_tools.knowledge.build_project_extra_sources()`
	# @used-by :meth:`Df.Harness.Project.AttachmentKbSyncer.AttachmentKbSyncer.sync()`
	# @used-by :meth:`Df.Harness.Project.KbPopulator.KbPopulator.populate()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	def build(self) -> list[dict]:
		from agent_tools.path_registry import project_paths
		pp = project_paths(self.__project_root, exact_root=True)
		assets = AttachmentInventory(pp.root).sync(self.__data.get('saved_attachments'), self.__data.get('asset_evidence')) if None is self.__assets else self.__assets
		descriptions = self.load_media_descriptions(pp.root, self.__data.get('media_descriptions'))
		r: list[dict] = []
		doc_markdowns: list[str] = []
		for asset in assets:
			self.__process_asset(pp, asset, descriptions, doc_markdowns, r)
		media_dir = pp.data_dir / 'media'
		for v in VideoDetector.detect(self.__data.get('description') or '', doc_markdowns, assets):
			r.append(self.__process_video(v, assets, descriptions, media_dir))
		return r
	# @used-by :func:`agent_tools.knowledge._load_media_descriptions()`
	# @used-by :meth:`ExtraSourceBuilder.build()`
	@staticmethod
	def load_media_descriptions(project_root: Path, overrides: dict | None=None) -> dict[str, str]:
		from agent_tools.path_registry import project_paths
		media_dir = project_paths(project_root, exact_root=True).data_dir / 'media'
		store_file = media_dir / 'descriptions.json'
		r: dict[str, str] = {}
		if store_file.is_file():
			try:
				loaded = json.loads(store_file.read_text(encoding='utf-8'))
				if isinstance(loaded, dict):
					r.update({str(k): str(v) for k, v in loaded.items() if isinstance(v, str) and v.strip()})
			except Exception:
				pass
		if overrides and isinstance(overrides, dict):
			for k, v in overrides.items():
				if isinstance(v, str) and v.strip():
					r[str(k)] = v.strip()
			media_dir.mkdir(parents=True, exist_ok=True)
			replace_bytes(store_file, OnceFileWriter.json_bytes(r))
		return r
