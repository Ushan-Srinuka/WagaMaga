import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { apiPort, webPort } from './e2e/environment.ts'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: webPort,
    strictPort: true,
    proxy: {
      '/health': `http://127.0.0.1:${apiPort}`,
      '/docs': `http://127.0.0.1:${apiPort}`,
      '/openapi.json': `http://127.0.0.1:${apiPort}`,
      '/api': `http://127.0.0.1:${apiPort}`,
    },
  },
  test: {
    include: ['src/**/*.test.{ts,tsx}'],
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    restoreMocks: true,
  },
})
