<template>
  <div class="publicbody-chooser mb-3">
    <div class="form-search">
      <div class="input-group">
        <input type="search" v-model:value="search" class="search-public_bodies form-control" :placeholder="i18n.publicBodySearchPlaceholder" @keyup="triggerAutocomplete" @keydown.enter.prevent="triggerAutocomplete"/>
        <span class="input-group-btn">
          <button type="button" class="btn btn-primary btn-lg search-public_bodies-submit" @click="triggerAutocomplete">
            <i class="fa fa-search"></i>
            {{ i18n.search }}
          </button>
        </span>
      </div>
    </div>
    <div v-if="searching" class="search-spinner">
      <img :src="config.resources.spinner" alt="Loading..."/>
    </div>
    <component :is="listView" :name="name" :scope="scope" :i18n="i18n"></component>
  </div>
</template>

<script>

import {debounce} from 'underscore'
import {mapGetters, mapMutations} from 'vuex'

import {
  SET_PUBLICBODY, SET_PUBLICBODIES,
  SET_SEARCHRESULTS, CACHE_PUBLICBODIES
} from '../store/mutation_types'
import {FroideSearch} from '../lib/search'

import PBResultList from './pb-result-list'

export default {
  name: 'publicbody-chooser',
  props: ['name', 'scope', 'defaultsearch', 'formJson', 'config'],
  mounted: function () {
    this.pbSearch = new FroideSearch(this.config)

    if (this._form.cleaned_data) {
      this.cachePublicBodies([this._form.cleaned_data[this.name]])
      this.setPublicbody({
        publicbody: this._form.cleaned_data[this.name],
        scope: this.scope
      })
    }
    if (this.field.objects) {
      this.cachePublicBodies([this.field.objects])
      this.setPublicBodies({
        publicbodies: this.field.objects,
        scope: this.scope
      })
    }
    if (this.field.value) {
      this.value = this.field.value
    }
  },
  data () {
    return {
      publicbodies: {},
      search: this.defaultsearch,
      lastSearch: null,
      emptyResults: false,
      searching: false,
      listView: 'result'
    }
  },
  components: {
    result: PBResultList
  },
  computed: {
    help_url () {
      return this.config.url.helpAbout
    },
    i18n () {
      return this.config.i18n
    },
    _form () {
      return JSON.parse(this.formJson)
    },
    form () {
      return this._form.fields
    },
    field () {
      return this.form[this.name]
    },
    errors () {
      return this._form.errors
    },
    label () {
      if (this.publicbody) {
        return this.publicbody.name
      }
    },
    debouncedAutocomplete () {
      return debounce(this.runAutocomplete, 300)
    },
    publicbody () {
      return this.getPublicBodyByScope(this.scope)
    },
    publicbodyDetails () {
      return this.getPublicBodyDetailsByScope(this.scope)
    },
    searchResults () {
      return this.getScopedSearchResults(this.scope)
    },
    ...mapGetters([
      'getPublicBodyByScope',
      'getPublicBodyDetailsByScope',
      'getScopedSearchResults',
      'getScopedSearchMeta'
    ])
  },
  methods: {
    fillSearch (event) {
      this.search = event.target.dataset.search
      this.triggerAutocomplete()
    },
    triggerAutocomplete () {
      if (this.search === '') {
        // this.searchResults = []
        this.emptyResults = false
        this.searching = false
      }
      if (this.search !== undefined && this.search.length < 3) {
        return
      }
      this.debouncedAutocomplete()
    },
    runAutocomplete () {
      if (this.search === this.lastSearch && !this.emptyResults &&
          this.searchResults.length !== 0) {
        this.searching = false
        return
      }
      this.searching = true
      this.lastSearch = this.search
      this.pbSearch.searchPublicBody(this.search).then((results) => {
        this.searching = false
        this.emptyResults = results.length === 0
        this.setSearchResults({
          searchResults: results.objects,
          searchMeta: results.meta,
          scope: this.scope
        })
        this.cachePublicBodies(results.objects)
      }, () => {
        this.searching = false
      })
    },
    fetchDetails (pb) {
      if (this.getPublicBodyDetailsByScope(this.scope, pb.id) !== undefined) {
        return
      }
      this.pbSearch.getPublicBody(pb.id).then((result) => {
        this.setPublicbodyDetail({
          publicbody: result,
          scope: this.scope
        })
      })
    },
    ...mapMutations({
      setPublicBody: SET_PUBLICBODY,
      setPublicBodies: SET_PUBLICBODIES,
      setSearchResults: SET_SEARCHRESULTS,
      cachePublicBodies: CACHE_PUBLICBODIES
    })
  }
}
</script>
