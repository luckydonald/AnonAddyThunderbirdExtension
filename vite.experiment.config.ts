import { defineConfig } from "vite";
import { resolve } from "path";

// Builds src/experiment/implementation.ts as a standalone IIFE.
//
// Rollup emits: var AddressChipMenu = (function () { ... return class...; }());
//
// When TB loads this file via loadSubScript(url, sandbox), `var` at script
// top level creates a property on the sandbox object — exactly where TB looks
// for the experiment class. ChromeUtils / Services / Ci are passed as IIFE
// parameters so they stay as global references in the output.
export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        implementation: resolve(__dirname, "src/experiment/implementation.ts"),
      },
      external: ["ChromeUtils", "Services", "Ci"],
      output: {
        format: "iife",
        entryFileNames: "[name].js",
        // The IIFE is a pure side-effect: it runs globalThis.AddressChipMenu = class...
        // inside the body. In TB's loadSubScript sandbox, globalThis === sandbox, so
        // sandbox.AddressChipMenu gets the class without needing a top-level var.
        globals: {
          ChromeUtils: "ChromeUtils",
          Services: "Services",
          Ci: "Ci",
        },
        inlineDynamicImports: true,
      },
    },
    outDir: "dist/experiment",
    emptyOutDir: false,
    minify: false,
  },
});
