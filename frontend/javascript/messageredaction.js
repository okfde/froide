import { vuepo } from 'vuepo:client'
import { createGettext } from 'vuepo/vue'
import { createAppWithProps } from './lib/vue-helper'

import MessageRedaction from './components/messageredaction/message-redaction.vue'
import DescriptionRedaction from './components/messageredaction/description-redaction.vue'

const gettext = createGettext(vuepo)

function createMessageRedaction(selector) {
  createAppWithProps(selector, MessageRedaction).use(gettext).mount(selector)
}

function createDescriptionRedaction(selector) {
  createAppWithProps(selector, DescriptionRedaction)
    .use(gettext)
    .mount(selector)
}

document.querySelectorAll('[data-redact="message"]').forEach((el) => {
  el.addEventListener('show.bs.modal', () => {
    const redaction = el.querySelector('message-redaction')
    if (redaction !== null) {
      createMessageRedaction(redaction)
    }
  })
})

document.querySelectorAll('[data-redact="description"]').forEach((el) => {
  el.addEventListener('show.bs.modal', () => {
    const redaction = el.querySelector('description-redaction')
    if (redaction !== null) {
      createDescriptionRedaction(redaction)
    }
  })
})

const exp = {
  createMessageRedaction
}

export default exp
