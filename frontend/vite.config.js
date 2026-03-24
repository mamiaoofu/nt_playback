import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    watch: {
      usePolling: true,
    },
    // listen on all interfaces inside the container
    host: '0.0.0.0',
    port: 8001,
    // HMR: let client connect to the page origin (works for localhost and LAN)
    // remove explicit `host` so client uses the current origin automatically
    hmr: {
      // protocol: 'ws',
      clientPort: 443,
    },
    // allow Host headers coming from the proxy container and LAN
    allowedHosts: ['frontend', 'localhost', '127.0.0.1', '192.168.1.90', '192.168.1.202','ecmnichetelcomm.ddns.net']
    ,
    // Proxy API and auth requests from the dev server to the backend container
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path,
      },
      '/login': {
        target: 'http://backend:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})
