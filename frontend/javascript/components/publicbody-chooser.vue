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

import PBResultList from './pb-result-list'
import PBActionList from './pb-action-list'
import PBMultiList from './pb-multi-list'

import PBChooserMixin from '../lib/pb-chooser-mixin'
import I18nMixin from '../lib/i18n-mixin'

export default {
  name: 'publicbody-chooser',
  mixins: [PBChooserMixin, I18nMixin],
  props: ['name', 'scope', 'defaultsearch', 'formJson', 'config', 'listView'],
  data () {
    return {
      search: this.defaultsearch,
      lastQuery: null,
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
      if (this.publicBody) {
        return this.publicBody.name
      }
    },
    publicBody () {
      return this.getPublicBodyByScope(this.scope)
    }
  },
  watch: {
    defaultsearch: function () {
      this.triggerAutocomplete()
    }
  }
}
</script>
