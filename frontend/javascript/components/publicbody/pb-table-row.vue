<template>
  <tr @click="toggleRow" class="row-data" :class="{'row-active': value }">
    <td>
      <input type="checkbox" :data-label="row.name" :value="row.id" v-model="value"/>
    </td>
    <td>
      {{ row.name }}
      <a :href="row.site_url" @click.stop class="info-link" target="_blank">
        <span class="sr-only">Details</span><i class="fa fa-info-circle" aria-hidden="true"></i>
      </a>
    </td>
    <td v-if="hasJurisdiction">
      {{ row.jurisdiction.name }}
    </td>
    <td v-if="hasClassification">
      {{ (row.classification && row.classification.name) || '-' }}
    </td>
    <td v-if="hasCategories">
      {{ rowCategories }}
    </td>
  </tr>
</template>

<script>

export default {
  name: 'pb-table-row',
  props: ['name', 'row', 'selected',  'headers'],
  computed: {
    rowCategories () {
      return this.row.categories.map((x) => x.name).join(', ')
    },
    value: {
      get () {
        return this.selected
      },
      set (value) {
        this.$emit('update:row', {id: this.row.id, value: value})
      }
    },
    hasJurisdiction () {
      return this.headers.filter((x) => x.key === 'jurisdiction').length > 0
    },
    hasClassification () {
      return this.headers.filter((x) => x.key === 'classification').length > 0
    },
    hasCategories () {
      return this.headers.filter((x) => x.key === 'categories').length > 0
    }
  },
  methods: {
    toggleRow (event) {
      this.value = !this.value
    }
  }
}
</script>

<style lang="scss" scoped>
  @import "../../../styles/variables";

  .row-data {
    cursor: pointer;
  }

  .row-active {
    background-color: lighten($success, 50%);
  }

  .info-link {
    color: $gray-500;
    &:hover {
      color: $link-color;
    }
  }

</style>
