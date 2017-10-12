<template>
  <div v-if="publicbody" class="card mb-3">
    <h5 class="card-header">
      {{ i18n.similarExist }}
    </h5>
    <div class="card-body">
      <div class="row">
        <div v-show="publicbody" class="col-md-6">
          <h6>
            {{ i18n.relevantResources }}
          </h6>
          <ul>
            <li>
              <a :href="publicbody.url" target="_blank">
                Website of {{ publicbody.name }}
              </a>
            </li>
          </ul>
        </div>
        <div v-show="similarRequests.length > 0" class="col-md-6">
          <h6>
            {{ i18n.similarRequests }}
          </h6>
          <ul class="similar-requests">
            <li v-for="req in similarRequests">
              <a :href="req.url" target="_blank">
                {{ req.title }}
              </a>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>

import {debounce} from 'underscore'

import {mapGetters} from 'vuex'

import {FroideSearch} from '../lib/search'

export default {
  name: 'similar-requests',
  props: ['config', 'pbScope'],
  data () {
    return {
      similarRequests: [],
      searches: {}
    }
  },
  created () {
    this.search = new FroideSearch(this.config)
    this.$store.watch(this.$store.getters.getSubject, this.debouncedSearch)
    this.runSearch()
  },
  computed: {
    i18n () {
      return this.config.i18n
    },
    debouncedSearch () {
      return debounce(this.runSearch, 1000)
    },
    publicbody () {
      return this.getPublicBodyByScope(this.pbScope)
    },
    ...mapGetters(['getPublicBodyByScope', 'subject'])
  },
  methods: {
    runSearch () {
      if (!this.subject) {
        return
      }
      if (this.searches[this.subject] !== undefined) {
        if (this.searches[this.subject] !== false) {
          this.similarRequests = this.searches[this.subject]
        }
        return
      }
      this.searches[this.subject] = false;
      ((subject) => {
        this.search.searchFoiRequests(subject).then(result => {
          this.similarRequests = result
          this.searches[subject] = result
        })
      })(this.subject)
    }
  }
}
</script>
