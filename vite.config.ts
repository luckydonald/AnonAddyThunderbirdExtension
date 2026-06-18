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
      input: {
        options: resolve(__dirname, "options.html"),
        composePopup: resolve(__dirname, "composePopup.html"),
        createAlias: resolve(__dirname, "createAlias.html"),
        background: resolve(__dirname, "src/background/index.ts"),
      },
      output: {
        // Keep background.js name predictable — manifest.json references it directly.
        entryFileNames: (chunk) =>
          chunk.name === "background" ? "[name].js" : "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
    outDir: "dist",
    emptyOutDir: true,
  },
});
