// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
import Vue from 'vue'

import store from './store'

import RequestForm from './components/request-form'

Vue.config.productionTip = false

function createRequestForm (selector, config) {
  /* eslint-disable no-new */
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
