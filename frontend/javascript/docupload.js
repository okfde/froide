import { vuepo } from 'vuepo:client'
import { createGettext } from 'vuepo/vue'
import { createAppWithProps } from './lib/vue-helper'

import { pinia } from './lib/pinia'

import AttachmentManager from './components/docupload/attachment-manager.vue'

const gettext = createGettext(vuepo)

document.addEventListener('DOMContentLoaded', function () {
  const el = document.getElementById('attachment-manager')
  const app = createAppWithProps(el, AttachmentManager)
  app.use(gettext)
  app.use(pinia)
  app.mount(el)
})
