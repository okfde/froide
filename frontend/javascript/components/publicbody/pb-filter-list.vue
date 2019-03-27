<template>
  <div class="filter-list-wrapper">
    <ul class="filter-list">
      <li v-for="item in filteredItems" :key="item.id" :class="{ active: isActive(item.id) }">
        <a href="#" @click.prevent="setFilter(item)">
          {{ item.label }}
        </a>
        <small v-if="item.count">({{ item.count }})</small>
        <i v-if="item.children && item.children.length > 0 && !item.subItems"
          class="fa fa-chevron-down load-children"
          @click="loadChildren(item)"
        ></i>

        <pb-filter-list v-if="item.subItems && item.subItems.length > 0"
          :config="config"
          :i18n="i18n"
          :scope="scope"
          :value="value"
          :items="item.subItems"
          @removeFilter="removeFilter"
          @setFilter="setFilter"
          @loadMore="loadMore"
          @loadChildren="loadChildren"
        ></pb-filter-list>
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
        return {}
      }
      let counts = facets[this.config.key]
      if (counts) {
        let facetMap = {}
        counts.forEach((x) => {
          facetMap[x[0]] = x[1]
        })
        return facetMap
      }
      return {}
    },
    filteredItems () {
      // if (!this.value) {
      //   return this.items.filter((x) => x.count && x.count > 0)
      // }
      return this.items
    },
    orderedItems () {
      let items = this.items
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
    isActive (itemId) {
      if (this.config.multi) {
        return this.value && this.value.some((x) => itemId === x.id)
      } else {
        return this.value && itemId === this.value.id
      }
    },
    removeFilter (item) {
      this.$emit('removeFilter', item)
    },
    setFilter (item) {
      this.$emit('setFilter', item)
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
  @import "../../../styles/variables";
  .filter-list-wrapper {
    padding-bottom: 2em;
  }
  .filter-list {
    list-style: none;
    padding-left: 0;

    li a {
      cursor: pointer;
    }

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
  .load-children {
    color: #999;
  }
</style>
