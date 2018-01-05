<template>
  <div class="mb-3">
    <h5>{{ config.label }}</h5>
    <input v-if="hasSearch" type="search" class="form-control form-control-sm" :placeholder="i18n.searchPlaceholder" v-model:value="search" @keyup="triggerSearch" @keydown.enter.prevent="triggerSearch">
    <div class="filter-list-container">
      <pb-filter-list :config="config" :i18n="i18n" :scope="scope" :has-more="hasMore" :items="orderedItems" :value="value"
      @removeFilter="removeFilter" @setFilter="setFilter" @loadMore="loadMore" @loadChildren="loadChildren"></pb-filter-list>
    </div>
  </div>
</template>

<script>
import Vue from 'vue'
import {mapGetters} from 'vuex'
import {debounce} from 'underscore'

import {FroideSearch} from '../lib/search'

import PbFilterList from './pb-filter-list'

export default {
  name: 'pb-filter',
  props: ['globalConfig', 'config', 'i18n', 'scope', 'value'],
  components: {PbFilterList},
  data () {
    return {
      items: [],
      search: '',
      lastSearch: null,
      searchMeta: null
    }
  },
  mounted () {
    this.runSearch()
  },
  computed: {
    hasSearch () {
      return this.config.hasSearch
    },
    triggerSearch () {
      return debounce(this.runSearch, 300)
    },
    facetMap () {
      let facets = this.getScopedSearchFacets(this.scope)
      if (!facets) {
        return null
      }
      let counts = facets[this.config.key]
      if (counts) {
        let facetMap = {}
        counts.forEach((x) => {
          facetMap[x[0]] = x[1]
        })
        return facetMap
      }
      return null
    },
    orderedItems () {
      let items = this.items
      if (this.facetMap) {
        let applyFacetMap = function (facetMap, items) {
          return items.map((x) => {
            x.count = facetMap[x.value]
            if (x.subItems) {
              x.subItems = applyFacetMap(facetMap, x.subItems)
            }
            return x
          })
        }
        items = applyFacetMap(this.facetMap, items)
      }
      return items
    },
    searcher () {
      let searcher = new FroideSearch(this.globalConfig)
      return searcher
    },
    hasMore () {
      if (!this.searchMeta) { return false }
      return this.searchMeta.next !== null
    },
    ...mapGetters(['getScopedSearchFacets'])
  },
  methods: {
    runSearch () {
      if (this.lastSearch === this.search) {
        return
      }
      this.lastSearch = this.search
      let filters = null
      if (this.search === '') {
        filters = this.config.initialFilters
      }
      this.getItems(this.search, filters)
    },
    getItems (q, filters) {
      this.search = q
      this.config.getItems(q, filters).then((result) => {
        this.searchMeta = result.meta
        this.items = this.processItems(result.objects)
      })
    },
    processItems (items) {
      if (this.config.itemFilter) {
        items = items.filter(this.config.itemFilter)
      }
      if (this.config.itemMap) {
        items = items.map(this.config.itemMap)
      }
      return items
    },
    loadMore () {
      if (!this.searchMeta) { return }
      if (!this.searchMeta.next) { return }
      this.searcher.getJson(this.searchMeta.next).then((result) => {
        this.searchMeta = result.meta
        this.items = [...this.items, ...this.processItems(result.objects)]
      })
    },
    loadChildren (item) {
      this.config.getItems(null, {parent: item.id}).then((result) => {
        let items = this.processItems(result.objects)
        Vue.set(item, 'subItems', items)
      })
    },
    removeFilter (itemValue) {
      if (this.config.multi) {
        let val = this.value.filter((x) => itemValue !== x)
        this.$emit('update', this.config, val)
      } else {
        this.$emit('update', this.config, null)
      }
    },
    setFilter (itemValue) {
      if (this.config.multi) {
        if (!this.value) {
          var val = [itemValue]
        } else if (!this.value.some((x) => itemValue === x)) {
          val = [...this.value, itemValue]
        }
        if (val) {
          this.$emit('update', this.config, val)
        }
      } else {
        this.$emit('update', this.config, itemValue)
      }
    }
  }
}
</script>

<style lang="scss" scoped>
  @import "../../styles/variables";

  .filter-list-container {
    max-height: 210px;
    overflow-y: auto;

    @include media-breakpoint-up(md) {
      max-height: 420px;
    }
  }
</style>
