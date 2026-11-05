import { vuepo } from 'vuepo:client'
import { createGettext } from 'vuepo/vue'
import { createAppWithProps } from './lib/vue-helper'

import GeoMatcher from './components/geomatch/geo-matcher.vue'

const gettext = createGettext(vuepo)

function createGeoMatcher(element) {
  createAppWithProps(element, GeoMatcher).use(gettext).mount(element)
}

document.addEventListener('DOMContentLoaded', function () {
  const el = document.querySelector('#geomatch-component')
  if (el) {
    createGeoMatcher(el)
  }
})
