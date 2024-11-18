import { createAppWithProps } from './lib/vue-helper'

import { createPinia } from 'pinia'

import AttachmentManager from './components/docupload/attachment-manager.vue'
console.log('### am.js 1')

document.addEventListener('DOMContentLoaded', function () {
  console.log('### am.js 2')
  const el = document.getElementById('attachment-manager')
  const app = createAppWithProps(el, AttachmentManager)
  const pinia = createPinia()
  console.log('### use am.js')
  app.use(pinia)
  app.mount(el)
})
