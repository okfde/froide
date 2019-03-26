<template>
  <div class="geo-matcher mb-3 mt-3">
    <dl>
      <dd>Region Kind</dd>
      <dt><input v-model="regionKind"/></dt>
      <dd>Ancestor GeoRegion</dd>
      <dt>
        <input v-model="ancestor" @change="ancestorChanged"/>
        {{ ancestorName }}
      </dt>
      <dd>Public Body Category</dd>
      <dt>
        <input v-model="category" @change="categoryChanged"/>
        {{ categoryName }}
      </dt>
      <dd>Jurisdiction</dd>
      <dt>
        <input v-model="jurisdiction" @change="jurisdictionChanged"/>
        {{ jurisdictionName }}
      </dt>
      <dd>Public Body Search Hint</dd>
      <dt><input v-model="searchHint"/></dt>
    </dl>
    <button @click="load">Load</button>
    <p>
      Regions: {{ regionCount }}<br />
      Unlinked Regions: {{ unlinkedRegionCount }}<br />
      Unmatched Regions: {{ unmatchedRegionCount }}
    </p>
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Type</th>
          <th>Public Body</th>
          <th>Search matches</th>
        </tr>
      </thead>
      <tbody>
        <geo-matcher-row v-for="georegion in georegions"
          :key="georegion.id"
          :georegion="georegion"
          @connectpublicbody="connectPublicBody"
        >
        </geo-matcher-row>
      </tbody>
    </table>
  </div>
</template>

<script>

import Vue from 'vue'

import {getAllData, FroideAPI, getData, postData} from '../../lib/api.js'

import GeoMatcherRow from './geo-matcher-row.vue'

function getQueryVariable(variable) {
  var query = window.location.search.substring(1);
  var vars = query.split('&');
  for (var i = 0; i < vars.length; i++) {
    var pair = vars[i].split('=');
    if (decodeURIComponent(pair[0]) == variable) {
      return decodeURIComponent(pair[1]);
    }
  }
}

export default {
  name: 'geo-matcher',
  props: ['config'],
  components: {
    GeoMatcherRow
  },
  data () {
    return {
      georegions: [],
      regionKind: '',
      ancestor: '',
      ancestorName: '',
      jurisdiction: '',
      jurisdictionName: '',
      category: '',
      categoryName: '',
      searchHint: '',
    }
  },
  mounted () {
    this.$root.config = this.config
    this.$root.csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value
    this.ancestor = getQueryVariable('ancestor') || ''
    this.regionKind = getQueryVariable('kind') || ''
    this.category = getQueryVariable('category') || ''
    this.jurisdiction = getQueryVariable('jurisdiction') || ''
    this.searchHint = getQueryVariable('searchhint') || ''

    this.loadCategoryName()
    this.loadAncestorName()
    this.loadJurisdictionName()
  },
  computed: {
    regionCount () {
      return this.georegions.length
    },
    unlinkedRegion () {
      return this.georegions.filter((gr) => !gr.links || !gr.links.length)
    },
    unlinkedRegionCount () {
      return this.unlinkedRegion.length
    },
    unmatchedRegion () {
      return this.unlinkedRegion.filter((gr) => !gr.matches || !gr.matches.length)
    },
    unmatchedRegionCount () {
      return this.unmatchedRegion.length
    },
    georegionMapping () {
      let mapping = {}
      this.georegions.forEach((gr, i) => {
        mapping[gr.resource_uri] = i
      })
      return mapping
    }
  },
  methods: {
    load () {
      this.loadGeoRegions()
    },
    categoryChanged () {
      this.loadCategoryName()
    },
    ancestorChanged () {
      this.loadAncestorName()
    },
    jurisdictionChanged () {
      this.loadJurisdictionName()
    },
    loadCategoryName () {
      if (!this.category) {
        return
      }
      getData(`${this.config.url.listCategories}${this.category}/`).then((data) => {
        this.categoryName = data.name
      })
    },
    loadAncestorName () {
      if (!this.ancestor) {
        return
      }
      getData(`${this.config.url.listGeoregion}${this.ancestor}/`).then((data) => {
        this.ancestorName = `${data.name} (${data.kind} - ${data.kind_detail})` 
      })
    },
    loadJurisdictionName () {
      if (!this.jurisdiction) {
        return
      }
      const url = this.config.url.detailJurisdiction.replace(/0/, this.jurisdiction)
      getData(url).then((data) => {
        this.jurisdictionName = data.name 
      })
    },
    loadGeoRegions () {
      let apiUrl = `${this.config.url.listGeoregion}?kind=${this.regionKind}`
      if (this.ancestor) {
        apiUrl += `&ancestor=${this.ancestor}`
      }
      getAllData(apiUrl).then((data) => {
        this.georegions = data
        this.loadLinks().then(() => {
          this.searchPublicBodies()
        })
      })
    },
    loadLinks () {
      const MAX_ITEMS = 40
      const regions = this.georegions.map((gr) => gr.id)
      const rounds = Math.ceil(regions.length / MAX_ITEMS)

      const promises = [...Array(rounds).keys()].map((index) => {
        let ids = regions.slice(index * MAX_ITEMS, index * MAX_ITEMS + MAX_ITEMS)
        return this.loadPublicBodyWithRegions(ids)
      })

      return Promise.all(promises)
    },
    loadPublicBodyWithRegions (ids) {
      let apiUrl = `${this.config.url.listPublicBodies}?regions=${ids.join(',')}`
      if (this.category) {
        apiUrl += `&category=${this.category}`
      }
      return getAllData(apiUrl).then((data) => {
        data.forEach((pb) => {
          pb.regions.forEach((region_uri) => {
            let gr = this.georegions[this.georegionMapping[region_uri]]
            Vue.set(gr, 'links', [
              ...(gr.links || []),
              pb
            ])
          })
        })
      })
    },
    searchPublicBodies () {
      const filter = {}
      if (this.category) {
        filter.categories = this.category
      }
      if (this.jurisdiction) {
        filter.jurisdiction = this.jurisdiction
      }
      const api = new FroideAPI(this.config)
      this.georegions.forEach((gr) => {
        if (gr.links === undefined || gr.links.length === 0) {
          Vue.set(gr, 'loading', true)
          let term = gr.name
          if (this.searchHint) {
            term = `${this.searchHint} ${term}`
          }
          api.searchPublicBodies(term, filter).then((data) => {
            Vue.set(gr, 'loading', false)
            Vue.set(gr, 'matches', data.objects.results.slice(0, 5))
          })
        }
      })
    },
    connectPublicBody (payload) {
      const data = {georegion: payload.georegionId, publicbody: payload.publicbodyId}
      postData('', data, this.$root.csrfToken).then((data) => {
        let gr = this.georegions[this.georegionMapping[payload.georegionUrl]]
        Vue.set(gr, 'links', [
          ...(gr.links || []),
          payload.publicbody
        ])
        Vue.set(gr, 'matches', [])
      })
    }
  }
}
</script>