<template>
  <div if="hasValue">
    <div v-for="v in valueList" :key="v" class="filter-badge">
      {{ v }}
      <i  @click="removeFilter(v)" class="remove-filter fa fa-close" aria-hidden="true"></i>
    </div>
  </div>
</template>

<script>
import FilterMixin from '../../lib/filter-mixin'

export default {
  name: 'pb-filter-selected',
  props: ['globalConfig', 'config', 'i18n', 'scope', 'value', 'expanded'],
  mixins: [FilterMixin],
}
</script>

<style lang="scss" scoped>
  @import "../../../styles/variables";

  .filter-badge {
    background-color: $primary;
    color: #fff;
    display: block;
    border-radius: 4px;
    padding: 0.25rem 0.5rem;
    margin: 0.5rem 0;

    .remove-filter {
      color: #eee;
      padding: 0.25rem 0.5rem;
      float: right;
      &:hover {
        color: #fff;
      }
      cursor: pointer;
    }

  }
</style>
