import { createAppWithProps } from './lib/vue-helper'

import store from './store'

import PostUploadSimple from './components/postupload/post-upload-simple.vue'
import PostUpload from './components/postupload/post-upload.vue'

// FIXME WIP expand into a proper beta mode
const wip = 2 // 0 = legacy Django; 1 = simplistic vueified proof of concept, 2 = vueified, new
// 0 doesn't really work any more because of the message_id redirect

function createPostUpload(element) {
  const component = wip === 2 ? PostUpload : PostUploadSimple
  createAppWithProps(element, component).use(store).mount(element)
}

if (wip > 0) {
  const els = document.querySelectorAll('.post-upload')
  for (let i = 0; i < els.length; i += 1) {
    createPostUpload(els[i])
  }
}
