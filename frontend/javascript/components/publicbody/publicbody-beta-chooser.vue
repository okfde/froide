<template>
  <div class="publicbody-chooser mb-3">
    <button
      v-if="!showSearch"
      class="btn btn-sm btn-light float-end"
      @click.prevent="showSearch = true">
      {{ i18n.searchPublicBodyLabel }}
    </button>
    <div v-if="showSearch" class="form-search">
      <div class="input-group">
        <input
          v-model="search"
          type="search"
          class="search-public_bodies form-control"
          :placeholder="i18n.publicBodySearchPlaceholder"
          @keyup="triggerAutocomplete"
          @keydown.enter.prevent="triggerAutocomplete" />
        <button
          type="button"
          class="btn btn-secondary search-public_bodies-submit"
          @click="triggerAutocomplete">
          <i class="fa fa-search" />
          {{ i18n.search }}
        </button>
      </div>

      <div v-if="showFilters" class="row mt-3">
        <div
          v-for="filterKey in filterOrder"
          :key="filterKey"
          class="col-sm-4 filter-column position-relative">
          <PbFilter
            :global-config="config"
            :config="filterConfig[filterKey]"
            :i18n="i18n"
            :scope="scope"
            :value="filters[filterKey]"
            @update="updateFilter"
            />
        </div>
      </div>
    </div>
    <div class="row mt-3">
      <p v-if="searching">
        <span class="spinner-border spinner-border-sm" role="status">
          <span class="visually-hidden">Loading...</span>
        </span>
      </p>
      <p v-else-if="lastQuery && (showFoundCountIfIdle || searchMeta)">
        {{ searching ? '…' : i18n._('publicBodiesFound', { count: searchResultsLength }) }}
      </p>
    </div>
    <div v-if="showBadges" class="mb-3 d-flex flex-wrap gap-2">
        <PbFilterBadge
          v-if="search"
          label="Freitext"
          :value="search"
          :i18n="i18n"
          @remove-click="search = ''"
          />
        <PbFilterSelected
          v-for="filterKey in activeFilters"
          :key="filterKey"
          :config="filterConfig[filterKey]"
          @update="updateFilter"
          :value="filters[filterKey]"
          :i18n="i18n"
          />
    </div>

    <component :is="listView" :name="name" :scope="scope" :config="config"
      @update="$emit('update', $event)"
      @step-next="$emit('stepNext')"
      />
    <!-- outside of listView component is awkward but easier than passing around v-model -->
    <ResultsPagination
      :response-meta="getScopedSearchMeta(scope)"
      v-model="pagination"
      />
  </div>
</template>

<script>
import PBResultList from './pb-result-list'
import PBActionList from './pb-action-list'
import PBMultiList from './pb-multi-list'
import PBBetaList from './pb-beta-list'
import ResultsPagination from '../makerequest/results-pagination.vue'

import { mapMutations, mapActions } from 'vuex'
import {
  SET_STEP_REQUEST,
  ADD_PUBLICBODY_ID,
  REMOVE_PUBLICBODY_ID,
  CLEAR_PUBLICBODIES
} from '../../store/mutation_types'

import { FroideAPI } from '../../lib/api'
import I18nMixin from '../../lib/i18n-mixin'
import PBListMixin from './lib/pb-list-mixin'

import PbFilter from './pb-filter'
import PbFilterSelected from './pb-filter-selected'
import PBChooserMixin from './lib/pb-chooser-mixin'
import PbFilterBadge from './pb-filter-badge'

const searchResultPageSize = 30

function treeLabel(item) {
  return item.name
}

export default {
  name: 'PublicbodyChooser',
  components: {
    resultList: PBResultList,
    actionList: PBActionList,
    multi: PBMultiList,
    betaList: PBBetaList,
    PbFilter,
    PbFilterSelected,
    PbFilterBadge,
    ResultsPagination,
  },
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
    form: {
      type: Object,
      required: false
    },
    config: {
      type: Object,
      required: true
    },
    searchCollapsed: {
      type: Boolean,
      default: false
    },
    listView: {
      type: String,
      default: 'betaList'
    },
    showFilters: {
      type: Boolean,
      default: true
    },
    showBadges: {
      type: Boolean,
      default: true
    },
    showFoundCountIfIdle: {
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      search: this.defaultsearch,
      lastQuery: null,
      searching: false,
      showSearch: !this.searchCollapsed,
      blockUI: false,
      blockMessage: null,
      blockProgress: 0,
      selectOptions: {
        selectAllCheckbox: true
      },
      filters: this.getEmptyFilters(),
      filterOrder: [
        'jurisdiction',
        'regions',
        'categories',
        // 'classification'
        // 'regions_kind',
      ],
      pagination: {
        offset: 0,
        limit: searchResultPageSize
      },
    }
  },
  computed: {
    label() {
      if (this.publicBody) {
        return this.publicBody.name
      }
      return ''
    },
    publicBody() {
      return this.getPublicBodyByScope(this.scope)
    },
    activeFilters() {
      return this.filterOrder.filter((filterKey) => {
        const value = this.filters[filterKey]
        if (value === null) {
          return false
        }
        return !(this.filterConfig[filterKey].multi && value.length === 0)
      })
    },
    filterConfig() {
      const searcher = new FroideAPI(this.config)
      return {
        classification: { // = Behörden-Typen
          label: this.i18n.classificationPlural[1],
          key: 'classification',
          initialFilters: { depth: 1 },
          multi: true,
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
          label: this.i18n.level, // this.i18n.jurisdictionPlural[1],
          key: 'jurisdiction',
          multi: true,
          getItems: () => searcher.listJurisdictions(),
          itemMap: (item) => {
            return {
              label: item.name,
              ...item
            }
          },
          groupBy: 'region_kind',
        },
        categories: { // = Themen
          label: this.i18n.topicPlural[1],
          key: 'categories',
          initialFilters: { depth: 1 },
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
          label: this.i18n.location,
          key: 'regions',
          multi: true,
          initialFilters: { kind: this.config.fixtures.georegion_kind[0][0] },
          getItems: (q, filters) => searcher.listGeoregions(q, filters),
          hasSearch: true,
          choices: ['kind', this.config.fixtures.georegion_kind],
          itemMap: (item) => {
            return {
              label: item.name,
              subLabel: item.kind_detail,
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
    }
  },
  methods: {
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
    updateFilter(filter, value) {
      this.filters[filter.key] = value
      this.triggerAutocomplete()
    },
    updateJurisdictionFilter(filter, value) {
      if (value) {
        const regionIds = value
          .filter((v) => v.rank === 2)
          .map((v) => ({ id: v.region.split('/').reverse()[1] }))
        if (regionIds.length > 0) {
          this.filters.regions = regionIds
        } else {
          this.filters.regions = null
        }
      }
      this.filters[filter.key] = value
      this.triggerAutocomplete()
    },
    ...mapMutations({
      setStepRequest: SET_STEP_REQUEST,
      addPublicBodyId: ADD_PUBLICBODY_ID,
      removePublicBodyId: REMOVE_PUBLICBODY_ID,
      clearPublicBodies: CLEAR_PUBLICBODIES
    }),
    ...mapActions(['getNextSearchResults'])
  },
  mounted() {
    if (this.defaultsearch && this.searchMeta === null) {
      this.triggerAutocomplete()
    }
  },
  watch: {
    'pagination.offset': function() {
      this.triggerAutocomplete()
    }
  },
}
</script>