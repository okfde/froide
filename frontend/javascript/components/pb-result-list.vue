<template>
  <div>
    <div class="search-result" v-if="publicBody && !hasSearchResults">
      <label>
        <input type="radio" :data-label="publicBody.name" :name="name" :value="publicBody.id" v-model="value"/>
        {{ publicBody.name }}
        <small>
          {{ publicBody.jurisdiction.name }}
        </small>
      </label>
    </div>
    <ul v-if="searchResults.length > 0 || emptyResults" class="search-results list-unstyled">
      <li v-for="result in searchResults" class="search-result">
        <label>
          <input type="radio" :data-label="result.name" :name="name" :value="result.id" @change="selectSearchResult" @click="selectSearchResult" v-model="value"/>
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

import PBListMixin from '../lib/pb-list-mixin'

export default {
  name: 'pb-result-list',
  props: ['name', 'scope', 'i18n'],
  mixins: [PBListMixin],
  computed: {
    value: {
      get () {
        if (this.publicBody) {
          return this.publicBody.id
        }
      },
      set (value) {
        this.setPublicBody({
          publicBody: this.getPublicBody(value),
          scope: this.scope
        })
        this.clearSearchResults({scope: this.scope})
      }
    }
  },
  methods: {
    selectSearchResult (event) {
      this.value = event.target.value
    }
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
