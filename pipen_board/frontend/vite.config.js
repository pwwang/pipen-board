import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { nodePolyfills } from 'vite-plugin-node-polyfills'

// https://vitejs.dev/config/
export default defineConfig({
  build: {
    outDir: 'build',
    chunkSizeWarningLimit: 4000,
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name].js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/[name].[ext]',
      },
    },
  },
  plugins: [
    svelte({
      onwarn: (warning, handler) => {
        if (warning.code === "a11y-interactive-supports-focus") return;
        if (warning.code === "a11y-no-noninteractive-element-interactions") return;
        if (warning.code === "a11y-no-static-element-interactions") return;
        handler(warning);
      }
    }),
    nodePolyfills(),
  ],
})
