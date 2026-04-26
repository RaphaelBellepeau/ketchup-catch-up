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

  // Routes that must be proxied so the browser sees them as same-origin.
  // The Gradbot voice client creates Web Workers from /static/js/* — workers
  // refuse cross-origin script URLs even with CORS allow-all, so this proxy
  // is mandatory for voice to work in dev.
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
        "/static": proxyHttp,
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
