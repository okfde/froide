import Vue from 'vue'

import Redaction from './components/redaction'

Vue.config.productionTip = false

function createRedaction (selector, pdfPath, config) {
  /* eslint-disable no-new */
  new Vue({
    data: {
      config: config,
      pdfPath: pdfPath
    },
    components: { Redaction },
    el: selector
  })
}

module.exports = {
  createRedaction
}
export default module.exports
