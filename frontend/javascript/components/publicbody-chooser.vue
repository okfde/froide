<template>
  <div class="publicbody-chooser mb-3">
    <div class="form-search">
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
    <div v-if="searching" class="search-spinner">
      <img :src="config.resources.spinner" alt="Loading..."/>
    </div>
    <component :is="getListView" :name="name" :scope="scope" :i18n="i18n"></component>
  </div>
</template>

<script>

import {mapGetters} from 'vuex'

import PBResultList from './pb-result-list'
import PBActionList from './pb-action-list'
import PBMultiList from './pb-multi-list'

import PbChooserMixin from '../lib/pb-chooser-mixin'

export default {
  name: 'publicbody-chooser',
  mixins: [PbChooserMixin],
  props: ['name', 'scope', 'defaultsearch', 'formJson', 'config', 'listView'],
  created () {
    if (this.hasForm && this.field.value) {
      let pbs = this.field.objects
      this.cachePublicBodies(pbs)
      this.setPublicBodies({
        publicbodies: pbs,
        scope: this.scope
      })
    }
  },
  data () {
    return {
      publicbodies: {},
      search: this.defaultsearch,
      lastSearch: null,
      emptyResults: false,
      searching: false
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
      if (this.publicbody) {
        return this.publicbody.name
      }
    },
    publicbody () {
      return this.getPublicBodyByScope(this.scope)
    },
    ...mapGetters([
      'getPublicBodyByScope'
    ])
  }
}
</script>
