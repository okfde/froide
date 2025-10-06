<template>
  <div v-if="hasValue">
    <PbFilterBadge
      v-for="v in valueList"
      :key="v.id"
      :label="config.label"
      :value="v.label"
      @remove-click="() => removeFilter(v)"
      />
  </div>
</template>

<script>
import FilterMixin from './lib/filter-mixin'
import PbFilterBadge from './pb-filter-badge'

export default {
  name: 'PbFilterSelected',
  components: { PbFilterBadge },
  props: ['globalConfig', 'config', 'i18n', 'scope', 'value', 'expanded'],
  mixins: [FilterMixin]
}
</script>

