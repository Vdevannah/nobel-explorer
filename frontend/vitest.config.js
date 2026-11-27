import { defineConfig, mergeConfig } from "vitest/config";

import viteConfig from "./vite.config.js";

// Test-only configuration layered on the unchanged Vite config, so the
// production build is not affected.
export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.js"],
      include: ["src/**/*.test.{js,jsx}"],
      restoreMocks: true,
      unstubGlobals: true,
      unstubEnvs: true,
      // Deterministic: no watch mode in CI-style runs, no shared state between files.
      isolate: true,
    },
  }),
);
