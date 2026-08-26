import { defineConfig } from "vite";
import { resolve } from "node:path";
import { viteSingleFile } from "vite-plugin-singlefile";

export default defineConfig(({ mode }) => {
  const standalone = mode === "standalone";
  return {
    root: resolve(import.meta.dirname, "src"),
    base: "./",
    publicDir: false,
    clearScreen: false,
    plugins: standalone ? [viteSingleFile()] : [],
    server: {
      host: "127.0.0.1",
      port: 1420,
      strictPort: true,
    },
    build: {
      outDir: resolve(import.meta.dirname, standalone ? "preview-dist" : "dist"),
      emptyOutDir: true,
    },
  };
});
