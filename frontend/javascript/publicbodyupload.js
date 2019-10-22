import Vue from 'vue'

import store from './store'
import {SET_CONFIG} from './store/mutation_types'

import {renderComponent} from './lib/vue-helper'

import PublicbodyUpload from './components/publicbodyupload/publicbody-upload.vue'

Vue.config.productionTip = false

function createPublicbodyUpload (element) {
  /* eslint-disable no-new */
  store.commit(SET_CONFIG)
  new Vue({
    store: store,
    components: { PublicbodyUpload },
    render: renderComponent(element, PublicbodyUpload)
  }).$mount(element)
}

var els = document.querySelectorAll('.publicbody-upload')
for (let i = 0; i < els.length; i += 1) {
  createPublicbodyUpload(els[i])
}
