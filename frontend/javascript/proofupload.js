import { vuepo } from 'vuepo:client'
import { createGettext } from 'vuepo/vue'
import ProofUpload from './components/proofupload/proof-upload'
import { createAppWithProps } from './lib/vue-helper'

const gettext = createGettext(vuepo)

function createProofUploadWidget(element) {
  createAppWithProps(element, ProofUpload).use(gettext).mount(element)
}

const els = document.querySelectorAll('[data-proofupload]')
for (let i = 0; i < els.length; i += 1) {
  createProofUploadWidget(els[i])
}
