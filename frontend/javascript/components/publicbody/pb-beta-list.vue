<template>
  <div class="search-result-container">
    <ul
      v-if="searchResultsLength > 0 || emptyResults"
      class="search-results list-unstyled">
      <li
        v-for="result in searchResults"
        :key="result.id"
        class="search-result"
        @click.prevent="selectSearchResult(result.id)">
        <div class="row">
          <div class="col-sm-8">
            <h4 class="pb-heading">
              {{ result.name }}
            </h4>
            <small>
              {{ result.jurisdiction.name }},
              {{ i18n._('requestCount', { count: result.number_of_requests }) }}
            </small>
          </div>
          <div class="col-sm-4">
            <a
              class="btn btn-primary"
              :href="getMakeRequestURLForResult(result)"
              @click.prevent="selectSearchResult(result.id)">
              {{ i18n.makeRequest }}
            </a>
          </div>
        </div>
      </li>
    </ul>
    <ul class="pagination" v-if="hasSearchResults && maxResultPage > 1">
      <li v-if="hasPreviousSearchResults" class="page-item">
        <a href="#" class="page-link prev" @click.prevent="getPrevious">
          <span aria-hidden="true">&laquo;</span>
          <span class="visually-hidden">{{ i18n.previous }}</span>
        </a>
      </li>
      <li v-else class="page-item disabled">
        <a class="page-link" href="#" tabindex="-1">
          <span aria-hidden="true">&laquo;</span>
          <span class="visually-hidden">{{ i18n.previous }}</span>
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
          <span class="visually-hidden">{{ i18n.next }}</span>
        </a>
      </li>
      <li v-else class="page-item disabled">
        <a class="page-link" href="#" tabindex="-1">
          <span class="visually-hidden">{{ i18n.next }}</span>
          <span aria-hidden="true">&raquo;</span>
        </a>
      </li>
    </ul>
  </div>
</template>

<script>
import { mapMutations } from 'vuex'
import {
  // SET_STEP_REQUEST,
  SET_STEP_ACCOUNT,
  SET_PUBLICBODY_ID
} from '../../store/mutation_types'

import PBListMixin from './lib/pb-list-mixin'
import I18nMixin from '../../lib/i18n-mixin'

export default {
  name: 'PbActionList',
  mixins: [PBListMixin, I18nMixin],
  props: ['name', 'scope', 'config'],
  methods: {
    selectSearchResult(pbid) {
      this.setPublicBodyId({
        publicBodyId: pbid,
        scope: this.scope
      })
      // this.setStepRequest()
      this.setStepAccount()
    },
    getMakeRequestURLForResult(result) {
      return this.config.url.makeRequestTo.replace(/0/, result.id)
    },
    ...mapMutations({
      // setStepRequest: SET_STEP_REQUEST,
      setStepAccount: SET_STEP_ACCOUNT,
      setPublicBodyId: SET_PUBLICBODY_ID
    })
  }
}
</script>

<style lang="scss" scoped>
@import '../../../styles/variables';

.search-result-container {
  margin-top: 30px;
}

.search-result {
  border-top: 1px solid #ccc;
  margin-top: 1rem;
  padding-top: 1rem;
  cursor: pointer;

  .row {
    padding: 1rem 0;
    &:hover {
      background-color: $gray-200;
    }
  }
  .btn {
    float: right;
  }
}

.pb-heading {
  margin-bottom: 0;
}
</style>
