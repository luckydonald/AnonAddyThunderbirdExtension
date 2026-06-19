# Addy for Thunderbird

[GitHub][gh] |
[Bug reports and suggestions][issues]

## About this fork

This is a fork of [jikamens/AnonAddyTB][upstream] written by Jonathan Kamens, which
provides the original integration of [addy.io][addyio] / [AnonAddy][anonaddy]
into Thunderbird. The upstream extension is also available on
[addons.thunderbird.net][atn].

This fork rewrote the extension from the ground up — new build system,
TypeScript + Vue 3 source, a richer popup UI, and a WebExtension Experiment
that integrates into Thunderbird's native address-pill context menus. See
[What was added in this fork](#what-was-added-in-this-fork) below for the full
list.

Maintainer of this fork: Lucky Lucy

Copyright &copy; 2025 Jonathan Kamens (original). Modifications copyright
&copy; 2026 Lucky Lucy. Released under the terms of the Mozilla Public
License, v. 2.0. Full text of the MPL can be found in
[LICENSE.txt](LICENSE.txt).

This extension and its maintainers are not affiliated with the maintainer of
the addy.io service.

## Details about the extension

"Addy for Thunderbird" is a Thunderbird extension that integrates
[addy.io][addyio] or any self-hosted [AnonAddy][anonaddy] server into the
Thunderbird message composition window.

This extension adds a button to the composition toolbar. When you click that
button, it examines the recipient addresses for the message you are composing,
identifies which AnonAddy aliases correspond to those recipients, and opens a
window allowing you to select from the aliases it found and/or create new ones.
When everything looks correct, you click **Apply** and the extension transforms
the recipient addresses into their corresponding outbound Addy forwarding
addresses. The message is routed through the Addy server and the recipient sees
your Addy alias as the return address instead of your real address.

You can also **right-click any address pill** in the To, Cc, or Bcc field and
choose from the Addy submenu to replace an address or create a new alias
without opening the full popup.

For the extension to match aliases to recipients, include the target email
address or domain in the **description** field of each alias on your Addy
server. For example, an alias you use for everyone at "example.com" should have
"example.com" somewhere in its description; one for "bob@example.com"
specifically should include that full address.

When you first install the extension, the options page opens automatically. Fill
in your addy.io or AnonAddy API key (see [here][apikey] for addy.io) and save.
Optionally specify the base URL of a self-hosted AnonAddy server; if you do,
you are prompted to grant the extension permission to make API calls to that
server when you save.

## What was added in this fork

### UI / UX

- **Dedicated popup window** — the alias selector opens as its own window (not a cramped inline compose toolbar popup), with proper sizing
- **Right-click context menu on address pills** — right-clicking any To/Cc/Bcc address pill shows an "Addy" submenu with icons, merging into Thunderbird's existing pill context menu; Reply-To is excluded
  - submenu offers "Existing…" (pick a known alias) and "New…" (create a new alias) directly from the address
- **Human-readable pill display for aliased addresses** — a forwarding address like `alias+them=their-host.com@anon.email` is displayed as `alias@anon.email → them@their-host.com`
- **Sends via / Sends as** — each alias card shows both the internal forwarding address (_Sends via_) and the outward-facing alias address the recipient sees (_Sends as_)
- **Typeahead domain dropdown** — the domain selector in "Create new alias" is a typeahead input; IDN (`xn--…`) domains show both their Punycode and Unicode forms
- **Alias creation merged into selection list** — a newly created alias is immediately added to the radio-button list; you can disable/delete it or deselect it without re-opening anything
- **Unambiguous Disable / Delete labels** — buttons are clearly labelled as acting on the alias on the Addy server, not on the current compose session
- **"Don't replace" restores original address** — selecting "Don't replace" on an already-aliased recipient reverts it; the Apply button is enabled for that action
- **Sender account validation** — if the sending account's address is not one of the alias recipients, the Addy toolbar button pulses red and shows an error on click
- **Redirect to settings when unconfigured** — clicking the Addy button before settings are filled in goes straight to the options page
- **Refresh button** — manual refresh in the popup re-fetches aliases from the API; context menu aliases also refresh from cache on open
- **Responsive layout** — format pills and all popup content wrap on narrow windows; no horizontal overflow

### Options page

- **API key shown as password field** with a show/hide toggle
- **Explicit permission feedback** — distinct status messages for permission granted, permission denied, and save errors (including which host permission was needed)

### Architecture & build

- **Full TypeScript + Vue 3 + SCSS rewrite** (was vanilla JS/HTML) — all three entry points (options, popup, background) are now TypeScript with full type annotations
- **Vite build pipeline** replaces a hand-rolled zip Makefile; tree-shaking and module splitting keep the XPI lean
- **WebExtension Experiment (`AddressChipMenu`)** — privileged XUL code that injects into Thunderbird's compose window chrome to attach the address-pill context menu, built as a separate IIFE via a second Vite config
- **Background alias cache** — the service worker pre-fetches and paginates all aliases hourly; the popup merges a targeted `filter[search]` API call on open for fast startup
- **`parseForwardingAddress()`** — round-trips the `local+orig=domain@aliasDomain` forwarding format so reopening the popup on an already-aliased draft recovers the original recipients

### Testing

- **Vitest unit tests** for alias search/matching logic, forwarding-address parsing, and pill display formatting
- **Python Marionette integration tests** (using `uv`) that drive a real Thunderbird instance, covering compose-window extension load, popup interaction, and context-menu behaviour
- **Shared JSON mock fixtures** under `tests/fixtures/` used by both JS and Python test suites for consistent assumptions
- **SMTP capture harness** (`tests/smtp_harness.py`) — a local SMTP server that captures outgoing raw headers; used in Marionette tests to assert aliased addresses appear correctly in sent mail and display-only "→" pill labels do not leak into outgoing headers

## Building

See [DEVELOPER.md](DEVELOPER.md) for prerequisites, build commands, and testing instructions.

[atn]: https://addons.thunderbird.net/thunderbird/addon/addy-io-anonaddy
[upstream]: https://github.com/jikamens/AnonAddyTB
[gh]: https://github.com/luckydonald/AnonAddyThunderbirdExtension
[issues]: https://github.com/luckydonald/AnonAddyThunderbirdExtension/issues
[addyio]: https://addy.io/
[anonaddy]: https://github.com/anonaddy/AnonAddy
[apikey]: https://app.addy.io/settings/api
