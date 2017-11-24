<template>
  <div class="search-result-container">
    <p v-if="hasSearchResults">
      {{ searchResultsLength }} {{ i18n.publicBodiesFound }}
    </p>
    <div class="row" v-if="publicBody">
      <div class="col-sm-8">
        <h4 class="pb-heading">
          <a :href="publicBody.site_url">
            {{ publicBody.name }}
          </a>
        </h4>
        <small>
          {{ publicBody.jurisdiction.name }}, {{ publicBody.number_of_requests }} {{ i18n.requests }}
        </small>
      </div>
      <div class="col-sm-4">
        <a class="btn btn-primary" href="#step-request" @click="selectSearchResult" :data-pbid="publicBody.id">
          {{ i18n.makeRequest }}
        </a>
      </div>
    </div>
    <ul v-if="searchResultsLength > 0 || emptyResults" class="search-results list-unstyled">
      <li v-for="result in searchResults" class="search-result">
        <div class="row">
          <div class="col-sm-8">
            <h4 class="pb-heading">
              <a :href="result.site_url">
                {{ result.name }}
              </a>
            </h4>
            <small>
              {{ result.jurisdiction.name }}, {{ result.number_of_requests }} {{ i18n.requests }}
            </small>
          </div>
          <div class="col-sm-4">
            <a class="btn btn-primary" href="#step-request" @click="selectSearchResult" :data-pbid="result.id">
              {{ i18n.makeRequest }}
            </a>
          </div>
        </div>
      </li>
    </ul>
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
  </div>
</template>

<script>
import {mapMutations} from 'vuex'
import {SET_STEP_REQUEST, ADD_PUBLICBODY_ID} from '../store/mutation_types'

import PBListMixin from '../lib/pb-list-mixin'

export default {
  name: 'pb-action-list',
  mixins: [PBListMixin],
  props: ['name', 'scope', 'i18n'],
  methods: {
    selectSearchResult (e) {
      let pbid = e.target.dataset.pbid
      this.addPublicBodyId({
        publicbodyId: pbid,
        scope: this.scope
      })
      this.setStepRequest()
    },
    ...mapMutations({
      setStepRequest: SET_STEP_REQUEST,
      addPublicBodyId: ADD_PUBLICBODY_ID
    })
  }
}
</script>

<style scoped>
  .search-result-container {
    margin-top: 30px;
  }

  .search-result {
    border-top: 1px solid #ccc;
    padding-top: 30px;
    margin-top: 15px;
  }
  .search-result .btn {
    float: right;
  }
  .pb-heading {
    margin-bottom: 0;
  }

  .search-result:hover {
  }

</style>
