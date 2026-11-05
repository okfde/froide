import store from './store'
import { SET_CONFIG } from './store/mutation_types'

import { vuepo } from 'vuepo:client'
import { createGettext } from 'vuepo/vue'
import { createAppWithProps } from './lib/vue-helper'

import PublicbodyUpload from './components/publicbodyupload/publicbody-upload.vue'

const gettext = createGettext(vuepo)

function createPublicbodyUpload(element) {
  store.commit(SET_CONFIG)
  createAppWithProps(element, PublicbodyUpload)
    .use(gettext)
    .use(store)
    .mount(element)
}

const els = document.querySelectorAll('.publicbody-upload')
for (let i = 0; i < els.length; i += 1) {
  createPublicbodyUpload(els[i])
}
