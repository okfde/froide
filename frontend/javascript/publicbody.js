import store from './store'
import { SET_CONFIG } from './store/mutation_types'

import { vuepo } from 'vuepo:client'
import { createGettext } from 'vuepo/vue'
import { createAppWithProps } from './lib/vue-helper'

import PublicbodyChooser from './components/publicbody/publicbody-chooser'

const gettext = createGettext(vuepo)

function createPublicbodyChooser(element) {
  store.commit(SET_CONFIG)
  createAppWithProps(element, PublicbodyChooser)
    .use(gettext)
    .use(store)
    .mount(element)
}

const els = document.querySelectorAll('.publicbody-chooser')
for (let i = 0; i < els.length; i += 1) {
  createPublicbodyChooser(els[i])
}
