<script setup>

import { inject } from 'vue'

const i18n = inject('i18n')

defineProps({
  label: {
    required: true,
    type: String
  },
  value: {
    required: true,
    type: String
  }
})

const emit = defineEmits(['removeClick'])

</script>

<template>
  <span class="badge bg-secondary-subtle text-body d-inline-flex justify-content-between fs-6 text-wrap">
    <dl class="text-start">
      <dt class="text-secondary mb-1"><small>{{ label }} =</small></dt>
      <dd>{{ value }}</dd>
    </dl>
    <button
      @click="emit('removeClick')"
      type="button"
      class="btn btn-close align-self-center"
      :aria-label="i18n.close"></button>
  </span>
</template>

<style lang="scss" scoped>
@import '../../../styles/variables';

dl,
dt,
dd {
  margin: 0;
  font-weight: inherit;
}

</style>