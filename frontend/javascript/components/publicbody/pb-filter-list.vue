<template>
  <div>
    <!-- this is the case for most PbFilterLists... -->
    <ul v-if="!config.groupBy" class="filter-list mb-0">
      <li
        v-for="item in filteredItems"
        :key="item.id"
        :class="{ active: item.isActive }">
        <div class="form-check">
          <!-- (when the parent PbFilterList is active, this child's matches will be included in the results anyway,
             hence we "auto-check" it, so state is displayed more consistently, unamiguously -->
          <input
            :type="inputType"
            :name="inputName + (parentInputName || '')"
            class="form-check-input"
            :id="item.labelId"
            @change="setFilter(item)"
            :data-test="item.isActive"
            :checked="item.isActive || (config.multi && parentActive)"
            :disabled="config.multi && parentActive"
            />
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
            :parent-active="item.isActive"
            :parent-input-name="item.labelId"
            @remove-filter="removeFilter"
            @set-filter="setFilter"
            @load-more="loadMore"
            @load-children="loadChildren"
            />
        </div>
      </li>
    </ul>
    <!-- ...this is used in PbBetaChooser for "layer"/jurisdiction -->
    <ul v-else class="list-unstyled mb-0 filter-list--grouped">
      <li
        v-for="itemGroup in itemGroups"
        :key="itemGroup.id"
        >
        <!-- special simple case for groups with one member -->
        <div
          v-if="itemGroup.items.length === 1"
          class="form-check"
          >
          <input
            :type="inputType"
            :name="inputName"
            class="form-check-input"
            :id="itemGroup.items[0].labelId"
            @change="setFilter(itemGroup.items[0])"
            :checked="itemGroup.items[0].isActive"
            />
          <label class="form-check-label text-break" :for="itemGroup.items[0].labelId">
            {{ itemGroup.items[0].label }}
          </label>
          <small v-if="itemGroup.items[0].count">({{ itemGroup.items[0].count }})</small>
        </div>
        <!-- groups with multiple members will have a "smart check all" checkbox... -->
        <div v-else>
          <div class="form-check">
            <!-- ...which can be indeterminate. Als note the itemGroupSelect here... -->
            <input
              :type="inputType"
              :name="inputName"
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
              ><span class="visually-hidden">{{ i18n.toggleCollapse }}</span></i>
          </div>
          <div class="collapse" :id="'collapse_' + itemGroup.id">
            <ul class="list-unstyled mb-0 ps-4">
              <!-- ...which will affect all the nested/indented group members right here.
                Note that we don't use a nested/recursive PbFilterList here, there is only "depth=1". -->
              <li v-for="item in itemGroup.items" :key="item.id">
                <div class="form-check">
                  <input
                    :type="inputType"
                    :name="inputName"
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
  props: ['config', 'items', 'i18n', 'scope', 'value', 'hasMore', 'parentActive', 'parentInputName'],
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
    inputType() {
      return this.config.multi ? 'checkbox' : 'radio'
    },
    inputName() {
      return 'pb_filter_' + this.config.key
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
      // uncollapse
      if (item.children && item.children.length > 0 && !item.subItems) {
        this.loadChildren(item)
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
