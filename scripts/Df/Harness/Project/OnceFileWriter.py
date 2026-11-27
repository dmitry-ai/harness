# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.storage import create_bytes
import json
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class OnceFileWriter:
	# @used-by :func:`agent_tools.knowledge.create_once()`
	# @used-by :meth:`Df.Harness.Project.KbPopulator.KbPopulator.__write_kb_pages()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__sync_context_config()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__sync_manifests()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.configure()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	def __init__(self, path: Path, content: str) -> None:
		self.__path = Path(path)
		self.__content = content
	# @used-by :func:`agent_tools.knowledge.json_bytes()`
	# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.__resolve_loom_body()`
	# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.load_media_descriptions()`
	# @used-by :meth:`Df.Harness.Project.KbPopulator.KbPopulator.populate()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.__render_selected()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_inspect()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__sync_context_config()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__sync_manifests()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectDirResolver.ProjectDirResolver.__resolve_or_make_new()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__load_and_prepare_fs()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	@staticmethod
	def json_bytes(value) -> bytes:
		return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
	# @used-by :func:`agent_tools.knowledge.create_once()`
	# @used-by :meth:`Df.Harness.Project.KbPopulator.KbPopulator.__write_kb_pages()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__sync_context_config()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__sync_manifests()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.configure()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	def write(self) -> None:
		self.__path.parent.mkdir(parents=True, exist_ok=True)
		if not self.__path.exists():
			if self.__path.suffix.lower() in ('.md', '.markdown', '.txt', '.html', '.htm'):
				from agent_tools.links import readable_link_issues
				issues = readable_link_issues(self.__content)
				if issues:
					raise ValueError('\n'.join(issues))
			create_bytes(self.__path, self.__content.encode('utf-8'))
