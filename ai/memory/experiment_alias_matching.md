---
name: experiment-alias-matching
description: "Alias matching in the experiment must use description-based logic, not email-based, to match the popup"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b3c2110f-ae97-47f6-bf3d-647bd0eaab60
---

The popup (`src/popup/utils.ts` `matchingAliases`) matches aliases by
**description containing the recipient domain** (e.g. "Shopping alias for
example.com").  AnonAddyTB sets descriptions in exactly this form when it
creates aliases.

The experiment's `matchingAliasesForEmail` was instead filtering by
`a.email.toLowerCase().includes(domain)` — finding aliases whose *own email
address* happened to contain the recipient domain (e.g. an alias at
`relay.example.com` for a recipient at `example.com`).  This returned entirely
different, usually empty, results.

**Why:** The two UI surfaces (toolbar popup and right-click chip menu) were
showing different alias candidates for the same recipient, with the chip menu
showing nothing useful.

**How to apply:** Both `matchingAliases` (popup) and `matchingAliasesForEmail`
(experiment) should filter with:
```javascript
(a.description ?? "").toLowerCase().includes(domain)
```
Keep the two implementations in sync; `src/experiment/utils.js` is the
extracted testable version of the inline function in `implementation.js`.

See also: [[marionette-tb-chrome-patterns]]
