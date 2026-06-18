/// <reference types="vitest" />
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/tests/setup.ts"],
  },
  // Relative base so asset references in HTML work inside moz-extension:// URLs.
  base: "./",
  plugins: [vue()],
  build: {
    rollupOptions: {
      preserveEntrySignatures: "strict",
      input: {
        options: resolve(__dirname, "options.html"),
        composePopup: resolve(__dirname, "composePopup.html"),
        background: resolve(__dirname, "src/background/index.ts"),
        // Compiled to dist/utils.js for use by the privileged experiment via
        // ChromeUtils.importESModule. Must stay dependency-free at runtime.
        utils: resolve(__dirname, "src/shared/forwardingAddress.ts"),
      },
      output: {
        // Keep background.js and utils.js names predictable — referenced directly.
        entryFileNames: (chunk) =>
          chunk.name === "background" || chunk.name === "utils"
            ? "[name].js"
            : "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
    outDir: "dist",
    emptyOutDir: true,
  },
});
