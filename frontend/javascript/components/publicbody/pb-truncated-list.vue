<template>
  <slot
    v-for="(pb, index) in shownPublicBodies"
    :key="pb.id"
    :pb="pb"
    :index="index"
  />
  <slot v-if="truncated" name="truncation" :count="publicBodies.length">
    {{ i18n._('publicBodiesCount', { count: publicBodies.length }) }}
  </slot>
</template>

<script>
export default {
  name: 'PbTruncatedList',
  props: {
    publicBodies: {
      type: Array,
      required: true
    },
    i18n: {
      type: Object,
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
  }
}
</script>
