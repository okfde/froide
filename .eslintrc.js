module.exports = {
  parserOptions: {
    sourceType: 'module',
    parser: '@typescript-eslint/parser',
    project: ['./tsconfig.json'],
    extraFileExtensions: ['.vue']
  },
  parser: 'vue-eslint-parser',
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-essential',
    'plugin:vue/vue3-strongly-recommended',
    'prettier'
  ],
  plugins: ['@typescript-eslint', 'prettier', 'html'],
  ignorePatterns: ['node_modules/**', '**/static/**'],
  rules: {
    indent: 'off',
    'prettier/prettier': 'error',
    'space-before-function-paren': [
      'error',
      {
        anonymous: 'always',
        named: 'never',
        asyncArrow: 'always'
      }
    ],
    "no-unused-vars": "off",
    "@typescript-eslint/no-unused-vars": "error"
  },
  overrides: [
    {
      files: ['*.ts', '*.tsx'],
      rules: {
        // TODO: remove these exceptions
        '@typescript-eslint/strict-boolean-expressions': 'warn',
        '@typescript-eslint/prefer-nullish-coalescing': 'warn',

        // compatibility with prettier
        '@typescript-eslint/space-before-function-paren': [
          'error',
          {
            anonymous: 'always',
            named: 'never',
            asyncArrow: 'always'
          }
        ],
        '@typescript-eslint/member-delimiter-style': [
          'error',
          {
            multiline: {
              delimiter: 'none'
            },
            singleline: { delimiter: 'semi', requireLast: false }
          }
        ]
      }
    }
  ]
}
