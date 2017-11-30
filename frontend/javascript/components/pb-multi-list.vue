<template>
  <div>
    <div v-if="searchResults.length > 0 || emptyResults">
      <div>
        <a class="btn btn-primary" href="#step-request" @click="setStepRequest"  v-show="hasPublicBodies">
          Continue
        </a>
        <a v-if="hasSearchResults" href="#" @click="selectAll" class="btn btn-light pull-right">
          Select all
        </a>
      </div>
      <ul class="search-results list-unstyled">
        <li v-for="result in searchResults" class="search-result">
          <pb-multi-item :name="name" :result="result" :scope="scope"></pb-multi-item>
        </li>
      </ul>
      <p v-if="hasPublicBodies">
        <a class="btn btn-primary" href="#step-request" @click="setStepRequest">
          Continue
        </a>
      </p>
    </div>
  </div>
</template>

<script>

import {mapMutations} from 'vuex'
import {SET_STEP_REQUEST, ADD_PUBLICBODY_ID} from '../store/mutation_types'

import PBListMixin from '../lib/pb-list-mixin'

import PbMultiItem from './pb-multi-item'

export default {
  name: 'pb-multi-list',
  props: ['name', 'scope', 'i18n'],
  mixins: [PBListMixin],
  methods: {
    selectAll () {
      this.searchResults.forEach((r) => {
        this.addPublicBodyId({
          publicBodyId: r.id,
          scope: this.scope
        })
      })
    },
    ...mapMutations({
      setStepRequest: SET_STEP_REQUEST,
      addPublicBodyId: ADD_PUBLICBODY_ID
    })
  },
  components: {
    PbMultiItem
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
