import ProofUpload from './components/proofupload/proof-upload'
import { createAppWithProps } from './lib/vue-helper'

function createProofUploadWidget(element) {
  createAppWithProps(element, ProofUpload).mount(element)
}

const els = document.querySelectorAll('[data-proofupload]')
for (let i = 0; i < els.length; i += 1) {
  createProofUploadWidget(els[i])
}
