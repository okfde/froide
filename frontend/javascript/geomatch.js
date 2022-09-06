import { createAppWithProps } from './lib/vue-helper'

import GeoMatcher from './components/geomatch/geo-matcher.vue'

function createGeoMatcher(element) {
  createAppWithProps(element, GeoMatcher).mount(element)
}

document.addEventListener('DOMContentLoaded', function () {
  const el = document.querySelector('#geomatch-component')
  if (el) {
    createGeoMatcher(el)
  }
})
