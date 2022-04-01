<template>
  <div>
    <div v-if="publicBody && !hasSearchResults" class="search-result">
      <label>
        <input
          v-model="value"
          type="radio"
          :data-label="publicBody.name"
          :name="name"
          :value="publicBody.id" />
        {{ publicBody.name }}
        <small>
          {{ publicBody.jurisdiction.name }}
        </small>
      </label>
    </div>
    <ul v-if="searchResults.length > 0" class="search-results list-unstyled">
      <li
        v-for="result in searchResults"
        :key="result.id"
        class="search-result">
        <label>
          <input
            v-model="value"
            type="radio"
            :data-label="result.name"
            :name="name"
            :value="result.id"
            @change="selectSearchResult"
            @click="selectSearchResult" />
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
import PBListMixin from './lib/pb-list-mixin'
import I18nMixin from '../../lib/i18n-mixin'

export default {
  name: 'PbResultList',
  mixins: [PBListMixin, I18nMixin],
  props: {
    name: {
      type: String,
      required: true
    },
    scope: {
      type: String,
      required: true
    },
    config: {
      type: Object,
      required: true
    }
  },
  computed: {
    value: {
      get() {
        if (this.publicBody) {
          return this.publicBody.id
        }
        return null
      },
      set(value) {
        this.setPublicBody({
          publicBody: this.getPublicBody(value),
          scope: this.scope
        })
        this.clearSearchResults({ scope: this.scope })
      }
    }
  },
  methods: {
    selectSearchResult(event) {
      this.value = event.target.value
    }
  }
}
</script>

<style lang="scss" scoped>
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

.search-result > label > small {
  margin-left: 5px;
  color: #999;
}

.search-result > label > input {
  margin: 0 5px;
}

/* Enter and leave animations can use different */
/* durations and timing functions.              */
.slide-up-enter-active {
  transition: all 0.3s ease;
  transform-origin: top;
}
.slide-up-leave-active {
  transition: all 0.8s ease-in-out;
  transform-origin: top;
}
.slide-up-enter,
.slide-up-leave-to {
  transform: scaleY(0);
  opacity: 0;
  max-height: 0;
}
</style>
