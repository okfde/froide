import { vuepo } from 'vuepo:client'
import { createGettext } from 'vuepo/vue'
import { createAppWithProps } from './lib/vue-helper'
import store from './store'
import PostUpload from './components/postupload/post-upload.vue'

const gettext = createGettext(vuepo)

document
  .querySelectorAll('post-upload')
  .forEach((element) =>
    createAppWithProps(element, PostUpload)
      .use(gettext)
      .use(store)
      .mount(element)
  )
