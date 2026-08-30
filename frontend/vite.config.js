import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// docs/02-tech-stack.md — Vite is the frozen build tool for this project.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  build: {
    // Recharts + D3 is the only heavy dependency; splitting it keeps the
    // initial chunk small enough to render the KPI skeleton fast (NFR-5).
    // Recharts + D3 is a single ~590 kB vendor chunk. It is split out
    // deliberately (below) and cached separately, so the default 500 kB warning
    // is not signal here.
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        manualChunks: {
          charts: ['recharts'],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
    css: false,
  },
});
