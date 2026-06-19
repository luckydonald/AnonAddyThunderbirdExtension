---
name: unittest-marionette-fix-session
description: "Regression-test and Thunderbird/Marionette fixes from the context-menu alias refresh session"
metadata:
    node_type: memory
    type: project
    originSessionId: codex-2026-06-19
---

# Unit And Marionette Fix Session

These notes capture the practical failures fixed while adding coverage for the
context-menu icon, stale alias refresh, alias creation, popup apply, and window
lifecycle work.

## Build the extension from clean state for Marionette

The Makefile target can leave `dist/experiment/implementation.js` stale because
the target depends on the `dist/` directory timestamp, not every source file.
The Marionette fixture should run `make clean` before `make` when packaging the
extension for Thunderbird. Otherwise Thunderbird may load an older experiment
script and tests can fail while the source tree looks correct.

## Start compose from the active main mail window

Thunderbird may leave the Add-ons Manager or another chrome window/tab as the
most recent window. Before opening compose, switch to a `mail:3pane` chrome
window and select/activate a real mail or folder tab. Prefer calling
`window.MsgNewMessage(null)` on that selected window instead of using
`Services.wm.getMostRecentWindow("mail:3pane")` after other window enumeration.

Record existing `msgcompose` handles before opening and wait for the newly added
handle. Close compose windows in `finally` blocks so later tests do not inherit
stale compose state.

## Seed storage, permissions, and background explicitly

Marionette tests that exercise API-backed extension behavior should seed
`options`, `aliasCache`, and `domainOptions` through `ExtensionStorageIDB`. When
the mock API host is not covered by manifest host permissions, inject the origin
permission with `ExtensionPermissions.add(policy.extension.id, { origins:
[host + "/*"], permissions: [] })`.

For MV3 backgrounds, wake the extension with
`policy.extension.wakeupBackground()`; `backgroundContext.wakeUp` is not the
right hook in this Thunderbird runtime.

## Mock server should record reads too

The stale Existing menu regression depends on proving that the menu refreshed
aliases from the API, not just that existing seeded cache data rendered. Record
GET requests in the Marionette mock server as well as POST/PATCH/DELETE.

## Privileged experiment HTTP details

When the experiment performs direct API work with `NetUtil`, set the upload
stream before assigning `channel.requestMethod`. If the method is set first, the
upload setup can overwrite the intended POST method and Thunderbird may send the
request as PUT.

Keep direct experiment-side cache writes limited to the storage-backed fallback
paths that need to work even when the background listener has gone stale.

## Popup frame scripts must avoid CSP eval

The extension popup is a remote browser. Use `messageManager.loadFrameScript`
to inspect or click content from Marionette, but do not rely on dynamic `eval`
inside the popup document. Build a small frame script that evaluates the needed
expression before sending the result back with `sendAsyncMessage`.

For radio and checkbox inputs in Vue forms, set `checked = true` and dispatch
`input` and `change`. Avoid an extra `click()` afterward, because it can toggle
the control back and leave Vue state unchanged.

## Keep failure diagnostics close to the broken surface

For XUL menu failures, collect labels from the injected Addy root menu and the
current pill attributes. For API assertions, include recorded mock-server
requests and any visible menu command errors. Do not leave broad production
debug attributes or console traces behind after the failure mode is understood.
