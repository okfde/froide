<template>
  <div>
    <h5>{{ config.label }}</h5>
    <ul class="filter-list">
      <li v-for="item in items" :class="{ active: item.value == value }">
        <a href="#" @click.prevent="setFilter(item.value)">
          {{ item.label }}
        </a>
        <i v-if="item.value == value" class="fa fa-close remove-filter" @click="setFilter(null)"></i>
      </li>
    </ul>
  </div>
</template>

<script>

export default {
  name: 'pb-filter',
  props: ['config', 'value'],
  created () {
    this.config.getItems().then((items) => {
      if (this.config.itemFilter) {
        items = items.filter(this.config.itemFilter)
      }
      if (this.config.itemMap) {
        items = items.map(this.config.itemMap)
      }
      this.items = items
    })
  },
  data () {
    return {
      items: []
    }
  },
  methods: {
    setFilter (item) {
      this.$emit('update', this.config, item)
    }
  }
}
</script>

<style lang="scss" scoped>
  @import "../../styles/variables";

  .filter-list {
    list-style: none;
    padding-left: 0;
    max-height: 210px;
    overflow-y: auto;

    @include media-breakpoint-up(md) {
      max-height: none
    }

    .active {
      font-weight: bold;
    }
    .remove-filter {
      cursor: pointer;
    }
  }
</style>
