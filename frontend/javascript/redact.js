import Vue from 'vue'

import {renderComponent} from './lib/vue-helper'

import Redaction from './components/redaction/redaction'

Vue.config.productionTip = false

function createRedaction (selector) {
  /* eslint-disable no-new */
  new Vue({
    components: { Redaction },
    render: renderComponent(selector, Redaction)
  }).$mount(selector)
}

document.addEventListener('DOMContentLoaded', function () {
  createRedaction('#redact')
})

const exp = {
  createRedaction
}

module.exports = exp
export default exp
