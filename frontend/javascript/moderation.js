import Vue from 'vue'

import { renderComponent } from './lib/vue-helper'

import ModerationDashboard from './components/moderation/moderation-dashboard'

Vue.config.productionTip = false

function createModerationDashboard(selector) {
  console.log('createModerationDashboard')
  /* eslint-disable no-new */
  new Vue({
    components: { ModerationDashboard },
    render: renderComponent(selector, ModerationDashboard)
  }).$mount(selector)
}

console.log('!createModerationDashboard')
createModerationDashboard('#moderation-dashboard')

const exp = {
  createModerationDashboard
}

export default exp
