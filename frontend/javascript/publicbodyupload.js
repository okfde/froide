import store from './store'
import { SET_CONFIG } from './store/mutation_types'

import { createAppWithProps } from './lib/vue-helper'

import PublicbodyUpload from './components/publicbodyupload/publicbody-upload.vue'

function createPublicbodyUpload(element) {
  store.commit(SET_CONFIG)
  createAppWithProps(element, PublicbodyUpload).use(store).mount(element)
}

const els = document.querySelectorAll('.publicbody-upload')
for (let i = 0; i < els.length; i += 1) {
  createPublicbodyUpload(els[i])
}
