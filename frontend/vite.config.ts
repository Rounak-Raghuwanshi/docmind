import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5173,
    // Same-origin /api in development, exactly like the Vercel rewrite in production,
    // so the httpOnly refresh cookie is first-party in both.
    proxy: {
      "/api": { target: process.env.VITE_DEV_API_TARGET ?? "http://localhost:8000", changeOrigin: true },
    },
  },
  build: {
    sourcemap: true,
    // three.js (~200 KB gzipped) is lazy-loaded only on 3D views, so a large chunk is expected.
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          pdf: ["react-pdf"],
          charts: ["recharts"],
          markdown: ["react-markdown", "remark-gfm"],
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
