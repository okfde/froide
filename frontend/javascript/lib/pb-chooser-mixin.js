import {debounce} from 'underscore'
import {mapGetters, mapMutations, mapActions} from 'vuex'

import {
  SET_PUBLICBODY, SET_PUBLICBODIES,
  ADD_PUBLICBODY_ID, REMOVE_PUBLICBODY_ID,
  SET_SEARCHRESULTS, CLEAR_SEARCHRESULTS, CACHE_PUBLICBODIES,
  CLEAR_PUBLICBODIES, SET_STEP_SELECT_PUBLICBODY
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
    headers () {
      return [
        {
          key: 'name',
          label: this.i18n.name,
          sortKey: (x) => x.name
        },
        {
          key: 'jurisdiction',
          label: this.i18n.jurisdictionPlural[0],
          sortKey: (x) => x.jurisdiction.name
        },
        {
          key: 'classification',
          label: this.i18n.classificationPlural[0],
          sortKey: (x) => x.classification && x.classification.name
        },
        {
          key: 'categories',
          label: this.i18n.topicPlural[1],
          sortKey: (x) => x.categories[0] && x.categories[0].name
        }
      ]
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
    selectAllRows (select) {
      this.searchResults.forEach((r) => {
        if (select) {
          this.addPublicBodyId({
            publicBodyId: r.id,
            scope: this.scope
          })
        } else {
          this.removePublicBodyId({
            publicBodyId: r.id,
            scope: this.scope
          })
        }
      })
    },
    clearSelection () {
      if (window.confirm(this.i18n.reallyClearSelection)) {
        this.clearPublicBodies({scope: this.scope})
        this.setStepSelectPublicBody()
      }
    },
    triggerAutocomplete () {
      if (this.search === '' && !this.hasFilters) {
        // this.searchResults = []
        this.searching = false
      }
      if (!this.allowEmptySearch) {
        if (this.search !== undefined && this.search.length < 3 &&
             !this.hasFilters) {
          this.searching = false
          return
        }
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
      return this.getSearchResults({
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
      clearPublicBodies: CLEAR_PUBLICBODIES,
      clearSearchResults: CLEAR_SEARCHRESULTS,
      addPublicBodyId: ADD_PUBLICBODY_ID,
      setStepSelectPublicBody: SET_STEP_SELECT_PUBLICBODY,
      removePublicBodyId: REMOVE_PUBLICBODY_ID
    }),
    ...mapActions(['getSearchResults'])
  }
}

export default PBChooserMixin
