<template>
  <div class="dropdown my-1 my-sm-0">
    <button
      type="button"
      class="btn btn-secondary dropdown-toggle d-block w-100"
      data-bs-toggle="dropdown"
      data-bs-auto-close="outside"
      >{{ config.label }}</button>
    <div class="dropdown-menu">
      <div v-if="hasSearch" class="px-3 py-2">
        <input
          type="search"
          class="form-control form-control-sm"
          :placeholder="i18n.searchPlaceholder"
          v-model="search"
          @input="triggerSearch"
          @keydown.enter.prevent="triggerSearch"
          />
      </div>
      <div v-if="hasChoices" class="px-3 py-2">
        <select
          v-model="choice"
          @change="triggerSearch"
          class="form-select form-control-sm form-select-sm">
          <option
            :value="null"
            :selected="!choice"
            style="font-style: italic"
            ><em>{{ config.choicesNoneLabel }}</em></option>
          <option
            v-for="opt in config.choices[1]"
            :key="opt[0]"
            :value="opt[0]"
            :selected="choice == opt[0]">
            {{ opt[1] }}
          </option>
        </select>
      </div>
      <div class="overflow-y-auto p-3" style="max-height: 50vh">
        <div
          v-if="loading"
          class="spinner-border text-secondary"
          role="status">
          <span class="visually-hidden">{{ i18n.loading }}</span>
        </div>
        <PbFilterList
          v-else
          :config="config"
          :i18n="i18n"
          :scope="scope"
          :has-more="hasMore"
          :items="orderedItems"
          :value="value"
          @remove-filter="removeFilter"
          @set-filter="setFilter"
          @load-more="loadMore"
          @load-children="loadChildren"></PbFilterList>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'
import debounce from 'lodash.debounce'

import { FroideAPI } from '../../lib/api'
import FilterMixin from './lib/filter-mixin'

import PbFilterList from './pb-filter-list'

export default {
  name: 'PbFilter',
  props: ['globalConfig', 'config', 'i18n', 'scope', 'value', 'expanded'],
  mixins: [FilterMixin],
  components: { PbFilterList },
  data() {
    let choice = null
    if (this.config.choices && !this.config.choicesNoneLabel) {
      choice = this.config.choices[1][0][0]
    }
    return {
      items: [],
      search: '',
      choice,
      lastSearch: null,
      searchMeta: null,
      loading: false
    }
  },
  mounted() {
    this.runSearch()
  },
  computed: {
    hasSearch() {
      return this.config.hasSearch
    },
    hasChoices() {
      return this.config.choices
    },
    triggerSearch() {
      return debounce(this.runSearch, 300)
    },
    facetMap() {
      const facets = this.getScopedSearchFacets(this.scope)
      if (!facets) {
        return null
      }
      const counts = facets[this.config.key]
      if (counts) {
        const facetMap = {}
        counts.forEach((x) => {
          facetMap[x[0]] = x[1]
        })
        return facetMap
      }
      return null
    },
    orderedItems() {
      let items = this.items
      if (this.facetMap) {
        const applyFacetMap = function (facetMap, items) {
          return items.map((x) => {
            x.count = facetMap[x.id]
            if (x.subItems) {
              x.subItems = applyFacetMap(facetMap, x.subItems)
            }
            return x
          })
        }
        items = applyFacetMap(this.facetMap, items)
      }
      if (this.choice) {
        items.forEach((x) => x.subLabel = false)
      }
      return items
    },
    searcher() {
      const searcher = new FroideAPI(this.globalConfig)
      return searcher
    },
    ...mapGetters(['getScopedSearchFacets'])
  },
  methods: {
    toggleExpand() {
      this.$emit('setFilterExpand', this.config, !this.expanded)
    },
    removeCurrentFilter(e) {
      e.preventDefault()
      this.removeFilter(this.value)
    },
    runSearch() {
      let filters = {}
      if (this.search === '') {
        filters = {
          ...filters,
          ...this.config.initialFilters
        }
      }
      if (this.config.choices) {
        filters[this.config.choices[0]] = this.choice === null
          // if no choice set, filter by "or all"
          ? this.config.choices[1].map((c) => c[0]).join(',')
          : this.choice
      }
      const searchDump = JSON.stringify({
        q: this.search,
        ...filters
      })
      if (this.lastSearch === searchDump) {
        return
      }
      this.items = []
      this.lastSearch = searchDump
      this.loading = true
      this.getItems(this.search, filters)
    },
    getItems(q, filters) {
      this.search = q
      this.config.getItems(q, filters).then((result) => {
        this.searchMeta = result.meta
        this.loading = false
        this.items = this.processItems(result.objects)
      })
    },
    processItems(items) {
      if (this.config.itemFilter) {
        items = items.filter(this.config.itemFilter)
      }
      if (this.config.itemMap) {
        items = items.map(this.config.itemMap)
      }
      return items
    },
    loadMore() {
      if (!this.searchMeta) {
        return
      }
      if (!this.searchMeta.next) {
        return
      }
      this.searcher.getJson(this.searchMeta.next).then((result) => {
        this.searchMeta = result.meta
        this.items = [...this.items, ...this.processItems(result.objects)]
      })
    },
    loadChildren(item) {
      this.config.getItems(null, { parent: item.id }).then((result) => {
        const items = this.processItems(result.objects)
        item.subItems = items
      })
    },
    setFilter(item) {
      if (this.config.multi) {
        if (!Array.isArray(item)) item = [item]
        let val
        if (!this.value) {
          val = item
        } else {
          val = [...this.value]
          item.forEach((i) => {
            if (!this.value.some((x) => i.id === x.id)) {
              val.push(i)
            }
          })
        }
        if (val) {
          this.$emit('update', this.config, val)
        }
      } else {
        this.$emit('update', this.config, item)
      }
    }
  }
}
</script>
