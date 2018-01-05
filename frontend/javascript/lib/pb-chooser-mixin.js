import {debounce} from 'underscore'
import {mapGetters, mapMutations, mapActions} from 'vuex'

import {
  SET_PUBLICBODY, SET_PUBLICBODIES,
  SET_SEARCHRESULTS, CLEAR_SEARCHRESULTS, CACHE_PUBLICBODIES
} from '../store/mutation_types'

var PBChooserMixin = {
  created () {
    if (this.hasForm && this.field.value) {
      let pbs = this.field.objects
      this.cachePublicBodies(pbs)
      this.setPublicBodies({
        publicBodies: pbs,
        scope: this.scope
      })
    }
  },
  computed: {
    help_url () {
      return this.config.url.helpAbout
    },
    hasForm () {
      return (this.formJson !== undefined && this.formJson !== null &&
              this.formJson !== '')
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
    hasPublicBodies () {
      return this.publicBodies.length > 0
    },
    debouncedAutocomplete () {
      return debounce(this.runAutocomplete, 300)
    },
    hasFilters () {
      if (!this.filters) { return false }
      return Object.keys(this.filters).length > 0
    },
    hasSearchResults () {
      return this.searchResults.length > 0
    },
    searchResults () {
      return this.getScopedSearchResults(this.scope)
    },
    ...mapGetters([
      'getPublicBodyByScope',
      'getScopedSearchResults',
      'getScopedSearchMeta'
    ])
  },
  methods: {
    buildQuery () {
      let query = this.search
      if (this.hasFilters) {
        query += JSON.stringify(this.filters)
      }
      return query
    },
    triggerAutocomplete () {
      if (this.search === '' && !this.hasFilters) {
        // this.searchResults = []
        this.searching = false
      }
      if (this.search !== undefined && this.search.length < 3 &&
           !this.hasFilters) {
        this.searching = false
        return
      }
      let query = this.buildQuery()
      if (query === this.lastQuery &&
          this.searchResults.length !== 0) {
        this.searching = false
        return
      }
      this.searching = true
      this.debouncedAutocomplete()
    },
    runAutocomplete () {
      this.searching = true
      this.lastQuery = this.buildQuery()
      this.getSearchResults({
        scope: this.scope,
        search: this.search,
        filters: this.filters
      }).then(() => {
        this.searching = false
      })
    },
    clearResults () {
      this.clearSearchResults({scope: this.scope})
    },
    ...mapMutations({
      setPublicBody: SET_PUBLICBODY,
      setPublicBodies: SET_PUBLICBODIES,
      setSearchResults: SET_SEARCHRESULTS,
      cachePublicBodies: CACHE_PUBLICBODIES,
      clearSearchResults: CLEAR_SEARCHRESULTS
    }),
    ...mapActions(['getSearchResults'])
  }
}

export default PBChooserMixin
