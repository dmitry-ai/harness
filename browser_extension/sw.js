// 2026-11-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
// 2026-11-16
// "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
// https://github.com/dmitry-ai/harness/issues/80
const OFFSCREEN_PATH = 'offscreen.html';
let creatingOffscreen = null;
/**
 * @used-by browser_extension/manifest.json
 * @used-by {@link import('./sw.js')}
 */
async function setupOffscreenDocument() {
	const offscreenUrl = chrome.runtime.getURL(OFFSCREEN_PATH);
	const existing = await chrome.runtime.getContexts({
		contextTypes: ['OFFSCREEN_DOCUMENT'],
		documentUrls: [offscreenUrl]
	});
	if (0 < existing.length) {
		return;
	}
	if (null !== creatingOffscreen) {
		await creatingOffscreen;
		return;
	}
	creatingOffscreen = chrome.offscreen.createDocument({
		url: OFFSCREEN_PATH,
		reasons: ['DOM_PARSER'],
		justification: 'Maintain primary Chrome profile browserContextId target and tab broker for Harness GuardedCDP'
	});
	try {
		await creatingOffscreen;
	} finally {
		creatingOffscreen = null;
	}
}
/**
 * @used-by browser_extension/manifest.json
 * @used-by {@link import('./offscreen.js')} (globalThis.__harnessBroker)
 * @used-by {@link import('./sw.js')}
 */
async function dispatchBrokerAction(message) {
	const action = message && 'string' === typeof message.action ? message.action : 'ping';
	if ('ping' === action) {
		return { ok: true, extensionId: chrome.runtime.id, offscreenPath: OFFSCREEN_PATH };
	}
	if ('createBackgroundTab' === action) {
		const targetUrl = message && 'string' === typeof message.url ? message.url : '';
		if (!targetUrl.startsWith('about:blank#')) {
			throw new Error('Broker createBackgroundTab requires an about:blank#<nonce> correlation URL');
		}
		const windows = await chrome.windows.getAll({ windowTypes: ['normal'] });
		const normalWindows = windows.filter((win) => !win.incognito && 'number' === typeof win.id);
		if (0 === normalWindows.length) {
			throw new Error('Primary Chrome profile Default has no open normal non-incognito window');
		}
		const chosen = normalWindows.find((win) => Boolean(win.focused)) || normalWindows[0];
		const created = await chrome.tabs.create({ windowId: chosen.id, url: targetUrl, active: false });
		return { ok: true, tabId: created.id, windowId: created.windowId };
	}
	if ('removeTab' === action) {
		const tabId = message ? message.tabId : null;
		if ('number' !== typeof tabId) {
			throw new Error('Broker removeTab requires a numeric tabId');
		}
		await chrome.tabs.remove(tabId);
		return { ok: true, removed: true, tabId };
	}
	throw new Error('Unsupported broker action: ' + action);
}
chrome.runtime.onStartup.addListener(async () => {
	try {
		await setupOffscreenDocument();
	} catch (_err) {
	}
});
chrome.runtime.onInstalled.addListener(async () => {
	try {
		await setupOffscreenDocument();
	} catch (_err) {
	}
});
chrome.windows.onCreated.addListener(async () => {
	try {
		await setupOffscreenDocument();
	} catch (_err) {
	}
});
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
	(async () => {
		try {
			await setupOffscreenDocument();
			const result = await dispatchBrokerAction(message);
			sendResponse(result);
		} catch (err) {
			sendResponse({ ok: false, error: String(err && err.message ? err.message : err) });
		}
	})();
	return true;
});
(async () => {
	try {
		await setupOffscreenDocument();
	} catch (_err) {
	}
})();
