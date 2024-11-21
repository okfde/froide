import { createAppWithProps } from './lib/vue-helper'

import PdfRedaction from './components/redaction/pdf-redaction'

function createRedaction(selector) {
  const app = createAppWithProps(selector, PdfRedaction)
  app.mount(selector)
}

document.addEventListener('DOMContentLoaded', function () {
  createRedaction('#redact')
})

const exp = {
  createRedaction
}

export default exp
