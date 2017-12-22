<template>
  <ul class="pagination" v-if="hasSearchResults">
    <li v-if="hasPreviousSearchResults" class="page-item">
      <a href="#" class="page-link prev" @click.prevent="getPrevious">
        <span aria-hidden="true">&laquo;</span>
        <span class="sr-only">{{ i18n.previous }}</span>
      </a>
    </li>
    <li v-else class="page-item disabled">
      <a class="page-link" href="#" tabindex="-1">
        <span aria-hidden="true">&laquo;</span>
        <span class="sr-only">{{ i18n.previous }}</span>
      </a>
    </li>
    <li class="page-item disabled">
      <span class="page-link">
        {{ currentResultPage }} / {{ maxResultPage }}
      </span>
    </li>
    <li v-if="hasNextSearchResults" class="page-item">
      <a href="#" class="page-link next" @click.prevent="getNext">
        <span aria-hidden="true">&raquo;</span>
        <span class="sr-only">{{ i18n.next }}</span>
      </a>
    </li>
    <li v-else class="page-item disabled">
      <a class="page-link" href="#" tabindex="-1">
        <span class="sr-only">{{ i18n.next }}</span>
        <span aria-hidden="true">&raquo;</span>
      </a>
    </li>
  </ul>
</template>

<script>

import {mapGetters, mapActions} from 'vuex'

export default {
  name: 'pb-pagination',
  props: ['scope', 'i18n'],
  computed: {
    searchResults () {
      return this.getScopedSearchResults(this.scope)
    },
    hasSearchResults () {
      return this.searchResults.length > 0
    },
    hasNextSearchResults () {
      let meta = this.getScopedSearchMeta(this.scope)
      if (!meta) {
        return false
      }
      return meta.next
    },
    hasPreviousSearchResults () {
      let meta = this.getScopedSearchMeta(this.scope)
      if (!meta) {
        return false
      }
      return meta.previous
    },
    currentResultPage () {
      let meta = this.getScopedSearchMeta(this.scope)
      if (!meta) {
        return 0
      }
      return (meta.offset / meta.limit) + 1
    },
    maxResultPage () {
      let meta = this.getScopedSearchMeta(this.scope)
      if (!meta) {
        return 0
      }
      return Math.ceil(meta.total_count / meta.limit)
    },
    currentResultsLength () {
      let sr = this.searchResults
      if (sr) {
        return sr.length
      }
      return null
    },
    searchResultsLength () {
      let meta = this.getScopedSearchMeta(this.scope)
      if (meta) {
        return meta.total_count
      }
      return null
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
    ...mapActions([
      'getNextSearchResults',
      'getPreviousSearchResults'
    ])
  }
}
</script>
