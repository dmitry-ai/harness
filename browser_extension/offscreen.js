// 2026-11-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
// "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
// https://github.com/dmitry-ai/harness/issues/80
globalThis.__harnessBroker = async (payload) => {
	const response = await chrome.runtime.sendMessage(payload || { action: 'ping' });
	return response;
};
