import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";

export default defineConfig({
  // Relative base so asset references in HTML work inside moz-extension:// URLs.
  base: "./",
  plugins: [vue()],
  build: {
    rollupOptions: {
      input: {
        options: resolve(__dirname, "options.html"),
      },
    },
    outDir: "dist",
    emptyOutDir: true,
  },
});
