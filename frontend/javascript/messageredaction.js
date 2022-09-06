import { createAppWithProps } from './lib/vue-helper'

import MessageRedaction from './components/messageredaction/message-redaction.vue'

function createMessageRedaction(selector) {
  createAppWithProps(selector, MessageRedaction).mount(selector)
}

document.querySelectorAll('[data-redact="message"]').forEach((el) => {
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
