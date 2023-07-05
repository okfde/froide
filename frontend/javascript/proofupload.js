import Vue from 'vue'

import { renderComponent } from './lib/vue-helper'

import ProofUpload from './components/proofupload/proof-upload'

Vue.config.productionTip = false

function createProofUploadWidget(element) {
  /* eslint-disable no-new */
  new Vue({
    components: { ProofUpload },
    render: renderComponent(element, ProofUpload)
  }).$mount(element)
}

const els = document.querySelectorAll('[data-proofupload]')
for (let i = 0; i < els.length; i += 1) {
  createProofUploadWidget(els[i])
}
