import { createAppWithProps } from './lib/vue-helper'
import store from './store'
import PostUpload from './components/postupload/post-upload.vue'

document
  .querySelectorAll('post-upload')
  .forEach((element) =>
    createAppWithProps(element, PostUpload).use(store).mount(element)
  )
