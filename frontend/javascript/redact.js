import Vue from 'vue'

import { renderComponent } from './lib/vue-helper'

import PdfRedaction from './components/redaction/pdf-redaction'

Vue.config.productionTip = false

function createRedaction(selector) {
  /* eslint-disable no-new */
  new Vue({
    components: { PdfRedaction },
    render: renderComponent(selector, PdfRedaction)
  }).$mount(selector)
}

document.addEventListener('DOMContentLoaded', function () {
  createRedaction('#redact')
})

const exp = {
  createRedaction
}

export default exp
