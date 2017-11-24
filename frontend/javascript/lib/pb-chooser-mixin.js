import {debounce} from 'underscore'
import {mapGetters, mapMutations, mapActions} from 'vuex'

import {
  SET_PUBLICBODY, SET_PUBLICBODIES,
  SET_SEARCHRESULTS, CACHE_PUBLICBODIES
} from '../store/mutation_types'

var PbChooserMixin = {
  computed: {
    help_url () {
      return this.config.url.helpAbout
    },
    i18n () {
      return this.config.i18n
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
    debouncedAutocomplete () {
      return debounce(this.runAutocomplete, 300)
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
    fillSearch (event) {
      this.search = event.target.dataset.search
      this.triggerAutocomplete()
    },
    triggerAutocomplete () {
      if (this.search === '') {
        // this.searchResults = []
        this.searching = false
      }
      if (this.search !== undefined && this.search.length < 3) {
        return
      }
      this.debouncedAutocomplete()
    },
    runAutocomplete () {
      if (this.search === this.lastSearch &&
          this.searchResults.length !== 0) {
        this.searching = false
        return
      }
      this.searching = true
      this.lastSearch = this.search
      this.getSearchResults({
        scope: this.scope,
        search: this.search
      }).then(() => {
        this.searching = false
      })
    },
    ...mapMutations({
      setPublicBody: SET_PUBLICBODY,
      setPublicBodies: SET_PUBLICBODIES,
      setSearchResults: SET_SEARCHRESULTS,
      cachePublicBodies: CACHE_PUBLICBODIES
    }),
    ...mapActions(['getSearchResults'])
  }
}

export default PbChooserMixin
