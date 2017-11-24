import Vue from 'vue'

import store from './store'

import {SET_CONFIG} from './store/mutation_types'
import RequestForm from './components/request-form'

Vue.config.productionTip = false

function createRequestForm (selector, config) {
  /* eslint-disable no-new */
  store.commit(SET_CONFIG, config)
  new Vue({
    store: store,
    data: {
      config: config
    },
    components: { RequestForm },
    el: selector
  })
}

module.exports = {
  createRequestForm
}
export default module.exports
