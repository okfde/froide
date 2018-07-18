import Vue from 'vue'

import Redaction from './components/redaction'

Vue.config.productionTip = false

function createRedaction (selector) {
  /* eslint-disable no-new */
  new Vue({
    components: { Redaction },
    el: selector
  })
}

document.addEventListener('DOMContentLoaded', function () {
  createRedaction('#redact')
})

const exp = {
  createRedaction
}

module.exports = exp
export default exp
