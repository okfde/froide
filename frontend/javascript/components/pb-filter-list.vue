<template>
  <div>
    <ul class="filter-list">
      <li v-for="item in items" :class="{ active: isActive(item.value) }">
        <a href="#" @click.prevent="setFilter(item.value)">
          {{ item.label }}
        </a>
        <small v-if="item.count">({{ item.count }})</small>
        <i v-if="item.children && item.children.length > 0 && !item.subItems" class="fa fa-chevron-down load-children" @click="loadChildren(item)"></i>

        <i v-if="isActive(item.value)" class="fa fa-close remove-filter" @click="removeFilter(item.value)"></i>

        <pb-filter-list v-if="item.subItems && item.subItems.length > 0" :config="config" :i18n="i18n" :scope="scope" :value="value" :items="item.subItems" @removeFilter="removeFilter" @setFilter="setFilter" @loadMore="loadMore" @loadChildren="loadChildren"></pb-filter-list>
      </li>
    </ul>
    <small v-if="hasMore" class="text-right">
      <a href="#" @click.prevent="loadMore">{{ i18n.loadMore }}</a>
    </small>
  </div>
</template>

<script>

import {mapGetters} from 'vuex'

export default {
  name: 'pb-filter-list',
  props: ['config', 'items', 'i18n', 'scope', 'value', 'hasMore'],
  computed: {
    facetMap () {
      let facets = this.getScopedSearchFacets(this.scope)
      if (!facets) {
        return null
      }
      let counts = facets[this.config.key]
      if (counts) {
        let facetMap = {}
        counts.forEach((x) => {
          facetMap[x[0]] = x[1]
        })
        return facetMap
      }
      return null
    },
    orderedItems () {
      let items = this.items
      if (this.facetMap) {
        return items.map((x) => {
          x.count = this.facetMap[x.value]
          return x
        })
      }
      return items
    },
    ...mapGetters(['getScopedSearchFacets'])
  },
  methods: {
    isActive (itemValue) {
      if (this.config.multi) {
        return this.value && this.value.some((x) => itemValue === x)
      } else {
        return itemValue === this.value
      }
    },
    removeFilter (itemValue) {
      this.$emit('removeFilter', itemValue)
    },
    setFilter (itemValue) {
      this.$emit('setFilter', itemValue)
    },
    loadMore () {
      this.$emit('loadMore')
    },
    loadChildren (item) {
      this.$emit('loadChildren', item)
    }
  }
}
</script>

<style lang="scss" scoped>
  @import "../../styles/variables";

  .filter-list {
    list-style: none;
    padding-left: 0;

    ul.filter-list {
      list-style-type: '-';
      padding-left: 15px;
    }

    .active {
      font-weight: bold;
    }
    .remove-filter, .load-children {
      cursor: pointer;
    }
  }
</style>
