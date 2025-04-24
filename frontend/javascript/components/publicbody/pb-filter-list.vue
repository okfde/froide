<template>
  <div class="filter-list-wrapper">
    <ul class="filter-list">
      <li
        v-for="item in filteredItems"
        :key="item.id"
        :class="{ active: item.isActive }">
        <div class="form-check">
          <input
            type="checkbox"
            class="form-check-input"
            :id="item.labelId"
            @change="setFilter(item)"
            :data-test="item.isActive"
            :checked="item.isActive" />
          <label class="form-check-label" :for="item.labelId">
            {{ item.label }}
          </label>
          <small v-if="item.count">({{ item.count }})</small>
          <i
            v-if="item.children && item.children.length > 0 && !item.subItems"
            class="fa fa-chevron-down load-children"
            @click="loadChildren(item)"></i>

          <pb-filter-list
            v-if="item.subItems && item.subItems.length > 0"
            :config="config"
            :i18n="i18n"
            :scope="scope"
            :value="value"
            :items="item.subItems"
            @remove-filter="removeFilter"
            @set-filter="setFilter"
            @load-more="loadMore"
            @load-children="loadChildren"></pb-filter-list>
        </div>
      </li>
    </ul>
    <small v-if="hasMore" class="text-end">
      <a href="#" @click.prevent="loadMore">{{ i18n.loadMore }}</a>
    </small>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
  name: 'PbFilterList',
  props: ['config', 'items', 'i18n', 'scope', 'value', 'hasMore'],
  computed: {
    facetMap() {
      const facets = this.getScopedSearchFacets(this.scope)
      if (!facets) {
        return {}
      }
      const counts = facets[this.config.key]
      if (counts) {
        const facetMap = {}
        counts.forEach((x) => {
          facetMap[x[0]] = x[1]
        })
        return facetMap
      }
      return {}
    },
    filteredItems() {
      return this.items.map((x) => {
        x.isActive = this.isActive(x.id)
        x.labelId = `${this.config.key}_${x.id}`
        return x
      })
    },
    orderedItems() {
      const items = this.items
      if (this.facetMap) {
        return items.map((x) => {
          x.count = this.facetMap[x.id] || null
          return x
        })
      }
      return items
    },
    ...mapGetters(['getScopedSearchFacets'])
  },
  methods: {
    isActive(itemId) {
      if (this.config.multi) {
        return this.value && this.value.some((x) => itemId === x.id)
      } else {
        return this.value && itemId === this.value.id
      }
    },
    removeFilter(item) {
      this.$emit('removeFilter', item)
    },
    setFilter(item) {
      if (this.isActive(item.id)) {
        this.removeFilter(item)
        return
      }
      this.$emit('setFilter', item)
    },
    loadMore() {
      this.$emit('loadMore')
    },
    loadChildren(item) {
      this.$emit('loadChildren', item)
    }
  }
}
</script>

<style lang="scss" scoped>
@import '../../../styles/variables';
.filter-list-wrapper {
  padding-bottom: 1rem;
}
.filter-list {
  list-style: none;
  padding-left: 0;

  .active {
    font-weight: bold;
  }
  .remove-filter,
  .load-children {
    cursor: pointer;
  }
}
.load-children {
  color: #999;
}
</style>
