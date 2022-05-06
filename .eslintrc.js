module.exports = {
  parserOptions: {
    sourceType: 'module',
    project: ['./tsconfig.json']
  },
  extends: ['plugin:vue/essential', 'standard-with-typescript'],
  plugins: ['prettier', 'html'],
  ignorePatterns: ['node_modules/**', '**/static/**'],
  rules: {
    'prettier/prettier': 'error',
    'space-before-function-paren': [
      'error',
      {
        anonymous: 'always',
        named: 'never',
        asyncArrow: 'always'
      }
    ]
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
