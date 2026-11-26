# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class LocalSourceResolver:
	# @used-by :func:`agent_tools.evidence.local_file()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ManifestPrimaryVerifier.ManifestPrimaryVerifier.__check_snapshot()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ManifestPrimaryVerifier.ManifestPrimaryVerifier.verify()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.PrimaryCapabilities.PrimaryCapabilities.__resolve_experiment()`
	# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.__check_counter_source()`
	# @used-by :meth:`Df.Harness.Analysis.ObservationContentLoader.ObservationContentLoader.load()`
	# @used-by :meth:`Df.Harness.Analysis.ObservationProber.ObservationProber.__probe_html()`
	# @used-by :meth:`Df.Harness.Analysis.SavedSourceLoader.SavedSourceLoader.__load_local()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def __init__(self, root, reference: str) -> None:
		self.__root = root
		self.__reference = reference
	# @used-by :func:`agent_tools.evidence.local_file()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ManifestPrimaryVerifier.ManifestPrimaryVerifier.__check_snapshot()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ManifestPrimaryVerifier.ManifestPrimaryVerifier.verify()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.PrimaryCapabilities.PrimaryCapabilities.__resolve_experiment()`
	# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.__check_counter_source()`
	# @used-by :meth:`Df.Harness.Analysis.ObservationContentLoader.ObservationContentLoader.load()`
	# @used-by :meth:`Df.Harness.Analysis.ObservationProber.ObservationProber.__probe_html()`
	# @used-by :meth:`Df.Harness.Analysis.SavedSourceLoader.SavedSourceLoader.__load_local()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def resolve(self) -> Path:
		from agent_tools.links import decode_file_uri
		from agent_tools.path_registry import project_paths
		path = decode_file_uri(self.__reference, reject_remote=True)
		pp = project_paths(self.__root, exact_root=True)
		root_resolved = pp.root
		target = (pp.kb_dir / path).resolve()
		if not target.exists() and path.replace('\\', '/').lstrip('/').startswith('source/'):
			alt = (root_resolved / path.replace('\\', '/').lstrip('/')).resolve()
			if alt.is_relative_to(pp.source_dir):
				target = alt
		if not (target.is_relative_to(root_resolved) or target.is_relative_to(pp.kb_dir.resolve())):
			raise ValueError('Source path escapes the project; copy authorized primary evidence into Evidence first')
		return target