import { vuepo } from 'vuepo:client'
import { createGettext } from 'vuepo/vue'
import { createAppWithProps } from './lib/vue-helper'

import PdfRedaction from './components/redaction/pdf-redaction'

const gettext = createGettext(vuepo)

function createRedaction(selector) {
  const app = createAppWithProps(selector, PdfRedaction)
  app.use(gettext)
  app.mount(selector)
}

document.addEventListener('DOMContentLoaded', function () {
  createRedaction('#redact')
})

const exp = {
  createRedaction
}

export default exp
