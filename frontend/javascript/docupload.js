import { createAppWithProps } from './lib/vue-helper'

import DocumentUploader from './components/docupload/document-uploader.vue'

function createDocumentUploader(element) {
  createAppWithProps(element, DocumentUploader).mount(element)
}

const els = document.querySelectorAll('.document-uploader')
for (let i = 0; i < els.length; i += 1) {
  createDocumentUploader(els[i])
}

document.addEventListener('DOMContentLoaded', function () {
  const docUploader = document.querySelector('#document-uploader')
  if (docUploader) {
    createDocumentUploader(docUploader)
  }
})
