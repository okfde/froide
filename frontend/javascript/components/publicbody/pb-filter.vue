<template>
  <div class="filter-component">
    <h5 @click="toggleExpand" class="filter-heading">
      {{ config.label }}&nbsp;<i class="fa expand-icon" :class="{'fa-chevron-down': !expanded, 'fa-chevron-up': expanded}"></i>
    </h5>
    <transition name="expand">
      <div v-show="expanded" class="filter-container">
        <input v-if="hasSearch" type="search" class="form-control form-control-sm" :placeholder="i18n.searchPlaceholder" v-model="search" @keyup="triggerSearch" @keydown.enter.prevent="triggerSearch">
        <div class="filter-list-container">
          <pb-filter-list :config="config" :i18n="i18n" :scope="scope" :has-more="hasMore" :items="orderedItems" :value="value"
          @removeFilter="removeFilter" @setFilter="setFilter" @loadMore="loadMore" @loadChildren="loadChildren"></pb-filter-list>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
import Vue from 'vue'
import {mapGetters} from 'vuex'
import debounce from 'lodash.debounce'

import {FroideAPI} from '../../lib/api'
import FilterMixin from './lib/filter-mixin'

import PbFilterList from './pb-filter-list'

export default {
  name: 'pb-filter',
  props: ['globalConfig', 'config', 'i18n', 'scope', 'value', 'expanded'],
  mixins: [FilterMixin],
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
            x.count = facetMap[x.id]
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
      let searcher = new FroideAPI(this.globalConfig)
      return searcher
    },
    ...mapGetters(['getScopedSearchFacets'])
  },
  methods: {
    toggleExpand () {
      this.$emit('setFilterExpand', this.config, !this.expanded)
    },
    removeCurrentFilter (e) {
      e.preventDefault()
      this.removeFilter(this.value)
    },
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
    setFilter (item) {
      if (this.config.multi) {
        if (!this.value) {
          var val = [item]
        } else if (!this.value.some((x) => item.id === x.id)) {
          val = [...this.value, item]
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

<style lang="scss" scoped>
  @import "../../../styles/variables";
  .filter-heading {
    font-size: 0.9em;
    cursor: pointer;
  }
  .expand-icon {
    cursor: pointer;
    font-size: 0.8em;
  }

  .expand-enter-active, .expand-leave-active {
    transition: opacity .5s;
  }
  .expand-enter, .expand-leave-to {
    opacity: 0;
    .filter-list-container {
      max-height: 0;
    }
  }

  @include media-breakpoint-only(sm) {
    .filter-heading {
      cursor: default;
      pointer-events: none;
    }
    .expand-icon {
      display: none;
    }
    .filter-container {
      display: block !important;
    }
  }

  .filter-list-container {
    transition: max-height 0.5s ease-in-out;
    padding: 5px;
    max-height: 200px;
    overflow-y: auto;
    position: relative;

    @include media-breakpoint-up(md) {
      max-height: 320px;
    }
  }
  .filter-container:after {
    content:' ';
    pointer-events: none;
    position: absolute;
    left: 0;
    height: 3em;
    bottom: 0em;
    width: 100%;
    background:linear-gradient(
      to bottom,
      rgba(255,255,255, 0),
      rgba(255,255,255,0.95) 50%
    );
    z-index:1;
  }
</style>
