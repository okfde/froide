<template>
  <div>
    <div class="row">
      <div v-for="item in summary" class="col-sm-6 col-md-4">
        <strong>
          {{ item.count }} {{ i18n._(item.i18nLabel, {count: item.count}) }}
          <span v-if="item.multi">multi</span>
        </strong>
        <ul class="summary-subitem-list">
          <li v-for="subitem in item.sorted">
            {{ subitem.count }} {{ subitem.label }}
          </li>
        </ul>
      </div>
    </div>
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
          let val = dimension.key(pb) || ''
          let dim = dimension.id
          summary[dim] = summary[dim] || {
            count: 0,
            items: {},
            i18nLabel: dimension.i18nLabel,
            multi: dim.multi
          }
          if (!Array.isArray(val)) {
            val = [val]
          }
          val.forEach((v) => {
            summary[dim].items[v] = summary[dim].items[v] || 0
            summary[dim].items[v] += 1
          })
        }
      }
      for (let dimension of this.dimensions) {
        let dim = dimension.id
        if (summary[dim] === undefined) { continue }
        summary[dim].count = Object.keys(summary[dim].items).length
        summary[dim].sorted = []
        for (let key in summary[dim].items) {
          summary[dim].sorted.push({
            label: key === '' ? '-' : key,
            count: summary[dim].items[key]
          })
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
