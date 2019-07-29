import Vue from 'vue'

import {renderComponent} from './lib/vue-helper'

import MessageRedaction from './components/messageredaction/messageredaction.vue'

Vue.config.productionTip = false

function createMessageRedaction (selector) {
  /* eslint-disable no-new */
  new Vue({
    components: { MessageRedaction },
    render: renderComponent(selector, MessageRedaction)
  }).$mount(selector)
}

Array.from(document.querySelectorAll('[data-redact="message"]')).forEach((el) => {
  el.addEventListener('show.bs.modal', () => {
    const redaction = el.querySelector('message-redaction')
    if (redaction !== null) {
      createMessageRedaction(redaction)
    }
  })
})

const exp = {
  createMessageRedaction
}

export default exp
