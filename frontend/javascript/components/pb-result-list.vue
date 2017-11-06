<template>
  <div>
    <ul v-if="searchResults.length > 0 || emptyResults" class="search-results list-unstyled">
      <li v-for="result in searchResults" class="search-result">
        <label>
          <input type="radio" :data-label="result.name" :name="name" :value="result.id" @change="selectSearchResult" v-model="value"/>
          {{ result.name }}
          <small>
            {{ result.jurisdiction.name }}
          </small>
        </label>
      </li>
    </ul>
  </div>
</template>

<script>

import {mapGetters, mapMutations} from 'vuex'
import {SET_PUBLICBODY, CLEAR_SEARCHRESULTS} from '../store/mutation_types'

export default {
  name: 'publicbody-chooser',
  props: ['name', 'scope', 'i18n'],
  computed: {
    publicBody () {
      return this.getPublicBodyByScope(this.scope)
    },
    searchResults () {
      return this.getScopedSearchResults(this.scope)
    },
    emptyResults () {
      let meta = this.getScopedSearchMeta(this.scope)
      if (meta) {
        return meta.total_count === 0
      }
      return false
    },
    value: {
      get () {
        if (this.publicbody) {
          return this.publicbody.id
        }
      },
      set (value) {
        this.setPublicBody({
          publicbody: this.getPublicBody(value),
          scope: this.scope
        })
        this.clearSearchResults({scope: this.scope})
      }
    },
    ...mapGetters([
      'getPublicBody',
      'getPublicBodyByScope',
      'getScopedSearchResults',
      'getScopedSearchMeta'
    ])

  },
  methods: {
    selectSearchResult (event) {
      this.value = event.target.value
    },
    ...mapMutations({
      setPublicBody: SET_PUBLICBODY,
      clearSearchResults: CLEAR_SEARCHRESULTS
    })
  }
}
</script>

<style scoped>
  .search-results {
      overflow-y: auto;
      outline: 1px solid #aaa;
  }

  .search-result {
      cursor: pointer;
  }

  .search-result:hover {
      background-color: #f5f5f5;
  }

  .search-result.selected {
     background-color: #dff0d8;
  }

  .search-result > label {
      font-weight: normal;
      cursor: pointer;
  }

  .search-result > label > small{
      margin-left: 5px;
      color: #999;
  }

  .search-result > label > input {
      margin: 0 5px;
  }

  /* Enter and leave animations can use different */
  /* durations and timing functions.              */
  .slide-up-enter-active {
    transition: all .3s ease;
    transform-origin: top;
  }
  .slide-up-leave-active {
    transition: all .8s ease-in-out;
    transform-origin: top;
  }
  .slide-up-enter, .slide-up-leave-to {
    transform: scaleY(0);
    opacity: 0;
    max-height: 0;
  }
</style>
