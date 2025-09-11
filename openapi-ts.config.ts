import { defineConfig } from '@hey-api/openapi-ts'

export default defineConfig({
  input: './froide/openapi-schema.yaml',
  output: {
    path: 'frontend/javascript/api/gen',
    format: 'prettier',
    lint: 'eslint'
  },
  plugins: [
    '@hey-api/client-fetch',
    '@hey-api/schemas',
    '@hey-api/sdk',
    {
      dates: true,
      name: '@hey-api/transformers'
    },
    {
      enums: 'javascript',
      name: '@hey-api/typescript'
    }
  ]
})
