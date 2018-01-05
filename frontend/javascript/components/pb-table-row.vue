<template>
  <tr @click="toggleRow" class="row-data" :class="{'row-active': value }">
    <td>
      <input type="checkbox" :data-label="row.name" :value="row.id" v-model="value"/>
    </td>
    <td>
      {{ row.name }}
    </td>
    <td>
      {{ row.jurisdiction.name }}
    </td>
    <td>
      {{ (row.classification && row.classification.name) || '-' }}
    </td>
    <td>
      {{ rowCategories }}
    </td>
  </tr>
</template>

<script>

import {mapGetters, mapMutations} from 'vuex'
import {ADD_PUBLICBODY_ID, REMOVE_PUBLICBODY_ID} from '../store/mutation_types'

export default {
  name: 'pb-table-row',
  props: ['name', 'row', 'scope'],
  computed: {
    rowCategories () {
      return this.row.categories.map((x) => x.name).join(', ')
    },
    value: {
      get () {
        return this.isPublicBodySelectedByScope(this.scope, this.row.id)
      },
      set (value) {
        if (value) {
          this.addPublicBodyId({
            publicBodyId: this.row.id,
            scope: this.scope
          })
        } else {
          this.removePublicBodyId({
            publicBodyId: this.row.id,
            scope: this.scope
          })
        }
      }
    },
    ...mapGetters([
      'isPublicBodySelectedByScope'
    ])
  },
  methods: {
    toggleRow (event) {
      this.value = !this.value
    },
    selectSearchResult (event) {
      this.value = event.target.value
    },
    ...mapMutations({
      addPublicBodyId: ADD_PUBLICBODY_ID,
      removePublicBodyId: REMOVE_PUBLICBODY_ID
    })
  }
}
</script>

<style lang="scss" scoped>
  @import "../../styles/variables";

  .row-data {
    cursor: pointer;
  }

  .row-active {
    background-color: lighten($success, 50%);
  }
</style>
