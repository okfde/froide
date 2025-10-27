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
          class="btn btn-outline-primary search-public_bodies-submit"
          @click="triggerAutocomplete">
          <i class="fa fa-search" />
          {{ i18n.search }}
        </button>
      </div>

      <div v-if="showFilters" class="row mt-3">
        <!-- <div class="col-4 filter-column position-relative">
          <pb-filter
            :global-config="config"
            :expanded="filterExpanded.jurisdiction"
            :config="filterConfig.jurisdiction"
            :i18n="i18n"
            :scope="scope"
            :value="filters.jurisdiction"
            @update="updateJurisdictionFilter"
            @setFilterExpand="setFilterExpand"></pb-filter>
        </div> -->
        <div
          v-for="filterKey in filterOrder"
          :key="filterKey"
          class="col-4 filter-column position-relative">
          <PbFilter
            :global-config="config"
            :expanded="filterExpanded[filterKey]"
            :config="filterConfig[filterKey]"
            :i18n="i18n"
            :scope="scope"
            :value="filters[filterKey]"
            @update="updateFilter"
            @set-filter-expand="setFilterExpand"></PbFilter>
        </div>
      </div>
    </div>
    <div class="row mt-3">
      <p
        v-show="
          !searching && lastQuery && (showFoundCountIfIdle || searchMeta)
        ">
        {{ i18n._('publicBodiesFound', { count: searchResultsLength }) }}
      </p>
    </div>
    <div v-if="showBadges" class="row">
      <div v-if="search" class="col-3">
        <PbFilterBadge
          label="Freitext"
          :value="search"
          :i18n="i18n"
          @remove-click="search = ''"
          />
      </div>
      <div v-for="filterKey in activeFilters" :key="filterKey" class="col-4">
        <PbFilterSelected
          :config="filterConfig[filterKey]"
          @update="updateFilter"
          :value="filters[filterKey]"
          :i18n="i18n"
          >
        </PbFilterSelected>
      </div>
    </div>

    <div v-if="searching" class="search-spinner">
      <div class="spinner-border" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
    </div>
    <component :is="listView" :name="name" :scope="scope" :config="config"
      @update="$emit('update', $event)"
      @step-next="$emit('stepNext')"
      />
  </div>
</template>

<script>
import PBResultList from './pb-result-list'
import PBActionList from './pb-action-list'
import PBMultiList from './pb-multi-list'
import PBBetaList from './pb-beta-list'

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
    PbFilterBadge
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
      filterExpanded: {
        // classification: true
      },
      filterOrder: [
        // TODO: 'jurisdiction-and-regions'
        'jurisdiction',
        'regions',
        'categories',
        // 'classification'
        // 'regions_kind',
      ]
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
          expanded: this.filterExpanded.classification,
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
          expanded: this.filterExpanded.jurisdiction,
          multi: true,
          getItems: () => searcher.listJurisdictions(),
          // itemFilter: (item) => item.rank < 3,
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
          expanded: this.filterExpanded.categories,
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
          label: this.i18n.location, // this.i18n.containingGeoregionsPlural[0],
          key: 'regions',
          multi: true,
          expanded: this.filterExpanded.georegion,
          initialFilters: { kind: this.config.fixtures.georegion_kind[0][0] },
          getItems: (q, filters) => searcher.listGeoregions(q, filters),
          hasSearch: true,
          choices: ['kind',
            [
              // ['', '(Alle)'],
              ...this.config.fixtures.georegion_kind
            ]
          ],
          choicesNoneLabel: this.i18n.filterPlaceholder,
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
  }
}
</script>