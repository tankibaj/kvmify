import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    // @novnc/novnc uses top-level await; esnext target supports it.
    target: 'esnext',
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://192.168.178.101:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, '')
      },
      '/novnc': {
        target: 'http://192.168.178.101:6080',
        ws: true,
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/novnc/, '')
      }
    }
  }
})
