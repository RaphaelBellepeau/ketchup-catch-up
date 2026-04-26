import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  // Resolve the proxy target from VITE_API_BASE_URL so dev can hit either a
  // local uvicorn or Cloud Run, transparently.
  const apiHttp = (env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
  const apiWs = (env.VITE_WS_BASE_URL || apiHttp.replace(/^http/, "ws")).replace(/\/$/, "");

  // Backend-only routes that must look same-origin to the browser:
  // `/api/audio-config` is a backend endpoint and the WS upgrade for voice.
  // Gradbot's static JS bundles are vendored under `public/static/js/` and
  // served directly by Vite, so they don't need proxying anymore.
  const proxyHttp = {
    target: apiHttp,
    changeOrigin: true,
  };
  const proxyWs = {
    target: apiWs,
    changeOrigin: true,
    ws: true,
  };

  return {
    server: {
      host: "::",
      port: 8080,
      hmr: { overlay: false },
      proxy: {
        "/api/audio-config": proxyHttp,
        "/ws": proxyWs,
      },
    },
    plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
      dedupe: [
        "react",
        "react-dom",
        "react/jsx-runtime",
        "react/jsx-dev-runtime",
        "@tanstack/react-query",
        "@tanstack/query-core",
      ],
    },
  };
});
