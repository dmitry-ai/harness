# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
import re
# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
def unsupported_probability_claims(text):
	from .text_core import scan
	lines = [line for line in scan(text) if 'prose' == line.kind]
	r = []
	for line in lines:
		value = re.sub('`[^`]*`|«[^»]*»|"[^"\\n]*"', ' ', line.raw)
		value = re.sub('\\[[^\\]]*\\]\\([^)]*\\)', ' ', value)
		if re.search('(?i)\\b(?:\\u043d\\u0435\\s+(?:\\u043e\\u0437\\u043d\\u0430\\u0447\\u0430\\w*|\\u0434\\u043e\\u043a\\u0430\\u0437\\u044b\\u0432\\u0430\\w*|\\u0443\\u0441\\u0442\\u0430\\u043d\\u0430\\u0432\\u043b\\u0438\\u0432\\u0430\\w*|\\u0441\\u043b\\u0435\\u0434\\u0443\\w*)|does\\s+not|cannot\\s+(?:establish|prove|imply))\\b', value):
			continue
		equality = re.search('(?i)\\u0440\\u0430\\u0432\\u043d\\w*\\s+(?:\\u043f\\u0440\\u043e\\u0446\\u0435\\u043d\\u0442\\w*|\\u0432\\u0435\\u0440\\u043e\\u044f\\u0442\\u043d\\u043e\\u0441\\u0442\\w*|\\u043e\\u0446\\u0435\\u043d\\u043a\\w*)|\\u0440\\u0430\\u0432\\u043d\\u043e\\u0432\\u0435\\u0440\\u043e\\u044f\\u0442\\w*|equal\\s+(?:probabilit\\w*|likelihood\\w*|percentage\\w*)|50\\s*[/—–:-]\\s*50', value)
		ignorance = re.search('(?i)\\u043e\\u0442\\u0441\\u0443\\u0442\\u0441\\u0442\\u0432\\w*\\s+(?:\\u0434\\u043e\\u043a\\u0430\\u0437\\u0430\\u0442\\u0435\\u043b\\u044c\\w*\\s+)?(?:\\u043e\\u0441\\u043d\\u043e\\u0432\\u0430\\u043d\\w*|\\u0434\\u0430\\u043d\\u043d\\w*|\\u0441\\u0432\\u0438\\u0434\\u0435\\u0442\\u0435\\u043b\\u044c\\u0441\\u0442\\u0432\\w*)|\\u043d\\u0435\\s+(?:\\u0437\\u043d\\u0430\\w*|\\u043d\\u0430\\u0445\\u043e\\u0436\\u0443\\s+\\u043e\\u0441\\u043d\\u043e\\u0432\\u0430\\u043d\\w*)|(?:lack|absence)\\s+of\\s+(?:evidentiary\\s+)?(?:basis|data|evidence|information)|no\\s+(?:evidentiary\\s+)?(?:basis|evidence)', value)
		link = re.search('(?i)\\u043e\\u0437\\u043d\\u0430\\u0447\\u0430\\w*|\\u0441\\u043b\\u0435\\u0434\\u043e\\u0432\\u0430\\u0442\\w*|\\u043f\\u043e\\u044d\\u0442\\u043e\\u043c\\u0443|\\u043f\\u043e\\u0442\\u043e\\u043c\\u0443\\s+\\u0447\\u0442\\u043e|\\u043f\\u043e\\u0441\\u043a\\u043e\\u043b\\u044c\\u043a\\u0443|because|therefore|implies|mean\\w*', value)
		if equality and ignorance and link:
			r.append(f'CAUSAL-PROBABILITY:{line.no}: absence of discriminating evidence does not establish equal probabilities; state the prior/basis or leave the cause unresolved')
	return r
