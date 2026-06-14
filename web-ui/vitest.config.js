import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
    // Unit/component tests live under src/; Playwright e2e specs live in e2e/
    // and must not be collected by Vitest (they use the Playwright runner).
    include: ['src/**/*.{test,spec}.{js,jsx}'],
  },
})
