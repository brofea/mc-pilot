import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ command }) => ({
  plugins: [vue()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  // Vite serves locally from `/`; FastAPI serves the compiled app at `/static/app/`.
  base: command === "serve" ? "/" : "/static/app/",
  build: { outDir: "../src/mc_pilot/static/app", emptyOutDir: true },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/admin/api": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/ws": { target: "ws://127.0.0.1:8000", ws: true }
    }
  }
}));
