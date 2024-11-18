import { createAppWithProps } from './lib/vue-helper'

import { pinia } from './lib/pinia'

import AttachmentManager from './components/docupload/attachment-manager.vue'
console.log('### am.js 1')

// const pinia = createPinia()

document.addEventListener('DOMContentLoaded', function () {
  console.log('### am.js 2')
  const el = document.getElementById('attachment-manager')
  const app = createAppWithProps(el, AttachmentManager)
  console.log('### use am.js 3')
  app.use(pinia)
  console.log('### use am.js 4')
  app.mount(el)
})
