import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: [
      "dazzling-vibrancy-production-7417.up.railway.app",
    ],
  },
});
