<template>
  <div>
    <div v-if="publicBody && !hasSearchResults" class="search-result">
      <div class="form-check">
        <input
          v-model="value"
          class="form-check-input"
          type="radio"
          :data-label="publicBody.name"
          :name="name"
          :value="publicBody.id" />
        <label class="form-check-label">
          {{ publicBody.name }}
          <small>
            {{ publicBody.jurisdiction.name }}
          </small>
        </label>
      </div>
    </div>
    <ul v-if="searchResults.length > 0" class="search-results list-unstyled">
      <li
        v-for="result in searchResults"
        :key="result.id"
        class="search-result">
        <div class="form-check">
          <!-- TODO: escape could/should "reset" -->
          <input
            v-model="value"
            type="radio"
            class="form-check-input"
            :data-label="result.name"
            :data-resource-uri="result.resource_uri"
            :name="name"
            :value="result.id"
            :id="`pb_${this.scope}_${result.id}`"
            tabindex="0"
            @change="selectSearchResult($event, false)"
            @click="selectSearchResult($event, true)"
            @keydown.enter.prevent="clear"
            @keydown.space.prevent="clear" />
          <!-- clearDelayed prevents in some browser the change on input not firing -->
          <label
            class="form-check-label"
            @click="clearDelayed"
            :for="`pb_${this.scope}_${result.id}`">
            {{ result.name }}
            <small>
              {{ result.jurisdiction.name }}
            </small>
          </label>
        </div>
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
      }
    }
  },
  methods: {
    selectSearchResult(event, doClear) {
      // keyboard navigation (arrow keys) can send a fake click event
      // it can be distinguished by detail attribute,
      // which usually holds the amount of clicks (e.g. 2 for a double click)
      // should this not suffice, we could check clientX === 0
      if (event.type === 'click' && event.detail === 0) {
        return
      }
      this.value = event.target.value
      this.$emit('update', {
        id: event.target.value,
        resourceUri: event.target.dataset.resourceUri
      })
      if (doClear) this.clear()
    },
    clear() {
      this.clearSearchResults({ scope: this.scope })
    },
    clearDelayed() {
      setTimeout(() => this.clear(), 100)
    }
  }
}
</script>

<style lang="scss" scoped>
@import '../../../styles/variables';

.search-results {
  overflow-y: auto;
  outline: 1px solid #aaa;
}

.search-result {
  cursor: pointer;
}

.search-result:hover {
  background-color: var(--#{$prefix}light-bg-subtle);
  color: var(--#{$prefix}light-text-emphasis);
}

.search-result.selected {
  background-color: var(--#{$prefix}body-secondary-bg);
}

.form-check label {
  display: block;
  cursor: pointer;
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
