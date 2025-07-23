import { createAppWithProps } from './lib/vue-helper'
import store from './store'
import MessageEditFlow from './components/editmessageflow/edit-message-flow.vue'

document
  .querySelectorAll('edit-message-flow')
  .forEach((element) =>
    createAppWithProps(element, MessageEditFlow).use(store).mount(element)
  )
