import { createAppWithProps } from './lib/vue-helper'

import { pinia } from './lib/pinia'

import AttachmentManager from './components/docupload/attachment-manager.vue'

document.addEventListener('DOMContentLoaded', function () {
  const el = document.getElementById('attachment-manager')
  const app = createAppWithProps(el, AttachmentManager)
  app.use(pinia)
  app.mount(el)
})
