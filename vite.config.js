import { resolve } from 'path'
import { defineConfig } from 'vite'
import autoprefixer from 'autoprefixer'
import devManifest from 'vite-plugin-dev-manifest'
import vue from '@vitejs/plugin-vue2'

const outputDir = resolve(__dirname, 'build')

// https://vitejs.dev/config/
export default defineConfig({
  base: '/static/',
  resolve: {
    dedupe: ['bootstrap', 'vue', 'pdfjs-dist'],
    extensions: ['.mjs', '.js', '.ts', '.vue', '.json']
  },
  build: {
    manifest: true,
    emptyOutDir: true,
    outDir: outputDir,
    sourcemap: true,
    rollupOptions: {
      input: {
        document: './frontend/javascript/document.js',
        docupload: './frontend/javascript/docupload.js',
        fileuploader: './frontend/javascript/fileuploader.js',
        filingcabinet:
          'node_modules/@okfde/filingcabinet/frontend/javascript/filingcabinet.js',
        geomatch: './frontend/javascript/geomatch.js',
        main: './frontend/javascript/main.ts',
        makerequest: './frontend/javascript/makerequest.js',
        messageredaction: './frontend/javascript/messageredaction.js',
        moderation: './frontend/javascript/moderation.js',
        publicbody: './frontend/javascript/publicbody.js',
        publicbodyupload: './frontend/javascript/publicbodyupload.js',
        redact: './frontend/javascript/redact.js',
        request: './frontend/javascript/request.ts',
        tagautocomplete: './frontend/javascript/tagautocomplete.ts'
      },
      output: {
        sourcemap: true,
        entryFileNames: '[name].js',
        chunkFileNames: 'js/[name].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name.endsWith('.css')) {
            return 'css/[name][extname]'
          } else if (
            assetInfo.name.match(/(\.(woff2?|eot|ttf|otf)|font\.svg)(\?.*)?$/)
          ) {
            return 'fonts/[name][extname]'
          } else if (assetInfo.name.match(/\.(jpg|png|svg)$/)) {
            return 'img/[name][extname]'
          }

          console.log('assetInfo', assetInfo)
          return 'js/[name][extname]'
        }
      }
    }
  },
  server: {
    port: 5173,
    origin: 'http://127.0.0.1:5173',
    fs: { allow: ['..'] }
  },
  plugins: [vue(), devManifest()],
  css: {
    postcss: {
      plugins: [autoprefixer]
    }
  }
})
