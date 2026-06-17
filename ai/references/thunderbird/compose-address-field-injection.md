# Compose Window Address-Field Injection — Feasibility Research

**Date:** 2026-06-17  
**Verdict: Not feasible with current Thunderbird 115+ MV3 WebExtension APIs.**

## What was investigated

Whether it is possible to inject a context menu or custom dropdown into the individual
address "pill" widgets in Thunderbird's compose window To/CC/BCC fields.

## Findings

### `messenger.menus` contexts

The four compose-related context types are:
- `compose_action` — right-click on the composeAction button
- `compose_action_menu` — composeAction button of type menu
- `compose_attachments` — right-click on an attachment
- `compose_body` — right-click inside the message body editor

**There is no `compose_address` or similar context for the address header fields.**
The `onClicked` event has a `fieldId` property (`composeTo`, `composeCc`, …) but this
only identifies which field triggered the event — it does not allow injecting UI into
address chips.

### Compose scripts (`scripting.compose`)

Injected into the message **body** area only, not the address header. The compose window
chrome (header area with address pills) is rendered in Thunderbird's native XUL chrome,
not a web-content frame accessible to content scripts. Bugzilla #1622502 confirms:
Thunderbird's main UI is never accessible via content scripts.

### `messenger.compose.*` API

`getComposeDetails()` / `setComposeDetails()` return recipients as an array of RFC 2822
strings. There is no API for individual address chip state, hover, click events, or
selection. The whole list can be read and rewritten; individual tokens cannot be instrumented.

### DOM injection

Not possible via standard WebExtension APIs. WebExtension Experiments (privileged,
requires signing bypass, incompatible with ordinary signed AMO extensions) would be the
only path — not a viable option for a normal extension.

### Community evidence

No public examples of address-field pill injection via WebExtensions exist. The AutoMention
extension uses `scripting.compose` for contact suggestions, but injects into the **body**
(on `@` trigger), not the address fields.

## Conclusion

The existing `composeAction` popup approach — reading recipients via `getComposeDetails()`
and rewriting them via `setComposeDetails()` — is the best available design and is
already implemented. Phase 4 is deferred indefinitely pending new Thunderbird API surface.
