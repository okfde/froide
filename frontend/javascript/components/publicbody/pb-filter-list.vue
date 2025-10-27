<template>
  <div class="filter-list-wrapper">
    <ul v-if="!config.groupBy" class="filter-list">
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
          <label class="form-check-label text-break" :for="item.labelId">
            {{ item.label }}
            <small v-if="item.subLabel" class="text-secondary d-block">{{ item.subLabel }}</small>
          </label>
          <small v-if="item.count" class="filter-list-sublabel">({{ item.count }})</small>
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
    <ul v-else class="list-unstyled filter-list--grouped">
      <li
        v-for="itemGroup in itemGroups"
        :key="itemGroup.id"
        >
        <div
          v-if="itemGroup.items.length === 1"
          class="form-check"
          >
          <input
            type="checkbox"
            class="form-check-input"
            :id="itemGroup.items[0].labelId"
            @change="setFilter(itemGroup.items[0])"
            :checked="itemGroup.items[0].isActive" />
          <label class="form-check-label text-break" :for="itemGroup.items[0].labelId">
            {{ itemGroup.items[0].label }}
          </label>
          <small v-if="itemGroup.items[0].count">({{ itemGroup.items[0].count }})</small>
        </div>
        <!--details v-else-->
        <div v-else>
          <div class="form-check">
            <input
              type="checkbox"
              class="form-check-input"
              :id="itemGroup.id"
              :checked="itemGroup.isActive"
              :indeterminate.prop="itemGroup.isActive === undefined"
              @click="itemGroupSelect(itemGroup)"
              />
            <label
              class="form-check-label text-break"
              :for="itemGroup.id"
              >{{ itemGroup.label }}</label>
            <i
              data-bs-toggle="collapse"
              :data-bs-target="'#collapse_' + itemGroup.id"
              class="fa fa-chevron-down load-children"
              role="button"
              :aria-controls="'collapse_' + itemGroup.id"
              ><!-- TODO a11y --></i>
          </div>
          <div class="collapse" :id="'collapse_' + itemGroup.id">
            <ul class="list-unstyled ps-4">
              <li v-for="item in itemGroup.items" :key="item.id">
                <div class="form-check">
                  <input
                    type="checkbox"
                    class="form-check-input"
                    :id="item.labelId"
                    @change="setFilter(item)"
                    :checked="isActive(item.id)"
                    />
                  <label class="form-check-label text-break" :for="item.labelId">
                    {{ item.label }}
                  </label>
                  <small v-if="item.count">({{ item.count }})</small>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </li>
    </ul>
    <div v-if="hasMore" class="pb-4">
      <button
        type="button"
        class="btn btn-link btn-sm"
        @click.prevent="loadMore"
        >{{ i18n.loadMore }}</button>
    </div>
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
    itemGroups() {
      if (!this.config.groupBy) return
      // const groupIds = new Set(this.items.map((x) => x[this.config.groupBy]))
      const groups = {}
      this.items.forEach((x) => {
        const groupId = x[this.config.groupBy]
        groups[groupId] = groups[groupId] || ({
          id: this.config.key + '_' + groupId,
          items: [],
          label: this.i18n['groupBy_' + groupId] || groupId,
          isActive: false,
        })
        groups[groupId].items.push(x)
      })
      for (const groupId in groups) {
        const group = groups[groupId]
        const itemsActive = group.items.map((x) => this.isActive(x.id))
        if (itemsActive.every((x) => x)) {
          group.isActive = true
        } else if (itemsActive.some((x) => x)) {
          group.isActive = undefined
        }
      }
      return groups
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
    itemGroupSelect(itemGroup) {
      // if all selected...
      if (itemGroup.isActive === true) {
        // unselect all; n.b. ids, not objects
        // const allActive = itemGroup.items.map((x) => x.id)
        this.$emit('removeFilter', itemGroup.items)
      } else {
        // select unselected (may be all); n.b. objects, not ids
        const notActive = itemGroup.items.filter((x) => !this.isActive(x))
        this.$emit('setFilter', notActive)
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
