import { createAppWithProps } from './lib/vue-helper'

import store from './store'

import PostUpload from './components/postupload/post-upload.vue'

function createPostUpload(element) {
  createAppWithProps(element, PostUpload).use(store).mount(element)
}

const els = document.querySelectorAll('.post-upload')
for (let i = 0; i < els.length; i += 1) {
  createPostUpload(els[i])
}
