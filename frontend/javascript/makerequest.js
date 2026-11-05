import { vuepo } from 'vuepo:client'
import { createGettext } from 'vuepo/vue'
import { createAppWithProps } from './lib/vue-helper'

import store from './store'

import RequestPage from './components/makerequest/request-page'

const gettext = createGettext(vuepo)

function createRequestPage(selector) {
  createAppWithProps(selector, RequestPage)
    .use(gettext)
    .use(store)
    .mount(selector)
}

document.addEventListener('DOMContentLoaded', function () {
  if (document.getElementById('make-request')) {
    createRequestPage('#make-request')
  }
})

export default {
  createRequestPage
}
