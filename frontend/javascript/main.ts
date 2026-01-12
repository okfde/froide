import '../styles/main.scss'

// TODO: refactor global imports to ESM, like with search
import './snippets/bootstrap.ts'
import './snippets/copy-text'
import './snippets/form-ajax.ts'
import './snippets/inline-edit-forms.ts'
import './snippets/misc.ts'
import './snippets/share-links.ts'
import './snippets/color-mode.ts'
import { initSearch } from './snippets/search.ts'

document.addEventListener('DOMContentLoaded', () => {
  initSearch()
})
