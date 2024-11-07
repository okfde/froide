import { createAppWithProps } from './lib/vue-helper'
import { vBsTooltip } from './lib/vue-bootstrap'

import PdfRedaction from './components/redaction/pdf-redaction'

function createRedaction(selector) {
  const app = createAppWithProps(selector, PdfRedaction)
  app.directive('bsTooltip', vBsTooltip)
  app.mount(selector)
}

document.addEventListener('DOMContentLoaded', function () {
  createRedaction('#redact')
})

const exp = {
  createRedaction
}

export default exp
