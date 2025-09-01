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
  /* else if (document.getElementById('make-request-sent')) {
    // note: this won't purge draft-specific storage
    // (scope: make-request-draft-123, see RequestPage.created)
    // but due to the nature of drafts this does not matter
    // (they're both more specific and ephemeral)
    store.dispatch('purgeStorage', { scope: 'make-request' })
  } */
})

export default {
  createRequestPage
}