import { vuepo } from 'vuepo:client'
import { createGettext } from 'vuepo/vue'
import { createAppWithProps } from './lib/vue-helper'

import ModerationDashboard from './components/moderation/moderation-dashboard'

const gettext = createGettext(vuepo)

function createModerationDashboard(selector) {
  createAppWithProps(selector, ModerationDashboard)
    .use(gettext)
    .mount(selector)
}

createModerationDashboard('#moderation-dashboard')

const exp = {
  createModerationDashboard
}

export default exp
