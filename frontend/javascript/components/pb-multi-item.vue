<template>
  <label>
    <input type="checkbox" :data-label="result.name" :name="name" :value="result.id" v-model="value"/>
    {{ result.name }}
    <small>
      {{ result.jurisdiction.name }}
    </small>
  </label>
</template>

<script>

import {mapGetters, mapMutations} from 'vuex'
import {ADD_PUBLICBODY_ID, REMOVE_PUBLICBODY_ID} from '../store/mutation_types'

export default {
  name: 'pb-multi-item',
  props: ['name', 'result', 'scope'],
  computed: {
    value: {
      get () {
        return this.isPublicBodySelectedByScope(this.scope, this.result.id)
      },
      set (value) {
        if (value) {
          this.addPublicBodyId({
            publicBodyId: this.result.id,
            scope: this.scope
          })
        } else {
          this.removePublicBodyId({
            publicBodyId: this.result.id,
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
