<!-- 2026-11-23 "Migrate general code formatting rules with Bash and ES6 guides": https://github.com/dmitry-ai/harness/issues/154 -->  
# JavaScript (ES6) Formatting Standard

Inherits all general rules from [CODE-1](../../../rules/11-code-formatting.md#code-1) (tab indentation, zero blank lines, single return point, variable `r`, Yoda comparisons, shorter `if` branch above longer `else` branch, single quotes by default, alphabetical function ordering, no unrequested comments).  

## Language Version and Declarations

1. Always use modern ES6+ syntax: `const` by default, `let` only when a variable is reassigned, and never `var`.  
1. Prefer arrow functions (`e => ...`), template literals (`` `${...}` ``) for string interpolation, spread syntax (`[...allItems]`), optional chaining (`?.`), and arrow IIFEs (`(() => { ... })();`).  
1. Terminate statements and function-expression assignments with semicolons (`;`).  

## Functions, Braces, and Expressions

1. Omit parentheses around a single untyped arrow parameter (`e => { ... }`, `b => { ... }`, `mm => { ... }`).  
1. Use concise expression arrow bodies without braces or `return` when returning a single expression (`i => 'Just not interested' === i.textContent.trim()`, `() => p() ? clearInterval(i) : null`).  
1. Place opening `{` on the same line as the controlling statement or arrow; place `else` on a new line after `}` (`}\nelse {`).  
1. Write compact object literals without padding spaces inside braces (`{attributes: true, attributeFilter: ['style']}`).  

## Comparisons, Quotes, and Naming

1. Use strict equality (`===`, `!==`) with constants on the left (`'Enter' === e.key`, `'attributes' === m.type && 'style' === m.attributeName`).  
1. Use single quotes (`'...'`) for static strings and CSS selectors containing double-quoted attributes (`'article[data-test="JobTile"]'`); use template literals (`` `${u.origin}/jobs/~${m[1]}` ``) for interpolation.  
1. Prefer concise contextual names (`e` for event, `mm`/`m` for collection and item, `c` for container, `i` for item or interval handle, `r` for return value when needed).  

<!-- 2026-11-26 "Codify navigable cross-reference standards and override SLOC exemption": https://github.com/dmitry-ai/harness/issues/286 -->  
## Cross-Reference Annotations (JavaScript / ES6 / TypeScript)

Writing new JavaScript, ES6, or TypeScript code without navigable cross-reference annotations is prohibited, and every code edit must keep them synchronized via `harness.py xref-sync` and verified via `harness.py xref-check`.  

1. Place `@used-by`, `@uses`, `@see`, and (in JavaScript) `@override` inside a JSDoc `/** ... */` block immediately above each named function, arrow-function constant, or class method (below any contextual GitHub Issue URL comment), wrapping every JS/TS symbol target in `{@link ...}` so IntelliJ IDEA `2026.3+` (`JSDocInlineTags` / `JSDocTagReferencesHolderImpl`) and TypeScript resolve `Ctrl+Click`, `Find Usages`, and `Rename` without adding runtime imports.  
1. Every named function and class method without exception must carry a complete, alphabetically sorted `@used-by` list: use `{@link fnName}` or `{@link ClassName#method}` for same-file callers, `{@link import('./file.js').exportedName}` or `{@link import('./file.js').ClassName#method}` for exported cross-file callers, `{@link import('./file.js')} (localCaller)` for unexported cross-file callers, and plain non-JS paths (e.g., `@used-by browser_extension/manifest.json` or `@used-by node:test`) for external/runtime entry points.  
1. Every overriding method on a subclass must carry `@override` in JSDoc (in JavaScript) or the native `override` modifier keyword (in TypeScript), paired with `@see {@link BaseClass#method}` (or `@see {@link import('./base.js').BaseClass#method}`) referencing the exact overridden parent method.  
1. Explicitly document direct, non-trivial, or dynamic dependencies invisible to static analysis (`obj[dynamicKey](...)`, `require(dynamicPath)`, `chrome.runtime.sendMessage`, CDP `Runtime.evaluate`, IPC/bridge dispatches) with `@uses {@link ...}` (or plain path/channel identifiers for non-JS targets) so `harness.py xref-sync` propagates reverse `@used-by` edges deterministically.  

## Illustrative Examples

These examples illustrate formatting only and are not part of any target program; never copy them into answers or target scripts.  

### DOM Event Handlers and Branch Ordering

```javascript
const openArticle = b => {
	const article = b.closest('article[data-test="JobTile"]');
	if (article) {
		const l = article.querySelector('a[data-test="job-tile-title-link UpLink"]');
		if (l) {
			const u = new URL(l.href);
			const m = u.pathname.match(/_~(\d+)(?=\/|$)/);
			window.open(`${u.origin}/jobs/~${m[1]}`, '_blank');
		}
	}
};
const stopEvent = e => {
	e.preventDefault();
	e.stopPropagation();
	e.stopImmediatePropagation();
};
(() => {
	let x = 0, y = 0, article;
	const updateArticle = () => {
		article = document.elementFromPoint(x, y)?.closest('article[data-test="JobTile"]');
	};
	document.addEventListener('mousemove', e => {
		x = e.clientX; y = e.clientY;
		updateArticle();
	}, true);
	document.addEventListener('scroll', updateArticle, true);
	document.addEventListener('keydown', e => {
		if ('Enter' === e.key) {
			stopEvent(e);
			openArticle(article);
		}
	}, true);
})();
document.addEventListener('click', e => {
	const i = e.target;
	const menuItemClass = 'air3-menu-item';
	if (!i.classList.contains(menuItemClass) && e.target.closest('article')) {
		const downBtn = i.closest('button[data-ev-label="dropdown_secondary_toggle"]');
		if (!downBtn) {
			stopEvent(e);
			openArticle(e.target);
		}
		else {
			setTimeout(() => {
				const allItems = document.querySelectorAll('.' + menuItemClass);
				const i = [...allItems].find(i => 'Just not interested' === i.textContent.trim());
				i ? i.click() : null;
			}, 50);
		}
	}
}, true);
```

### Compact Observer and Polling IIFE

```javascript
(() => {
	const p = () => {
		const c = document.querySelector('.conversation-container');
		if (c) {
			const observer = new MutationObserver(mm => {
				mm.forEach(m => {
					if ('attributes' === m.type && 'style' === m.attributeName) {
						c.style.removeProperty('min-height');
					}
				});
			});
			observer.observe(c, {attributes: true, attributeFilter: ['style']});
		}
		return !!c;
	};
	const i = setInterval(() => p() ? clearInterval(i) : null, 50);
})();
```
