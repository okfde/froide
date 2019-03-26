import Vue from 'vue'

import {renderComponent} from './lib/vue-helper'

import GeoMatcher from './components/geomatch/geo-matcher.vue'

Vue.config.productionTip = false

function createGeoMatcher (element) {
  /* eslint-disable no-new */
  new Vue({
    components: { GeoMatcher },
    render: renderComponent(element, GeoMatcher)
  }).$mount(element)
}

document.addEventListener('DOMContentLoaded', function () {
  var el = document.querySelector('#geomatch-component')
  if (el) {
    createGeoMatcher(el)
  }
})
