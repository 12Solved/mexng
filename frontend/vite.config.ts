import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, '../'), '')
  const basePath = env.VITE_BASE_PATH ?? '/'

  return {
    plugins: [react(), tailwindcss()],
    envDir: '../',
    base: basePath,
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      proxy: {
        [`${basePath}api`]: {
          target: 'http://127.0.0.1:8000',
          rewrite: (path) => path.replace(new RegExp(`^${basePath}api`), ''),
        },
      },
    },
  }
})
