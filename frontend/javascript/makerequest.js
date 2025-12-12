import { createAppWithProps } from './lib/vue-helper'

import store from './store'

import RequestPage from './components/makerequest/request-page'

function createRequestPage(selector) {
  createAppWithProps(selector, RequestPage).use(store).mount(selector)
}

document.addEventListener('DOMContentLoaded', function () {
  if (document.getElementById('make-request')) {
    createRequestPage('#make-request')
  }
})

export default {
  createRequestPage
}