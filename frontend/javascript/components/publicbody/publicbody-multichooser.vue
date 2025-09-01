<template>
  <div class="publicbody-chooser mb-3">
    <div v-if="blockUI" class="mt-5 text-center">
      <h4>
        {{ blockMessage }}
      </h4>
      <div
        class="progress"
        role="progressbar"
        :aria-valuenow="blockProgress"
        aria-valuemin="0"
        aria-valuemax="100"
      >
        <div class="progress-bar" :style="blockProgressWidth"></div>
      </div>
    </div>
    <template v-else>
      <div class="row">
        <div class="form-search col-md-8 mt-3">
          <label for="publicbody-multi-search-input">{{
            i18n.searchPublicBodyLabel
          }}</label>
          <div class="input-group">
            <input
              id="publicbody-multi-search-input"
              type="search"
              class="search-public_bodies form-control form-control-lg"
              v-model="search"
              :placeholder="i18n.publicBodySearchPlaceholder"
              @keyup="triggerAutocomplete"
              @keydown.enter.prevent="triggerAutocomplete"
            />
            <button
              type="button"
              class="btn btn-primary search-public_bodies-submit"
              @click="triggerAutocomplete"
            >
              <i class="fa fa-search"></i>
              {{ i18n.search }}
            </button>
          </div>
        </div>
      </div>
      <div class="row mb-4 mt-5">
        <div class="col-auto">
          <h3 v-show="!searching">
            {{ i18n._('publicBodiesFound', { count: searchResultsLength }) }}
          </h3>
          <div v-show="searching" class="col-auto">
            <div class="spinner-border text-secondary" role="status">
              <span class="visually-hidden">{{ i18n.loading }}</span>
            </div>
          </div>
        </div>
        <div class="col-auto">
          <button
            @click.prevent="selectAll"
            class="btn btn-sm btn-outline-secondary"
            :disabled="selectAllButtonDisabled"
          >
            {{ i18n._('selectAll', { count: searchResultsLength }) }}
          </button>
        </div>
        <div class="col-auto">
          <button
            :disabled="!hasSearchResults"
            @click.prevent="clearSearch"
            class="btn-sm btn btn-outline-secondary"
          >
            {{ i18n.clearSearchResults }}
          </button>
        </div>
        <div class="col-auto ms-auto">
          <button
            :disabled="!stepCanContinue(scope)"
            type="button"
            class="btn btn-primary"
            @click="setStepReviewPublicbody"
            >§Weiter mit Auswahl</button>
        </div>
      </div>
      <div class="row">
        <div class="col-md-8 col-lg-9 order-2">
          <PbTable
            :name="name"
            :scope="scope"
            :i18n="i18n"
            :headers="currentHeaders"
            :options="selectOptions"
            :rows="searchResults"
            @select-all-rows="selectAllRows"
          ></PbTable>
          <div
            v-show="searching"
            class="spinner-border text-secondary"
            role="status"
          >
            <span class="visually-hidden">{{ i18n.loading }}</span>
          </div>
          <slot name="publicbody-missing" v-if="!searching"></slot>
          <PbPagination :scope="scope" :i18n="i18n"></PbPagination>
        </div>
        <div class="col-md-4 col-lg-3 order-md-1">
          <PbFilterSelected
            v-for="filterKey in filterOrder"
            :key="filterKey"
            :config="filterConfig[filterKey]"
            @update="updateFilter"
            :value="filters[filterKey]"
          >
          </PbFilterSelected>
          <div class="row mt-3">
            <div
              v-for="filterKey in filterOrder"
              :key="filterKey"
              class="col-sm-4 col-md-12 filter-column position-relative"
            >
              <PbFilter
                :global-config="config"
                :expanded="filterExpanded[filterKey]"
                :config="filterConfig[filterKey]"
                :i18n="i18n"
                :scope="scope"
                :value="filters[filterKey]"
                @update="updateFilter"
                @set-filter-expand="setFilterExpand"
              ></PbFilter>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import { mapGetters, mapMutations, mapActions } from 'vuex'
import {
  SET_STEP_REQUEST,
  SET_STEP_REVIEW_PUBLICBODY,
  ADD_PUBLICBODY_ID,
  REMOVE_PUBLICBODY_ID,
  CLEAR_PUBLICBODIES
} from '../../store/mutation_types'

import { FroideAPI } from '../../lib/api'
import I18nMixin from '../../lib/i18n-mixin'

import PBChooserMixin from './lib/pb-chooser-mixin'
import PBListMixin from './lib/pb-list-mixin'

import PbTable from './pb-table'
import PbPagination from './pb-pagination'
import PbFilter from './pb-filter'
import PbFilterSelected from './pb-filter-selected'

const MAX_PUBLICBODIES = 800

function treeLabel(item) {
  return '-'.repeat(item.depth - 1) + ' ' + item.name
}

export default {
  name: 'PublicbodyMultiChooser',
  mixins: [PBChooserMixin, PBListMixin, I18nMixin],
  props: {
    name: {
      type: String,
      required: true
    },
    scope: {
      type: String,
      required: true
    },
    defaultsearch: {
      type: String,
      default: ''
    },
    formJson: {
      type: Object,
      default: () => ({})
    },
    config: {
      type: Object,
      default: () => ({})
    }
  },
  components: {
    PbTable,
    PbPagination,
    PbFilter,
    PbFilterSelected
  },
  allowEmptySearch: true,
  mounted() {
    if (!this.hasSearchResults) {
      this.triggerAutocomplete()
    }
  },
  data() {
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
      filters: this.getEmptyFilters(),
      filterExpanded: {
        classification: true
      },
      filterOrder: [
        'classification',
        'jurisdiction',
        'categories',
        'regions_kind',
        'regions'
      ]
    }
  },
  computed: {
    getListView() {
      if (!this.listView) {
        return 'resultList'
      }
      return this.listView
    },
    filterConfig() {
      const searcher = new FroideAPI(this.config)
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
            return { label: item.name, id: item.id }
          }
        },
        categories: {
          label: this.i18n.topicPlural[1],
          key: 'categories',
          expanded: this.filterExpanded.categories,
          getItems: (q, filters) => searcher.listCategories(q, filters),
          hasSearch: true,
          multi: true,
          itemMap: (item) => {
            return {
              label: treeLabel(item),
              id: item.id,
              children: item.children
            }
          }
        },
        regions: {
          label: this.i18n.containingGeoregionsPlural[0],
          key: 'regions',
          expanded: this.filterExpanded.georegion,
          getItems: (q, filters) => searcher.listGeoregions(q, filters),
          hasSearch: true,
          choices: ['kind', this.config.fixtures.georegion_kind],
          itemMap: (item) => {
            return {
              label: item.name,
              id: item.id
            }
          }
        },
        regions_kind: {
          label: this.i18n.administrativeUnitKind,
          key: 'regions_kind',
          getItems: () =>
            Promise.resolve({
              meta: { next: null },
              objects: this.config.fixtures.georegion_kind
            }),
          itemMap: (item) => {
            return { label: item[1], id: item[0] }
          }
        }
      }
    },
    currentHeaders() {
      return this.headers.filter((x) => !this.hasFilter(x.key))
    },
    publicBodies() {
      return this.getPublicBodiesByScope(this.scope)
    },
    hasNextSearchResults() {
      const meta = this.getScopedSearchMeta(this.scope)
      if (!meta) {
        return false
      }
      return meta.next
    },
    selectAllButtonDisabled() {
      return !(this.hasSearchResults && this.canSelectAll)
    },
    canSelectAll() {
      let searchCount = 0
      const meta = this.getScopedSearchMeta(this.scope)
      if (meta) {
        searchCount = meta.total_count
      }
      return this.publicBodies.length + searchCount <= MAX_PUBLICBODIES
    },
    maxResultPage() {
      const meta = this.getScopedSearchMeta(this.scope)
      if (!meta) {
        return 0
      }
      return Math.ceil(meta.total_count / meta.limit)
    },
    blockProgressWidth() {
      return `width: ${this.blockProgress}%`
    },
    ...mapGetters([
      'getPublicBodiesByScope',
      'getScopedSearchMeta',
      'stepCanContinue',
    ])
  },
  methods: {
    togglePane(e) {
      this.tabPane = e.target.dataset.pane
    },
    getEmptyFilters() {
      return {
        classification: null,
        jurisdiction: null,
        categories: [],
        regions: null,
        regions_kind: null
      }
    },
    hasFilter(key) {
      const v = this.filters[key]
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
    selectAll() {
      this.blockUI = true
      this.blockMessage = this.i18n.selectingAll
      if (this.currentResultPage !== 1) {
        this.runAutocomplete().then(() => this.selectAll())
      } else {
        this.selectAllRows(true)
        this.selectAllNext(1)
      }
    },
    selectAllNext(num) {
      this.blockProgress = (num / this.maxResultPage) * 100
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
    clearSearch() {
      this.clearResults()
      this.filters = this.getEmptyFilters()
      this.search = ''
      this.triggerAutocomplete()
    },
    setFilterExpand(filter, expand) {
      const expanded = {
        [filter.key]: expand
      }
      if (expand) {
        for (const key in this.filterExpanded) {
          if (key !== filter.key) {
            expanded[key] = false
          }
        }
      }
      this.filterExpanded = expanded
    },
    updateFilter(filter, value) {
      this.filters[filter.key] = value
      this.triggerAutocomplete()
    },
    ...mapMutations({
      setStepRequest: SET_STEP_REQUEST,
      setStepReviewPublicbody: SET_STEP_REVIEW_PUBLICBODY,
      addPublicBodyId: ADD_PUBLICBODY_ID,
      removePublicBodyId: REMOVE_PUBLICBODY_ID,
      clearPublicBodies: CLEAR_PUBLICBODIES
    }),
    ...mapActions(['getNextSearchResults'])
  },
  watch: {
    defaultsearch: function () {
      this.triggerAutocomplete()
    }
  }
}
</script>

<style lang="scss" scoped>
@import '../../../styles/variables';

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
