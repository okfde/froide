import { defineConfig } from '@hey-api/openapi-ts'

export default defineConfig({
  client: '@hey-api/client-fetch',
  input: 'froide/openapi-schema.yaml',
  output: {
    path: 'frontend/javascript/api/gen',
    format: 'prettier',
    lint: 'eslint'
  },
  plugins: [
    '@hey-api/schemas',
    '@hey-api/services',
    {
      dates: true,
      name: '@hey-api/transformers'
    },
    {
      enums: 'javascript',
      name: '@hey-api/types'
    }
  ]
})
