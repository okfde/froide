import Vue from 'vue'

import store from './store'
import {SET_CONFIG} from './store/mutation_types'

import PublicbodyChooser from './components/publicbody-chooser'

Vue.config.productionTip = false

function createPublicbodyChooser (selector, config) {
  /* eslint-disable no-new */
  store.commit(SET_CONFIG, config)
  new Vue({
    store: store,
    data: {
      config: config
    },
    components: { PublicbodyChooser },
    el: selector
  })
}

module.exports = {
  createPublicbodyChooser
}
export default module.exports
