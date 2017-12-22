<template>
  <div>
    {{ i18n._('publicBodiesCount', {count: publicBodies.length}) }}
    <ul>
      <li v-for="item in summary">
        <strong>
          {{ item.count }} {{ i18n._(item.i18nLabel, {count: item.count}) }}
        </strong>
        <ul class="summary-subitem-list">
          <li v-for="subitem in item.sorted">
            {{ subitem.count }} {{ subitem.label }}
          </li>
        </ul>
      </li>
    </ul>
  </div>
</template>

<script>
import {mapGetters} from 'vuex'

export default {
  name: 'pb-summary',
  props: ['scope', 'dimensions', 'i18n'],
  computed: {
    summary () {
      let summary = {}
      for (let pb of this.publicBodies) {
        for (let dimension of this.dimensions) {
          let val = dimension.key(pb)
          let dim = dimension.id
          summary[dim] = summary[dim] || {
            count: 0, items: {}, i18nLabel: dimension.i18nLabel
          }
          summary[dim].items[val] = summary[dim].items[val] || 0
          summary[dim].items[val] += 1
        }
      }
      for (let dimension of this.dimensions) {
        let dim = dimension.id
        if (summary[dim] === undefined) { continue }
        summary[dim].count = Object.keys(summary[dim].items).length
        summary[dim].sorted = []
        for (let key in summary[dim].items) {
          summary[dim].sorted.push({label: key, count: summary[dim].items[key]})
        }
        summary[dim].sorted.sort((a, b) => {
          if (a.count === b.count) {
            if (a.label > b.label) return 1
            if (a.label < b.label) return -1
            return 0
          }
          // sort highest count up
          if (a.count > b.count) return -1
          return 1
        })
      }
      return summary
    },
    publicBodies () {
      return this.getPublicBodiesByScope(this.scope)
    },
    ...mapGetters([
      'getPublicBodiesByScope'
    ])
  }
}
</script>

<style scoped>
  .summary-subitem-list {
    max-height: 200px;
    overflow-y: scroll;
  }
</style>
