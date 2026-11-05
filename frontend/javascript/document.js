// TODO rename this file

import { vuepo } from 'vuepo:client'
import { createGettext } from 'vuepo/vue'
import { createAppWithProps } from './lib/vue-helper'

import FileUploader from './components/upload/file-uploader.vue'

const gettext = createGettext(vuepo)

function createFileUploader(element) {
  createAppWithProps(element, FileUploader).use(gettext).mount(element)
}

const els = document.querySelectorAll('.document-upload')
for (let i = 0; i < els.length; i += 1) {
  createFileUploader(els[i])
}

document.addEventListener('DOMContentLoaded', function () {
  const docUploader = document.querySelector('#document-upload')
  if (docUploader) {
    createFileUploader(docUploader)
  }
})
