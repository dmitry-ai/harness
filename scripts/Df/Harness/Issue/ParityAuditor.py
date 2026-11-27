# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.RepoGate import RepoGate
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
import json
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ParityAuditor:
	# @used-by :func:`agent_tools.issues.parity.check_similar_project_parity()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.audit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_parity_and_scope_completeness()`
	def __init__(self, root: Path, repo_touched: dict[Path, set[str]], turn_issues: dict[str, dict], turn_state: dict | None, candidate_repos: list[Path], violations: list[str]) -> None:
		self.__root = root
		self.__repo_touched = repo_touched
		self.__turn_issues = turn_issues
		self.__turn_state = turn_state
		self.__candidate_repos = candidate_repos
		self.__violations = violations
	# @used-by :meth:`ParityAuditor.audit()`
	def __evaluate_peer_item(self, item: dict, exemptions: list[dict], cand_keys: set[str], canonicalize_root_dir) -> tuple[dict, bool]:
		peer_root = canonicalize_root_dir(Path(item['peer_root']))
		for pcr in self.peer_code_repo_candidates(peer_root):
			if pcr.as_posix().lower() not in cand_keys:
				cand_keys.add(pcr.as_posix().lower())
				self.__candidate_repos.append(pcr)
		peer_slugs = self.similar_project_repo_slugs(peer_root)
		resolution, matched_ev = self.__resolve_peer_parity(item, peer_root, peer_slugs, exemptions)
		satisfied = None is not resolution
		if not satisfied:
			target_repo = peer_slugs[0] if peer_slugs else peer_root.as_posix()
			joined_slugs = ', '.join(peer_slugs)
			hint = f' (repos: {joined_slugs})' if peer_slugs else ''
			src_lbl = item['source_label']
			self.__violations.append(f'EXEC-5 / SCOPE-4 parity violation: changes in similar source [{src_lbl}] require parity with peer {peer_root.as_posix()}{hint}; update peer code, file a porting GitHub issue via df_github_issue.py create --repo {target_repo}, or record an audited exemption via harness.py similar-project-exempt "{self.__root.as_posix()}" --peer "{target_repo}" --reason "<technical justification >= 30 chars>"')
		rec = {'group_id': item.get('group_id'), 'source_projects': [Path(sp).as_posix() for sp in item.get('source_projects') or ()], 'peer_root': peer_root.as_posix(), 'peer_repos': peer_slugs, 'satisfied': satisfied, 'resolution': resolution, 'evidence': matched_ev}
		return (rec, satisfied)
	# @used-by :meth:`ParityAuditor.__match_exemption()`
	@staticmethod
	def __exemption_matches(ex: dict, peer_key: str, slug_keys: set[str]) -> bool:
		ex_root_raw = str(ex.get('peer_root') or '').strip()
		root_hit = False
		if ex_root_raw:
			try:
				root_hit = Path(ex_root_raw).resolve().as_posix().lower() == peer_key
			except OSError:
				root_hit = ex_root_raw.replace('\\', '/').rstrip('/').lower() == peer_key
		ex_repos = {str(s).strip().lower() for s in (ex.get('peer_repos') or ()) if str(s).strip()}
		ex_peer = str(ex.get('peer') or '').strip().lower()
		return root_hit or bool(ex_repos & slug_keys) or bool(ex_peer and (ex_peer in slug_keys or ex_peer.replace('\\', '/').rstrip('/') == peer_key))
	# @used-by :meth:`ParityAuditor.__resolve_peer_parity()`
	def __find_peer_issue(self, slug_keys: set[str]) -> tuple[str | None, str | None]:
		res, ev = (None, None)
		for info in sorted(self.__turn_issues.values(), key=lambda x: str(x.get('url') or '')):
			acts = {str(a) for a in (info.get('actions') or ()) if a}
			if info.get('last_action'):
				acts.add(str(info['last_action']))
			repo_s = str(info.get('repo') or '').strip()
			num = int(info['number'])
			if repo_s.lower() in slug_keys and (acts & {'create', 'edit', 'comment'}) and EvidenceWorkspace.evidence_issue_files(self.__root, repo_s, f'issue-{num}.json', self.__candidate_repos):
				res, ev = ('peer_issue_recorded', info.get('url'))
				break
		return (res, ev)
	# @used-by :meth:`ParityAuditor.audit()`
	def __load_exemptions(self) -> list[dict]:
		from agent_tools.path_registry import project_paths
		items = [raw for raw in ((self.__turn_state or {}).get('similar_project_exemptions') or []) if isinstance(raw, dict)]
		turn_key = str((self.__turn_state or {}).get('key') or '').strip()
		if turn_key:
			ex_file = project_paths(self.__root, exact_root=True).turns_dir / f'{turn_key}-similar-exemptions.json'
			if ex_file.is_file():
				try:
					loaded = json.loads(ex_file.read_text(encoding='utf-8'))
					raw_list = loaded.get('exemptions') if isinstance(loaded, dict) else loaded
					if isinstance(raw_list, list):
						items.extend((raw for raw in raw_list if isinstance(raw, dict)))
				except (OSError, ValueError):
					pass
		return items
	# @used-by :meth:`ParityAuditor.__resolve_peer_parity()`
	@classmethod
	def __match_exemption(cls, exemptions: list[dict], peer_root: Path, peer_slugs: list[str]) -> dict | None:
		peer_key, slug_keys = (peer_root.as_posix().lower(), {s.lower() for s in peer_slugs})
		return next((ex for ex in exemptions if 30 <= len(str(ex.get('reason') or '').strip()) and cls.__exemption_matches(ex, peer_key, slug_keys)), None)
	# @used-by :meth:`ParityAuditor.__evaluate_peer_item()`
	def __resolve_peer_parity(self, item: dict, peer_root: Path, peer_slugs: list[str], exemptions: list[dict]) -> tuple[str | None, str | None]:
		if item.get('peer_touched'):
			resolution, matched_ev = ('peer_code_updated', peer_root.as_posix())
		else:
			resolution, matched_ev = self.__find_peer_issue({s.lower() for s in peer_slugs})
			if None is resolution:
				ex = self.__match_exemption(exemptions, peer_root, peer_slugs)
				if None is not ex:
					resolution, matched_ev = ('exempted', str(ex.get('reason') or '').strip())
		return (resolution, matched_ev)
	# @used-by :func:`agent_tools.issues.parity.check_similar_project_parity()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.audit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_parity_and_scope_completeness()`
	def audit(self) -> dict:
		from agent_tools.path_registry import canonicalize_root_dir, evaluate_similar_project_touches
		touched_files = [code_repo / rel for code_repo, rels in sorted(self.__repo_touched.items(), key=lambda x: str(x[0])) for rel in sorted(rels)]
		touches = evaluate_similar_project_touches(touched_files) if touched_files else []
		if not touches:
			r = {'verified': True, 'peers': []}
		else:
			exemptions = self.__load_exemptions()
			cand_keys = {c.resolve().as_posix().lower() for c in self.__candidate_repos}
			peer_records, all_ok = ([], True)
			for item in touches:
				rec, ok = self.__evaluate_peer_item(item, exemptions, cand_keys, canonicalize_root_dir)
				peer_records.append(rec)
				all_ok = all_ok and ok
			r = {'verified': all_ok, 'peers': peer_records}
		return r
	# @used-by :meth:`ParityAuditor.__evaluate_peer_item()`
	# @used-by :meth:`ParityAuditor.similar_project_repo_slugs()`
	@staticmethod
	def peer_code_repo_candidates(peer_root: Path, *, registry=None) -> list[Path]:
		from agent_tools.path_registry import project_paths
		pp_peer = project_paths(peer_root, registry=registry)
		out, seen = ([], set())
		for cand in (*pp_peer.code_repos, pp_peer.root, pp_peer.root / 'code', pp_peer.root / '\u2c0f/\u227b/\u2655/\u26ef', pp_peer.root / 'Artifacts/\u227b/Deliverables/\u26ef'):
			try:
				resolved = cand.resolve()
			except OSError:
				continue
			key = resolved.as_posix().lower()
			if key not in seen and RepoGate(resolved).is_issue_tracked():
				seen.add(key)
				out.append(resolved)
		return out
	# @used-by :func:`agent_tools.issues.parity.similar_project_repo_slugs()`
	# @used-by :meth:`Df.Harness.Issue.PendingPeerFinder.PendingPeerFinder.find()`
	# @used-by :meth:`ParityAuditor.__evaluate_peer_item()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_parity_and_scope_completeness()`
	@classmethod
	def similar_project_repo_slugs(cls, peer_root: Path, *, registry=None) -> list[str]:
		slugs, seen = ([], set())
		for cand in cls.peer_code_repo_candidates(peer_root, registry=registry):
			slug = EvidenceWorkspace.origin_repo_slug(cand)
			if slug and slug.lower() not in seen:
				seen.add(slug.lower())
				slugs.append(slug)
		return slugs
