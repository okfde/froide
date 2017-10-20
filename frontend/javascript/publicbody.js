import Vue from 'vue'

import store from './store'

import PublicbodyChooser from './components/publicbody-chooser'

Vue.config.productionTip = false

function createPublicbodyChooser (selector, config) {
  /* eslint-disable no-new */
  new Vue({
    store: store,
    data: {
      config: config
    },
    components: { PublicbodyChooser },
    el: selector
  })
}

module.exports = {
  createPublicbodyChooser
}
export default module.exports
