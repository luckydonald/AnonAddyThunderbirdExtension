---
name: experiment-iife-build
description: "How the experiment is compiled to a privileged IIFE via a second Vite config, and why globalThis works for sandbox registration"
metadata: 
  node_type: memory
  type: project
  originSessionId: 30053dbd-5c03-4901-9e6e-3eeb5a0a3a38
---

The experiment (`src/experiment/implementation.ts`) is compiled by a **second Vite config** (`vite.experiment.config.ts`, format: `"iife"`) that Rollup bundles independently of the main popup/options/background build. This eliminates code duplication: shared helpers from `src/shared/forwardingAddress.ts` and `src/experiment/pillDecoration.js` are bundled directly into `dist/experiment/implementation.js` via normal `import` statements and tree-shaking.

**Why `globalThis` registers the class correctly:**
TB loads experiment scripts via `loadSubScript(url, sandbox)`. In Firefox's sandbox compartment, `globalThis` IS the sandbox object. So `(globalThis as any).AddressChipMenu = class extends ...` inside the IIFE registers the class exactly where TB's experiment loader looks (`sandbox["AddressChipMenu"]`). This works in strict mode — `globalThis` is never `undefined`, unlike `this` inside a strict-mode function.

**Vite/esbuild export-stripping trap:**
`export default class` in TypeScript does NOT produce a `var X = (function(){...}())` IIFE wrapper. Vite/esbuild strips the `export` keyword during TypeScript transpilation before Rollup sees it, so Rollup finds no exports and ignores the `name` option entirely — emitting a bare `(function(){...})()` with no assignment. `exports: "default"` throws because it sees "undefined" exports. **Solution:** don't use the export mechanism at all; assign directly to `globalThis` as a side effect.

**Rollup config for the experiment build:**
```typescript
// vite.experiment.config.ts
rollupOptions: {
  input: { implementation: resolve(__dirname, "src/experiment/implementation.ts") },
  external: ["ChromeUtils", "Services", "Ci"],
  output: {
    format: "iife",
    entryFileNames: "[name].js",
    globals: { ChromeUtils: "ChromeUtils", Services: "Services", Ci: "Ci" },
    inlineDynamicImports: true,
  },
},
outDir: "dist/experiment",
emptyOutDir: false,  // don't wipe files from the first build
minify: false,
```

`package.json build` runs both: `vite build && vite build --config vite.experiment.config.ts`.

**Why:** [[chromeutilsimportesmodule-moz-extension-limitation]] — `ChromeUtils.importESModule` cannot load `moz-extension://` URLs, so runtime import of shared helpers is impossible. Compile-time bundling via a second IIFE build is the only duplication-free solution.
