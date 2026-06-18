---
name: dts-alongside-js-typing
description: Type a plain JS module for TypeScript import without allowJs — create a matching .d.ts file alongside it
metadata:
    node_type: memory
    type: project
    originSessionId: 30053dbd-5c03-4901-9e6e-3eeb5a0a3a38
---

TypeScript with `moduleResolution: "bundler"` resolves `.js` imports to a matching `.d.ts` file without needing `allowJs: true`. This is used for `src/experiment/pillDecoration.js`:

```typescript
// src/experiment/pillDecoration.d.ts
export declare function decoratePillViaTextNode(
    pill: Element,
    displayText: string | null | undefined,
): boolean;
// ...
```

Then `implementation.ts` can `import { decoratePillViaTextNode } from "./pillDecoration.js"` with full types. At bundle time Vite/Rollup reads the actual `.js` source for content; the `.d.ts` is only for type-checking.

**When to apply:** When a plain `.js` file (e.g. one that must stay as JS for test imports or has special loading requirements) is imported from TypeScript, add a `.d.ts` alongside it instead of converting to `.ts` or enabling `allowJs`. Keeps the JS file importable by both Jest/Vitest (no transpilation needed) and TypeScript consumers.
