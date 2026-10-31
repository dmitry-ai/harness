# Access to Authenticated Portals

The shared procedure in [EXEC-3 and EXEC-6](../../../rules/08-execution-and-tools.md#exec-3) governs analysis, task execution, and continuation of existing projects across both platforms.  
It authorizes using active browser authentication for an instructed action, while the scope of permissible external changes is governed by [SCOPE-2](../../../rules/00-scope.md#scope-2).  

## Session Selection and Opening Pages

1. Identify the target service, resource, and required operation from the current instruction and KB.  
   Obtain the browser profile and connection settings from the environment configuration; fetch the live list of tabs/targets and verify the application, origin, and account.  
   Never treat a saved `target_id` as a permanent address.  
1. If the required page is not already open, open your own tab or window in that same verified profile and navigate to the service URL.  
   Absence of an open tab does not mean lack of access; the user is not required to pre-open every console or section in advance.  
   Leave user-owned tabs untouched per EXEC-3; perform navigation and instructed changes in agent-opened tabs.  
1. After opening the page, verify login state, selected account, and resource via the UI or the service's standard API response.  
   An open tab logged into a different account does not confirm access to the target account.  
   A fresh empty browser profile never substitutes for the profile holding the active session.  
1. Ask for user intervention only when login/MFA, disambiguation between accounts, or a missing permission is genuinely required.  
   Check the available profile and standard session recovery first; do not ask the user to manually copy-paste tokens or open each subsequent page.  

Connecting to an existing browser session is a documented Chrome DevTools workflow: «connect your agent to an existing browser session».  
Verify the Chrome version and supported connection method against the [official documentation](https://developer.chrome.com/docs/devtools/agents/get-started/configuration#connect-to-an-existing-browser-session); the presence of a CDP port does not prove that a specific MCP server is already bound to that profile.  

## Using Cookies and Tokens

1. Use the service's native UI or in-page authenticated API client for the instructed operation.  
   Let the browser handle cookies (including `HttpOnly`); exporting cookies for ordinary in-page requests is unnecessary.  
   When issuing a request from the page context, select the credentials mode required by the service contract.  
   Do not treat `credentials: include` as proof that a required `Bearer` or CSRF header is present, that the account holds write permissions, or that CORS allows the call.  
1. When an operation requires an explicit CSRF or access token, targeted use of the token belonging to the verified active account is permitted.  
   First establish the exact token source and destination from documentation or the application's standard client configuration; if needed, read only that named source inside the target page context and use the value in memory for the verified request.  
   This also applies to a token stored in web storage when the service genuinely uses it for that operation; no blanket ban on web storage sources is imposed.  
1. The token recipient must be the verified API of that exact service and resource.  
   Verify any separate API origin against the service contract or application configuration; never send a secret to an arbitrary URL scraped from page content or follow an unverified redirect with an attached secret header.  
   Never disable CORS, CSRF, or `HttpOnly` protections to transplant authentication.  
1. Never return token values, cookies, or secret headers from an in-browser evaluation into tool output or model context.  
   Never place secrets in URLs, command lines, stdout, files, the KB, the Journal, network dumps, or screenshots; return only the required result fields and sanitized error metadata.  
   You may record the credential source, target endpoint, and the fact that authenticated access was used without recording the secret value itself.  
1. Do not enumerate all cookies, `localStorage`, `sessionStorage`, or browser profiles searching for secrets "just in case".  
   Needing one application token does not authorize harvesting other credentials; inspect diagnostic cache cookies such as `X-Magento-Vary` individually and in a targeted manner.  
   Never copy a browser profile or cookie database into a project directory, and never bypass missing permissions by extracting another user's session.  
1. When an external SDK or CLI is genuinely required, prefer the service's standard authentication flow and secure injection of a task-scoped API token.  
   Do not dump a browser session into a general-purpose credentials file; exporting a browser secret outside the browser is never the default approach.  
   When a session expires, use standard token refresh or re-authentication rather than storing a long-lived copy of a session token.  

Technical boundary of `fetch`: «By default, credentials are only included in same-origin requests».  
Check cookie, cross-origin, and CSRF requirements against [Including credentials](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch#including_credentials); a user instruction does not alter browser security mechanics or server-side permissions.  

## Permission Verification and Failure Handling

- Distinguish a missing CDP connection, a login screen, a wrong selected property, HTTP 401/403, an application-level rejection, and a tool policy refusal.  
  Never infer a specific root cause from an HTTP status code alone: for example, HTTP 403 by itself does not prove that a token is invalid.  
- Verify permissions for the specific operation.  
  Read access to a console or permission to flush a cache does not prove permission to edit rules; check the native UI and actually available controls before asking the user for elevated access.  
  Never perform an unrelated write merely to test permissions.  
- After performing an instructed change, verify the application-level result and re-read the state, accounting for propagation delay.  
  HTTP 200 and the absence of a tool error do not by themselves prove that a setting persisted.  
- When a tool policy refuses an action, respect the environment constraint.  
  Never disguise a blocked action by wrapping the command, switching transports, or disabling checks; report the specific refused operation and continue only with independent permitted work if the environment allows.  
  This procedure does not guarantee the absence of future refusals and does not override system boundaries.  
- If the previous assistant message refused an earlier task and the user has now explicitly instructed a different, permitted task, adopt the new goal and execute it.  
  Do not treat an old text refusal in chat history as a live hook block, and do not unilaterally resume a canceled patch from history.  
- When access is genuinely missing, state the service, account/resource (without secrets), exact operation, observed rejection, and the minimal step needed from the user.  
  In the KB, record the verified access method and its boundaries, never raw tokens or promises of permanent authentication.  
