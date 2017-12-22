<template>
  <div class="publicbody-chooser mb-3">
    <ul class="nav nav-tabs">
      <li class="nav-item">
        <a href="#pb-select-pane" @click.prevent="togglePane" class="nav-link" :class="{ active: selectPane }" data-pane="select" data-toggle="tab" role="tab" aria-controls="pb-select-pane" :aria-expanded="selectPane">
          {{ i18n.selectPublicBodies}}
        </a>
      </li>
      <li class="nav-item">
        <a href="#pb-chosen-pane" @click.prevent="togglePane" class="nav-link" :class="{ active: chosenPane }"  data-pane="chosen" data-toggle="tab" role="tab" aria-controls="pb-chosen-pane" aria-expanded="chosenPane">
          {{ i18n._('publicBodiesChosen', {count: publicBodies.length}) }}
        </a>
      </li>
      <li class="nav-item ml-auto">
        <a class="btn btn-primary" href="#step-request" @click="setStepRequest"  v-show="hasPublicBodies">
          {{ i18n.continue }}
        </a>
      </li>
    </ul>
    <div class="tab-content mt-3">
      <div role="tabpanel" class="tab-pane" :class="{ active: selectPane }" id="pb-select-pane">
        <div class="row">
          <div class="form-search col-md-8">
            <div class="input-group">
              <input type="search" v-model:value="search" class="search-public_bodies form-control" :placeholder="i18n.publicBodySearchPlaceholder" @keyup="triggerAutocomplete" @keydown.enter.prevent="triggerAutocomplete"/>
              <span class="input-group-btn">
                <button type="button" class="btn btn-primary search-public_bodies-submit" @click="triggerAutocomplete">
                  <i class="fa fa-search"></i>
                  {{ i18n.search }}
                </button>
              </span>
            </div>
          </div>
        </div>

        <div class="row">
          <div class="col-md-4 order-md-2">
            <div class="row mt-3">
              <div v-for="filter in filterConfig" class="col-sm-4 col-md-12">
                <pb-filter :config="filter" @update="updateFilter" :value="filters[filter.key]"></pb-filter>
              </div>
            </div>
          </div>
          <div class="col-md-8 order-md-1">
            <p class="mt-3">
              <a href="#" @click="selectAll" class="btn btn-light">
                {{ i18n.selectAll }}
              </a>
              <img v-show="searching" :src="config.resources.spinner" alt="Loading..."/>
            </p>

            <pb-table :name="name" :scope="scope" :i18n="i18n" :headers="headers" :options="selectOptions" :rows="searchResults"></pb-table>
            <pb-pagination :scope="scope" :i18n="i18n"></pb-pagination>
          </div>
        </div>
      </div>

      <div role="tabpanel" class="tab-pane" :class="{ active: chosenPane }" id="pb-chosen-pane">
        <pb-summary :scope="scope" :i18n="i18n" :dimensions="summaryDimensions"></pb-summary>

        <pb-table :name="name" :scope="scope" :i18n="i18n" :headers="headers" :options="chosenOptions" :rows="publicBodies"></pb-table>
      </div>

    </div>
  </div>
</template>

<script>
import Vue from 'vue'

import {mapGetters, mapMutations} from 'vuex'
import {SET_STEP_REQUEST, ADD_PUBLICBODY_ID} from '../store/mutation_types'

import {FroideSearch} from '../lib/search'
import PBChooserMixin from '../lib/pb-chooser-mixin'
import I18nMixin from '../lib/i18n-mixin'

import PbTable from './pb-table'
import PbPagination from './pb-pagination'
import PbSummary from './pb-summary'
import PbFilter from './pb-filter'

export default {
  name: 'publicbody-multi-chooser',
  mixins: [PBChooserMixin, I18nMixin],
  props: ['name', 'scope', 'defaultsearch', 'formJson', 'config'],
  components: {
    PbTable,
    PbPagination,
    PbSummary,
    PbFilter
  },
  data () {
    return {
      search: '',
      lastQuery: null,
      emptyResults: false,
      searching: false,
      tabPane: 'select',
      selectOptions: {},
      chosenOptions: {
        sortableHeader: true
      },
      filters: {
        jurisdiction: null
      }
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
      return [
        {
          label: this.i18n.jurisdictionPlural[1],
          key: 'jurisdiction',
          getItems: () => searcher.listJurisdiction(),
          itemFilter: (item) => item.rank < 3,
          itemMap: (item) => {
            return { label: item.name, value: item.name }
          }
        },
        {
          label: this.i18n.topicPlural[1],
          key: 'tags',
          getItems: () => searcher.listPublicbodyTag(),
          itemMap: (item) => {
            return { label: item.name, value: item.name }
          }
        }
      ]
    },
    headers () {
      return [
        { label: this.i18n.name, sortKey: (x) => x.name },
        { label: this.i18n.jurisdictionPlural[0], sortKey: (x) => x.jurisdiction.name }
      ]
    },
    summaryDimensions () {
      return [
        {
          id: 'jurisdiction',
          i18nLabel: 'jurisdictionPlural',
          key: (x) => x.jurisdiction.name
        }
      ]
    },
    selectPane () {
      return this.tabPane === 'select'
    },
    chosenPane () {
      return this.tabPane === 'chosen'
    },
    publicBodies () {
      return this.getPublicBodiesByScope(this.scope)
    },
    ...mapGetters([
      'getPublicBodiesByScope'
    ])
  },
  methods: {
    togglePane (e) {
      this.tabPane = e.target.dataset.pane
    },
    selectAll () {
      this.searchResults.forEach((r) => {
        this.addPublicBodyId({
          publicBodyId: r.id,
          scope: this.scope
        })
      })
    },
    updateFilter (filter, value) {
      Vue.set(this.filters, filter.key, value)
      this.triggerAutocomplete()
    },
    ...mapMutations({
      setStepRequest: SET_STEP_REQUEST,
      addPublicBodyId: ADD_PUBLICBODY_ID
    })
  },
  watch: {
    defaultsearch: function () {
      this.triggerAutocomplete()
    }
  }
}
</script>

<style lang="scss" scoped>

</style>
