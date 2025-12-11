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
  <span class="badge bg-secondary-subtle text-body d-flex fs-6 text-wrap gap-2 justify-content-between">
    <div class="text-start lh-sm">
      <small class="text-body-secondary">{{ label }}</small><br/>
      {{ value }}
    </div>
    <button
      @click="emit('removeClick')"
      type="button"
      class="btn btn-close align-self-center"
      :aria-label="i18n.remove"></button>
  </span>
</template>
