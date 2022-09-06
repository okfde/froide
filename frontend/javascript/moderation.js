import { createAppWithProps } from './lib/vue-helper'

import ModerationDashboard from './components/moderation/moderation-dashboard'

function createModerationDashboard(selector) {
  createAppWithProps(selector, ModerationDashboard).mount(selector)
}

createModerationDashboard('#moderation-dashboard')

const exp = {
  createModerationDashboard
}

export default exp
