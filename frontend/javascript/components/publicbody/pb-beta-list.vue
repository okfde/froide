<template>
  <div class="search-result-container">
    <h3 v-if="searchResultsLength > 0 || emptyResults" class="visually-hidden">{{ i18n.searchResults }}</h3>
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
  </div>
</template>

<script>
import { mapMutations } from 'vuex'
import {
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
      this.$emit('stepNext')
    },
    getMakeRequestURLForResult(result) {
      return this.config.url.makeRequestTo.replace(/0/, result.id)
    },
    ...mapMutations({
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
      background-color: var(--bs-secondary-bg);
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
