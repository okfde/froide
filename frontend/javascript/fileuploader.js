import Vue from 'vue'

import store from './store'
import { SET_CONFIG } from './store/mutation_types'

import { renderComponent } from './lib/vue-helper'

import FileUploader from './components/upload/file-uploader.vue'

Vue.config.productionTip = false

function createFileUploader(element) {
  /* eslint-disable no-new */
  store.commit(SET_CONFIG)
  new Vue({
    store: store,
    components: { FileUploader },
    render: renderComponent(element, FileUploader)
  }).$mount(element)
}

const els = document.querySelectorAll('.file-uploader')
for (let i = 0; i < els.length; i += 1) {
  createFileUploader(els[i])
}
