<template>
  <div class="publicbody-chooser mb-3">
    <button
      v-if="!showSearch"
      class="btn btn-sm btn-light float-right"
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
        <div class="input-group-append">
          <button
            type="button"
            class="btn btn-outline-primary search-public_bodies-submit"
            @click="triggerAutocomplete">
            <i class="fa fa-search" />
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
    <component :is="listView" :name="name" :scope="scope" :config="config" />
  </div>
</template>

<script>
import PBResultList from './pb-result-list'
import PBActionList from './pb-action-list'
import PBMultiList from './pb-multi-list'

import PBChooserMixin from './lib/pb-chooser-mixin'
import I18nMixin from '../../lib/i18n-mixin'

export default {
  name: 'PublicbodyChooser',
  components: {
    resultList: PBResultList,
    actionList: PBActionList,
    multi: PBMultiList
  },
  mixins: [PBChooserMixin, I18nMixin],
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
      required: true
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
      default: 'resultList'
    }
  },
  data() {
    return {
      search: this.defaultsearch,
      lastQuery: null,
      emptyResults: false,
      searching: false,
      showSearch: !this.searchCollapsed
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
    }
  },
  mounted() {
    if (this.defaultsearch && this.searchMeta === null) {
      this.triggerAutocomplete()
    }
  }
}
</script>
