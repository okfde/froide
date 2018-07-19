import Vue from 'vue'

import store from './store'

import {renderComponent} from './lib/vue-helper'

import RequestForm from './components/request-form'

Vue.config.productionTip = false

function createRequestForm (selector) {
  /* eslint-disable no-new */
  new Vue({
    store: store,
    components: { RequestForm },
    render: renderComponent(selector, RequestForm)
  }).$mount(selector)
}

document.addEventListener('DOMContentLoaded', function () {
  createRequestForm('#make-request')
})

const exp = {
  createRequestForm
}
module.exports = exp
export default exp
