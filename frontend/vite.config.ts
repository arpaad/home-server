import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// The API serves the built client from its own origin in production, so the
// client always calls /api on whatever host it was loaded from. In
// development Vite proxies that to the backend, which keeps the client's code
// identical in both and keeps CORS out of the picture entirely.
const BACKEND = process.env.HOME_API_URL ?? 'http://127.0.0.1:8080'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'H.O.M.E. Shopping',
        short_name: 'Shopping',
        description: "The household's shared shopping list",
        theme_color: '#1f6f43',
        background_color: '#faf9f6',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        // Precache the application shell only. List data must never be served
        // from a cache: the spec requires the client to say it cannot confirm
        // the list is current, and a cached list would look current while
        // being wrong — which is worse than showing nothing.
        globPatterns: ['**/*.{js,css,html,svg,png,webmanifest}'],
        navigateFallback: 'index.html',
        navigateFallbackDenylist: [/^\/api/, /^\/docs/, /^\/openapi\.json/, /^\/health/],
        runtimeCaching: [],
skipWaiting: true,
        clientsClaim: true,
      },
      devOptions: { enabled: false },
    }),
  ],
  server: {
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
    },
  },
  // `vite preview` serves the production build, which is what the end-to-end
  // tests run against: the manifest and service worker only exist there.
  preview: {
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
    },
  },
})
