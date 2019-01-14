import Vue from 'vue'

import store from './store'

import {renderComponent} from './lib/vue-helper'

import RequestPage from './components/makerequest/request-page'

Vue.config.productionTip = false

function createRequestPage (selector) {
  /* eslint-disable no-new */
  new Vue({
    store: store,
    components: { RequestPage },
    render: renderComponent(selector, RequestPage)
  }).$mount(selector)
}

document.addEventListener('DOMContentLoaded', function () {
  createRequestPage('#make-request')
})

export default {
  createRequestPage
}
