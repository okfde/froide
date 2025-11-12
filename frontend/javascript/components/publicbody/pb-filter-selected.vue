<template>
  <div v-if="hasValue && !valuesGrouped">
    <PbFilterBadge
      v-for="v in valueList"
      :key="v.id"
      :label="config.label"
      :value="v.label"
      :i18n="i18n"
      class="w-100"
      @remove-click="() => removeFilter(v)"
      />
  </div>
  <div v-else-if="hasValue && valuesGrouped">
    <PbFilterBadge
      v-for="group in valuesGrouped"
      :key="group.id"
      :label="config.label"
      :value="group.badgeValue"
      :i18n="i18n"
      class="w-100"
      @remove-click="() => removeFilter(group.values)"
      />
  </div>
</template>

<script>
import FilterMixin from './lib/filter-mixin'
import PbFilterBadge from './pb-filter-badge'

// above that, collapse individual value badges into one group badge
const groupedDisplayThreshold = 4
// above that, just show the group Label instead of a comma-separated list of values
const groupedCollapseLabelValuesThreshold = 8

export default {
  name: 'PbFilterSelected',
  components: { PbFilterBadge },
  props: ['globalConfig', 'config', 'i18n', 'scope', 'value', 'expanded'],
  mixins: [FilterMixin],
  computed: {
    valuesGrouped() {
      if (!this.config.groupBy) return
      if (this.valueList.length < groupedDisplayThreshold) return
      const groups = {}
      this.valueList.forEach((x) => {
        const groupId = x[this.config.groupBy]
        groups[groupId] = groups[groupId] || ({
          id: groupId,
          values: [],
          label: this.i18n['groupBy_' + groupId] || groupId,
        })
        groups[groupId].values.push(x)
      })
      for (const groupId in groups) {
        const group = groups[groupId]
        group.badgeValue = group.values.length > groupedCollapseLabelValuesThreshold
          ? group.label
          : group.values.map((v) => v.label).join(', ')
      }
      return groups
    }
  }
}
</script>

