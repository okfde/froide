<template>
  <div class="publicbody-chooser">
    <div class="form-search">
      <div class="input-group">
        <input type="search" v-model:value="search" class="search-public_bodies form-control" :placeholder="i18n.searchTerm" @keyup="triggerAutocomplete" @keydown.enter.prevent="triggerAutocomplete"/>
        <span class="input-group-btn">
          <button type="button" class="btn btn-success search-public_bodies-submit" @click="triggerAutocomplete">
            <span class="glyphicon glyphicon-search"></span>
            {{ i18n.search }}
          </button>
        </span>
      </div>
      <small class="search-examples help-block">
        {{ i18n.examples }}
        <a href="#" :data-search="i18n.environment" @click.prevent="fillSearch">
          {{ i18n.environment }}
        </a>
        {{ i18n.or }}
        <a href="#" :data-search="i18n.ministryOfLabour" @click.prevent="fillSearch">
          {{ i18n.ministryOfLabour}}
        </a>
      </small>
    </div>
    <div v-if="searching" class="search-spinner">
      <img :src="config.resources.spinner" alt="Loading..."/>
    </div>
    <ul v-if="searchResults.length > 0 || emptyResults || value" class="search-results list-unstyled">
      <li v-if="value" class="search-result active">
        <label>
          <input type="radio" :name="name" :data-label="label" :value="value" @change="selectSearchResult" v-model="value"/>
          {{ label }}
        </label>
      </li>
      <li v-for="result in searchResults" class="search-result">
        <label>
          <input type="radio" :data-label="result.name" :name="name" :value="result.id" @change="selectSearchResult" v-model="value"/>
          {{ result.name }}
        </label>
      </li>
      <li v-if="emptyResults" class="search-result">
        <strong>{{ i18n.noPublicBodiesFound }}</strong><br/>
        {{ i18n.missingPublicBody }}
         <a :href="help_url">
           {{ i18n.letUsKnow }}
         </a>
      </li>
    </ul>
  </div>
</template>

<script>

import {debounce} from 'underscore'
import {mapGetters, mapMutations} from 'vuex'

import {SET_PUBLICBODY} from '../store/mutation_types'
import {PublicBodySearch} from '../lib/search'

export default {
  name: 'publicbody-chooser',
  props: ['name', 'defaultlabel', 'defaultvalue', 'defaultsearch', 'config'],
  created: function () {
    if (this.defaultvalue) {
      this.$store.publicbodies = [{id: this.defaultvalue, name: this.defaultlabel}]
    }
    this.pbSearch = new PublicBodySearch(this.config)
  },
  data () {
    return {
      searchResults: [],
      publicbodies: {},
      search: this.defaultsearch,
      lastSearch: null,
      emptyResults: false,
      searching: false
    }
  },
  computed: {
    help_url () {
      return this.config.url.helpAbout
    },
    i18n () {
      return this.config.i18n
    },
    value: {
      get () {
        if (this.publicbody) {
          return this.publicbody.id
        }
      },
      set (value) {
        this.setPublicbody(this.publicbodies[value])
      }
    },
    label () {
      if (this.publicbody) {
        return this.publicbody.name
      }
    },
    debouncedAutocomplete () {
      return debounce(this.runAutocomplete, 300)
    },
    ...mapGetters([
      'publicbody'
    ])
  },
  methods: {
    fillSearch: function (event) {
      this.search = event.target.dataset.search
      this.triggerAutocomplete()
    },
    selectSearchResult: function (event) {
      this.searchResults = []
      this.setPublicbody(this.publicbodies[event.target.value])
    },
    triggerAutocomplete: function () {
      if (this.search === '') {
        this.searchResults = []
        this.emptyResults = false
        this.searching = false
      }
      if (this.search !== undefined && this.search.length < 3) {
        return
      }
      this.debouncedAutocomplete()
    },
    runAutocomplete: function () {
      if (this.search === this.lastSearch && !this.emptyResults &&
          this.searchResults.length !== 0) {
        this.searching = false
        return
      }
      this.searching = true
      this.lastSearch = this.search
      this.pbSearch.autocomplete(this.search).then((results) => {
        this.searching = false
        this.emptyResults = results.length === 0
        this.searchResults = results
        let newPublicBodies = {}
        this.searchResults.forEach(function (r) {
          newPublicBodies[r.id] = r
        })
        this.publicbodies = {
          ...this.publicbodies,
          ...newPublicBodies
        }
      }, () => {
        this.searching = false
      })
    },
    ...mapMutations({
      setPublicbody: SET_PUBLICBODY
    })
  }
}
</script>


<style scoped>
  .search-results {
      max-height: 12em;
      overflow-y: auto;
      outline: 1px solid #aaa;
  }

  .search-result {
      cursor: pointer;
  }

  .search-result:hover {
      background-color: #f5f5f5;
  }

  .search-result.active {
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

  .search-examples > a {
      color: #777;
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
