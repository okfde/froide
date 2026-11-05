<template>
  <div class="search-result-container">
    <h3 v-if="searchResultsLength > 0 || emptyResults" class="visually-hidden">
      {{ gettext('Search results') }}
    </h3>
    <ul
      v-if="searchResultsLength > 0 || emptyResults"
      class="search-results list-unstyled"
    >
      <li
        v-for="result in searchResults"
        :key="result.id"
        class="search-result"
        @click.prevent="selectSearchResult(result.id)"
      >
        <div class="row">
          <div class="col-sm-8">
            <h4 class="pb-heading">
              {{ result.name }}
            </h4>
            <small>
              {{ result.jurisdiction.name }},
              {{ requestCount(result.number_of_requests) }}
            </small>
          </div>
          <div class="col-sm-4">
            <a
              class="btn btn-primary"
              :href="getMakeRequestURLForResult(result)"
              :aria-label="gettext`Make request to ${result.name}`"
              @click.prevent="selectSearchResult(result.id)"
            >
              {{ gettext('Make request') }}
            </a>
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>

<script>
import { mapMutations } from 'vuex'
import { t } from 'vuepo'
import { translateMixin } from 'vuepo/vue'
import { SET_PUBLICBODY_ID } from '../../store/mutation_types'

import PBListMixin from './lib/pb-list-mixin'

export default {
  name: 'PbActionList',
  mixins: [translateMixin, PBListMixin],
  emits: ['stepNext'],
  props: ['name', 'scope', 'config'],
  methods: {
    requestCount(count) {
      return this.npgettext('js', 'one request', t`${count} requests`, count)
    },
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
  margin-top: 1rem;
  padding-top: 1rem;
  cursor: pointer;

  &:not(:first-child) {
    border-top: 1px solid $gray-300;
  }

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
