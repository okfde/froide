import store from './store'
import { SET_CONFIG } from './store/mutation_types'

import { createAppWithProps } from './lib/vue-helper'

import PublicbodyChooser from './components/publicbody/publicbody-chooser'

function createPublicbodyChooser(element) {
  store.commit(SET_CONFIG)
  createAppWithProps(element, PublicbodyChooser).use(store).mount(element)
}

const els = document.querySelectorAll('.publicbody-chooser')
for (let i = 0; i < els.length; i += 1) {
  createPublicbodyChooser(els[i])
}
