<template>
  <div class="publicbody-chooser mb-3">
    <div class="form-search">
      <div class="input-group">
        <input type="search" v-model="search" class="search-public_bodies form-control" :placeholder="i18n.publicBodySearchPlaceholder" @keyup="triggerAutocomplete" @keydown.enter.prevent="triggerAutocomplete"/>
        <div class="input-group-append">
          <button type="button" class="btn btn-primary search-public_bodies-submit" @click="triggerAutocomplete">
            <i class="fa fa-search"></i>
            {{ i18n.search }}
          </button>
        </div>
      </div>
    </div>
    <div v-if="searching" class="search-spinner">
      <div class="spinner-border" role="status">
        <span class="sr-only">Loading...</span>
      </div>
    </div>
    <component :is="getListView" :name="name" :scope="scope" :config="config"></component>
  </div>
</template>

<script>
import {mapMutations} from 'vuex'

import PBResultList from './pb-result-list'
import PBActionList from './pb-action-list'
import PBMultiList from './pb-multi-list'

import PBChooserMixin from './lib/pb-chooser-mixin'
import I18nMixin from '../../lib/i18n-mixin'

import { SET_CONFIG } from '../../store/mutation_types'

export default {
  name: 'publicbody-chooser',
  mixins: [PBChooserMixin, I18nMixin],
  props: ['name', 'scope', 'defaultsearch', 'form', 'config', 'listView'],
  data () {
    return {
      search: this.defaultsearch,
      lastQuery: null,
      emptyResults: false,
      searching: false
    }
  },
  created () {
    this.setConfig(this.config)
  },
  mounted () {
    if (this.defaultsearch && this.searchMeta === null) {
      this.triggerAutocomplete()
    }
  },
  components: {
    resultList: PBResultList,
    actionList: PBActionList,
    multi: PBMultiList
  },
  computed: {
    getListView () {
      if (!this.listView) {
        return 'resultList'
      }
      return this.listView
    },
    label () {
      if (this.publicBody) {
        return this.publicBody.name
      }
    },
    publicBody () {
      return this.getPublicBodyByScope(this.scope)
    }
  },
  methods: {
    ...mapMutations({
      setConfig: SET_CONFIG,
    })
  }
}
</script>
