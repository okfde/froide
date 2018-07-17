import Vue from 'vue'

import store from './store'

import RequestForm from './components/request-form'

Vue.config.productionTip = false

function createRequestForm (selector) {
  /* eslint-disable no-new */
  new Vue({
    store: store,
    components: { RequestForm },
    el: selector
  })
}

document.addEventListener('DOMContentLoaded', function () {
  createRequestForm('#make-request')
})

const exp = {
  createRequestForm
}
module.exports = exp
export default exp
