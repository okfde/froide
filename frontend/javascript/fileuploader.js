import { createAppWithProps } from './lib/vue-helper'
import store from './store'
import { SET_CONFIG } from './store/mutation_types'

import FileUploader from './components/upload/file-uploader.vue'

function createFileUploader(element) {
  store.commit(SET_CONFIG)
  createAppWithProps(element, FileUploader).use(store).mount(element)
}

const els = document.querySelectorAll('.file-uploader')
for (let i = 0; i < els.length; i += 1) {
  createFileUploader(els[i])
}
