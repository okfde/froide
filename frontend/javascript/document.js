import Vue from 'vue'

import {renderComponent} from './lib/vue-helper'

import FileUploader from './components/upload/file-uploader.vue'

Vue.config.productionTip = false

function createDocumentUploader (element) {
  /* eslint-disable no-new */
  new Vue({
    components: { FileUploader },
    render: renderComponent(element, FileUploader)
  }).$mount(element)
}

var els = document.querySelectorAll('.document-upload')
for (let i = 0; i < els.length; i += 1) {
  createDocumentUploader(els[i])
}

document.addEventListener('DOMContentLoaded', function () {
  let docUploader = document.querySelector('#document-upload')
  if (docUploader) {
    createDocumentUploader(docUploader)
  }
})
