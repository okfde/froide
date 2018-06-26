<template>
  <div class="publicbody-chooser mb-3">
    <div v-if="blockUI" class="mt-5 text-center">
      <h4>
        {{ blockMessage }}
      </h4>
      <div class="progress">
        <div class="progress-bar" :style="blockProgressWidth" role="progressbar" :aria-valuenow="blockProgress" aria-valuemin="0" aria-valuemax="100"></div>
      </div>
    </div>
    <template v-else>
      <div class="row">
        <div class="form-search col-md-8 mt-3">
          <label for="publicbody-multi-search-input">Suchen Sie nach Behörden</label>
          <div class="input-group">
            <input id="publicbody-multi-search-input" type="search" v-model="search" class="search-public_bodies form-control form-control-lg" :placeholder="i18n.publicBodySearchPlaceholder" @keyup="triggerAutocomplete" @keydown.enter.prevent="triggerAutocomplete"/>
            <div class="input-group-append">
              <button type="button" class="btn btn-primary search-public_bodies-submit" @click="triggerAutocomplete">
                <i class="fa fa-search"></i>
                {{ i18n.search }}
              </button>
            </div>
          </div>
        </div>
      </div>
      <div class="row mb-4 mt-5">
        <div class="col-auto">
          <h3 v-show="!searching">
            {{ i18n._('publicBodiesFound', {count: searchResultsLength} ) }}
          </h3>
          <img v-show="searching" class="col-auto" :src="config.resources.spinner" alt="Loading..."/>
        </div>
        <div class="col-auto">
          <button @click.prevent="selectAll" class="btn btn-sm btn-light" :disabled="selectAllButtonDisabled">
            {{ i18n._('selectAll', { count: searchResultsLength} ) }}
          </button>
        </div>
        <div class="col-auto ml-auto">
          <button :disabled="!hasSearchResults" @click.prevent="clearSearch" class="btn-sm btn btn-light">
            {{ i18n.clearSearchResults }}
          </button>
        </div>
      </div>
      <div class="row">
        <div class="col-md-8 col-lg-9 order-2">
          <pb-table :name="name" :scope="scope" :i18n="i18n" :headers="currentHeaders"
                    :options="selectOptions" :rows="searchResults" @selectAllRows="selectAllRows"></pb-table>
          <pb-pagination :scope="scope" :i18n="i18n"></pb-pagination>
        </div>
        <div class="col-md-4  col-lg-3 order-md-1">
          <pb-filter-selected
            v-for="filterKey in filterOrder" :key="filterKey"
            :config="filterConfig[filterKey]"
            @update="updateFilter"
            :value="filters[filterKey]">
          </pb-filter-selected>
          <div class="row mt-3">
            <div v-for="filterKey in filterOrder" :key="filterKey" class="col-sm-4 col-md-12 filter-column">
              <pb-filter :global-config="config" :expanded="filterExpanded[filterKey]" :config="filterConfig[filterKey]" :i18n="i18n" :scope="scope" @update="updateFilter" @setFilterExpand="setFilterExpand" :value="filters[filterKey]"></pb-filter>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import Vue from 'vue'

import {mapGetters, mapMutations, mapActions} from 'vuex'
import {
  SET_STEP_REQUEST, ADD_PUBLICBODY_ID, REMOVE_PUBLICBODY_ID,
  CLEAR_PUBLICBODIES
} from '../store/mutation_types'

import {FroideSearch} from '../lib/search'
import PBChooserMixin from '../lib/pb-chooser-mixin'
import I18nMixin from '../lib/i18n-mixin'
import PBListMixin from '../lib/pb-list-mixin'

import PbTable from './pb-table'
import PbPagination from './pb-pagination'
import PbSummary from './pb-summary'
import PbFilter from './pb-filter'
import PbFilterSelected from './pb-filter-selected'

import 'string.prototype.repeat'

const MAX_PUBLICBODIES = 800

function treeLabel (item) {
  return '-'.repeat(item.depth - 1) + ' ' + item.name
}

export default {
  name: 'publicbody-multi-chooser',
  mixins: [PBChooserMixin, PBListMixin, I18nMixin],
  props: ['name', 'scope', 'defaultsearch', 'formJson', 'config'],
  components: {
    PbTable,
    PbPagination,
    PbSummary,
    PbFilter,
    PbFilterSelected
  },
  allowEmptySearch: true,
  mounted () {
    if (!this.hasSearchResults) {
      this.triggerAutocomplete()
    }
  },
  data () {
    return {
      search: '',
      blockUI: false,
      blockMessage: null,
      blockProgress: 0,
      lastQuery: null,
      searching: false,
      selectOptions: {
        selectAllCheckbox: true
      },
      filters: {
        classification: null,
        jurisdiction: null,
        categories: []
      },
      filterExpanded: {
        classification: true
      },
      filterOrder: ['classification', 'jurisdiction', 'categories']
    }
  },
  computed: {
    getListView () {
      if (!this.listView) {
        return 'resultList'
      }
      return this.listView
    },
    filterConfig () {
      let searcher = new FroideSearch(this.config)
      return {
        classification: {
          label: this.i18n.classificationPlural[1],
          key: 'classification',
          expanded: this.filterExpanded.classification,
          initialFilters: { depth: 1 },
          getItems: (q, filters) => searcher.listClassifications(q, filters),
          hasSearch: true,
          itemMap: (item) => {
            return {
              label: treeLabel(item),
              value: item.name,
              id: item.id,
              children: item.children
            }
          }
        },
        jurisdiction: {
          label: this.i18n.jurisdictionPlural[1],
          key: 'jurisdiction',
          expanded: this.filterExpanded.jurisdiction,
          getItems: () => searcher.listJurisdictions(),
          // itemFilter: (item) => item.rank < 3,
          itemMap: (item) => {
            return { label: item.name, value: item.name, id: item.id }
          }
        },
        categories: {
          label: this.i18n.topicPlural[1],
          key: 'categories',
          expanded: this.filterExpanded.categories,
          getItems: (q) => searcher.listCategories(q),
          hasSearch: true,
          multi: true,
          itemMap: (item) => {
            return {
              label: treeLabel(item),
              value: item.name,
              id: item.id,
              children: item.children
            }
          }
        }
      }
    },
    currentHeaders () {
      return this.headers.filter((x) => !this.hasFilter(x.key))
    },
    publicBodies () {
      return this.getPublicBodiesByScope(this.scope)
    },
    hasNextSearchResults () {
      let meta = this.getScopedSearchMeta(this.scope)
      if (!meta) {
        return false
      }
      return meta.next
    },
    selectAllButtonDisabled () {
      return !(this.hasSearchResults && this.canSelectAll)
    },
    canSelectAll () {
      let searchCount = 0
      let meta = this.getScopedSearchMeta(this.scope)
      if (meta) {
        searchCount = meta.total_count
      }
      return this.publicBodies.length + searchCount <= MAX_PUBLICBODIES
    },
    maxResultPage () {
      let meta = this.getScopedSearchMeta(this.scope)
      if (!meta) {
        return 0
      }
      return Math.ceil(meta.total_count / meta.limit)
    },
    blockProgressWidth () {
      return `width: ${this.blockProgress}%`
    },
    ...mapGetters([
      'getPublicBodiesByScope',
      'getScopedSearchMeta'
    ])
  },
  methods: {
    togglePane (e) {
      this.tabPane = e.target.dataset.pane
    },
    hasFilter (key) {
      let v = this.filters[key]
      if (v === undefined) {
        return false
      }
      if (v === null) {
        return false
      }
      if (Array.isArray(v) && v.length === 0) {
        return false
      }
      return true
    },
    selectAll () {
      this.blockUI = true
      this.blockMessage = this.i18n.selectingAll
      if (this.currentResultPage !== 1) {
        this.runAutocomplete().then(() => this.selectAll())
      } else {
        this.selectAllRows(true)
        this.selectAllNext(1)
      }
    },
    selectAllNext (num) {
      this.blockProgress = num / this.maxResultPage * 100
      if (this.hasNextSearchResults) {
        this.getNextSearchResults(this.scope).then(() => {
          this.selectAllRows(true)
          if (this.hasNextSearchResults) {
            this.selectAllNext(num + 1)
          } else {
            this.blockUI = false
            this.tabPane = 'chosen'
          }
        })
      } else {
        this.blockUI = false
      }
    },
    clearSearch () {
      this.clearResults()
      this.filters = {}
    },
    setFilterExpand (filter, expand) {
      let expanded = {
        [filter.key]: expand
      }
      if (expand) {
        for (let key in this.filterExpanded) {
          if (key !== filter.key) {
            expanded[key] = false
          }
        }
      }
      this.filterExpanded = expanded
    },
    updateFilter (filter, value) {
      Vue.set(this.filters, filter.key, value)
      this.triggerAutocomplete()
    },
    ...mapMutations({
      setStepRequest: SET_STEP_REQUEST,
      addPublicBodyId: ADD_PUBLICBODY_ID,
      removePublicBodyId: REMOVE_PUBLICBODY_ID,
      clearPublicBodies: CLEAR_PUBLICBODIES
    }),
    ...mapActions([
      'getNextSearchResults'
    ])
  },
  watch: {
    defaultsearch: function () {
      this.triggerAutocomplete()
    }
  }
}
</script>

<style lang="scss" scoped>
  @import "../../styles/variables";

  button[disabled] {
    cursor: not-allowed;
  }
  @mixin filter-divider() {
    .filter-column:not(:first-child) {
      padding-top: 1em;
    }
    .filter-column:not(:last-child) {
      border-bottom: 2px solid $gray-300;
      padding-bottom: 1em;
    }
  }
  @include media-breakpoint-up(md) {
    @include filter-divider();
  }
  @include media-breakpoint-down(xs) {
    @include filter-divider();
  }
</style>
