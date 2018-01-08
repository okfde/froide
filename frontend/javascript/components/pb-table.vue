<template>
  <table class="table table-hover table-responsive">
    <thead>
      <tr>
        <th>
          <input v-if="options.selectAllCheckbox" type="checkbox" v-model="selectAllRows"/>
        </th>
        <th v-for="header in headers" :class="header.class">
          {{ header.label }}
          <i v-if="options.sortableHeader && header.sortKey" class="sort-control fa" :class="{'fa-sort-alpha-asc': sortOrder > 0, 'fa-sort-alpha-desc': sortOrder < 0, 'sort-control--active': sortHeader === header.label}" @click="changeSort(header.label)"></i>
        </th>
      </tr>
    </thead>
    <tbody>
      <pb-table-row v-for="row in sortedRows" :key="row.id" :name="name" :row="row" :scope="scope"></pb-table-row>
    </tbody>
  </table>
</template>

<script>
import {mapMutations} from 'vuex'
import {sortBy} from 'underscore'

import {SET_STEP_REQUEST, ADD_PUBLICBODY_ID} from '../store/mutation_types'

import PbTableRow from './pb-table-row'

export default {
  name: 'pb-table',
  props: ['name', 'headers', 'options', 'scope', 'i18n', 'rows'],
  data () {
    return {
      sortHeader: null,
      sortOrder: 1,
      allRowsSelected: false
    }
  },
  computed: {
    sortedRows () {
      let sortedRows = this.rows.slice()
      if (this.sortHeader === null) { return sortedRows }
      let header = this.headers.find((x) => x.label === this.sortHeader)
      sortedRows = sortBy(sortedRows, header.sortKey)
      if (this.sortOrder === -1) {
        sortedRows = sortedRows.reverse()
      }
      return sortedRows
    },
    selectAllRows: {
      get () {
        return this.allRowsSelected
      },
      set () {
        this.allRowsSelected = !this.allRowsSelected
        this.$emit('selectAllRows', this.allRowsSelected)
      }
    }
  },
  methods: {
    changeSort (sortHeader) {
      if (sortHeader === this.sortHeader) {
        this.sortOrder *= -1
      }
      this.sortHeader = sortHeader
    },
    ...mapMutations({
      setStepRequest: SET_STEP_REQUEST,
      addPublicBodyId: ADD_PUBLICBODY_ID
    })
  },
  components: {
    PbTableRow
  }
}
</script>

<style>
  .sort-control {
    cursor: pointer;
    opacity: 0.3;
  }
  .sort-control--active {
    opacity: 1;
  }

</style>
