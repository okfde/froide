import Vue from 'vue'

import store from './store'
import {SET_CONFIG} from './store/mutation_types'

import {renderComponent} from './lib/vue-helper'

import PublicbodyChooser from './components/publicbody/publicbody-chooser'

Vue.config.productionTip = false

function createPublicbodyChooser (element) {
  /* eslint-disable no-new */
  store.commit(SET_CONFIG)
  new Vue({
    store: store,
    components: { PublicbodyChooser },
    render: renderComponent(element, PublicbodyChooser)
  }).$mount(element)
}

var els = document.querySelectorAll('.publicbody-chooser')
for (let i = 0; i < els.length; i += 1) {
  createPublicbodyChooser(els[i])
}
