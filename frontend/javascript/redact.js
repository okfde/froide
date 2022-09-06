import { createAppWithProps } from './lib/vue-helper'

import PdfRedaction from './components/redaction/pdf-redaction'

function createRedaction(selector) {
  createAppWithProps(selector, PdfRedaction).mount(selector)
}

document.addEventListener('DOMContentLoaded', function () {
  createRedaction('#redact')
})

const exp = {
  createRedaction
}

export default exp
