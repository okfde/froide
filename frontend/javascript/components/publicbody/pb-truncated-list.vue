<template>
  <slot
    v-for="(pb, index) in shownPublicBodies"
    :key="pb.id"
    :pb="pb"
    :index="index"
  />
  <slot v-if="truncated" name="truncation" :count="publicBodies.length">
    {{ publicBodiesCount(publicBodies.length) }}
  </slot>
</template>

<script>
import { t } from 'vuepo'
import { translateMixin } from 'vuepo/vue'

export default {
  name: 'PbTruncatedList',
  mixins: [translateMixin],
  props: {
    publicBodies: {
      type: Array,
      required: true
    },
    // Truncate once there are more than `threshold` public bodies...
    threshold: {
      type: Number,
      default: 5
    },
    // ...and then only show the first `showCount` of them.
    showCount: {
      type: Number,
      default: 3
    }
  },
  computed: {
    truncated() {
      return this.publicBodies.length > this.threshold
    },
    shownPublicBodies() {
      if (!this.truncated) {
        return this.publicBodies
      }
      return this.publicBodies.slice(0, this.showCount)
    }
  },
  methods: {
    publicBodiesCount(count) {
      return this.ngettext('one public body', t`${count} public bodies`, count)
    }
  }
}
</script>
