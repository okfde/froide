<template>
  <div class="row">
    <div class="col-md-12">
      <div v-if="hasResources || hasSimilarRequests" class="card mb-3">
        <h5 class="card-header">
          {{ i18n.similarExist }}
        </h5>
        <div class="card-body">
          <div class="row">
            <div v-show="hasResources" class="col-md-6">
              <h6>
                {{ i18n.relevantResources }}
              </h6>
              <ul>
                <li v-if="publicBody?.url">
                  <a :href="publicBody.url" target="_blank" rel="noopener">
                    {{ i18n.officialWebsite }} {{ publicBody.name }}
                  </a>
                </li>
              </ul>
            </div>
            <div v-show="hasSimilarRequests" class="col-md-6">
              <h6>
                {{ i18n.similarRequests }}
              </h6>
              <ul class="similar-requests">
                <li v-for="req in similarRequests" :key="req.url">
                  <a :href="req.url" target="_blank">
                    {{ req.title }}
                  </a>
                </li>
              </ul>
              <p v-if="moreSimilarRequestsAvailable">
                <a :href="searchUrl" target="_blank">
                  {{ i18n.moreSimilarRequests }}
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import debounce from 'lodash.debounce'

import { FroideAPI } from '../../lib/api'
import I18nMixin from '../../lib/i18n-mixin'

const MAX_SIMILAR = 5

export default {
  name: 'SimilarRequests',
  props: ['config', 'publicbodies', 'subject'],
  mixins: [I18nMixin],
  data() {
    return {
      similarRequests: [],
      searches: {},
      moreSimilarRequestsAvailable: false
    }
  },
  created() {
    this.search = new FroideAPI(this.config)
    this.runSearch()
  },
  computed: {
    hasResources() {
      return this.publicBody && this.publicBody.url
    },
    hasSimilarRequests() {
      return this.similarRequests.length > 0
    },
    searchUrl() {
      return this.config.url.search + '?q=' + encodeURIComponent(this.subject)
    },
    debouncedSearch() {
      return debounce(this.runSearch, 1000)
    },
    publicBody() {
      return this.publicbodies[0]
    }
  },
  methods: {
    runSearch() {
      if (!this.subject) {
        return
      }
      if (this.searches[this.subject] !== undefined) {
        if (this.searches[this.subject] !== false) {
          this.similarRequests = this.searches[this.subject]
        }
        return
      }
      this.searches[this.subject] = false
      ;((subject) => {
        this.search.searchFoiRequests(subject).then((result) => {
          this.moreSimilarRequestsAvailable = result.length > MAX_SIMILAR
          this.similarRequests = result.slice(0, MAX_SIMILAR)
          this.searches[subject] = result
        })
      })(this.subject)
    }
  },
  watch: {
    subject: function () {
      this.debouncedSearch()
    }
  }
}
</script>
