---
name: vite-entry-splitting-popup
description: Adding a TS file as a Vite entry with preserveEntrySignatures breaks the popup — Rollup extracts shared modules as external chunks
metadata:
    node_type: memory
    type: feedback
    originSessionId: 30053dbd-5c03-4901-9e6e-3eeb5a0a3a38
---

Do NOT add shared TypeScript files as additional Vite entries to produce a separately loadable `dist/utils.js`. This approach was tried and broken the popup.

**Why:** Adding a TS file to `rollupOptions.input` with `preserveEntrySignatures: "strict"` causes Rollup to extract that file as an external module. Any other bundle that imports from it gets a relative import (`"../utils.js"`) instead of an inline copy. If that external file fails to load in Thunderbird (e.g. due to path resolution in `moz-extension://` context), the entire popup fails to mount — showing only a white screen.

**How to apply:** When you need shared code in both the popup and the experiment, compile it into the experiment via a separate IIFE build (see [[experiment-iife-build]]). The popup bundle stays self-contained (no external module references). Never add `preserveEntrySignatures: "strict"` to `vite.config.ts`.
