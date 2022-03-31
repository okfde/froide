import { mapGetters, mapMutations, mapActions } from 'vuex'
import { SET_PUBLICBODY, CLEAR_SEARCHRESULTS } from '../../../store/mutation_types'

const PBListMixin = {
  computed: {
    publicBody () {
      return this.getPublicBodyByScope(this.scope)
    },
    publicBodies () {
      return this.getPublicBodiesByScope(this.scope)
    },
    hasPublicBodies () {
      return this.publicBodies.length > 0
    },
    searchResults () {
      return this.getScopedSearchResults(this.scope)
    },
    hasSearchResults () {
      return this.searchResults.length > 0
    },
    hasNextSearchResults () {
      const meta = this.getScopedSearchMeta(this.scope)
      if (!meta) {
        return false
      }
      return meta.next
    },
    hasPreviousSearchResults () {
      const meta = this.getScopedSearchMeta(this.scope)
      if (!meta) {
        return false
      }
      return meta.previous
    },
    currentResultPage () {
      const meta = this.getScopedSearchMeta(this.scope)
      if (!meta) {
        return 0
      }
      return (meta.offset / meta.limit) + 1
    },
    maxResultPage () {
      const meta = this.getScopedSearchMeta(this.scope)
      if (!meta) {
        return 0
      }
      return Math.ceil(meta.total_count / meta.limit)
    },
    currentResultsLength () {
      const sr = this.searchResults
      if (sr) {
        return sr.length
      }
      return null
    },
    searchResultsLength () {
      const meta = this.getScopedSearchMeta(this.scope)
      if (meta) {
        return meta.total_count
      }
      return 0
    },
    emptyResults () {
      const len = this.searchResultsLength
      if (len === null) {
        return false
      }
      return len === 0
    },
    ...mapGetters([
      'getPublicBody',
      'getPublicBodyByScope',
      'getPublicBodiesByScope',
      'getScopedSearchResults',
      'getScopedSearchMeta'
    ])

  },
  methods: {
    getNext (e) {
      this.getNextSearchResults(this.scope)
    },
    getPrevious (e) {
      this.getPreviousSearchResults(this.scope)
    },
    ...mapMutations({
      setPublicBody: SET_PUBLICBODY,
      clearSearchResults: CLEAR_SEARCHRESULTS
    }),
    ...mapActions([
      'getNextSearchResults',
      'getPreviousSearchResults'
    ])
  }
}

export default PBListMixin
