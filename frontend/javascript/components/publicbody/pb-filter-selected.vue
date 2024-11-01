<template>
  <div v-if="hasValue">
    <div v-for="v in valueList" :key="v.id" class="filter-badge">
      <span class="text-truncate">{{ v.label }}</span>
      <button
        @click="removeFilter(v)"
        type="button"
        class="btn btn-close btn-close-white"
        aria-label="Close"
      ></button>
    </div>
  </div>
</template>

<script>
import FilterMixin from './lib/filter-mixin'

export default {
  name: 'PbFilterSelected',
  props: ['globalConfig', 'config', 'i18n', 'scope', 'value', 'expanded'],
  mixins: [FilterMixin]
}
</script>

<style lang="scss" scoped>
@import '../../../styles/variables';

.filter-badge {
  background-color: $primary;
  color: #fff;
  display: block;
  border-radius: 4px;
  padding: 0.25rem 0.5rem;
  margin: 0.5rem 0;
  display: flex;
  justify-content: space-between;
}
</style>
