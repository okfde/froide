<template>
  <div>
    <div class="row">
      <!-- col-12 is slightly akward on medium viewports but will make sure it is front and center -->
      <div class="col-12 col-md-4 mb-4 d-flex">
        <div class="d-flex flex-column border border-2 border-light h-100 p-3">
          <slot name="campaign_main" />
          <div class="mt-auto">
            <button
              type="button"
              class="btn btn-primary w-100"
              @click="emit('stepNext')"
            >
              {{ i18n.makeRequest }}
            </button>
          </div>
        </div>
      </div>
      <slot name="campaigns" />
    </div>
  </div>
</template>

<script setup>
import { inject } from 'vue'

const i18n = inject('i18n')

defineProps({
  config: {
    type: Object,
    required: true
  }
})

const emit = defineEmits('stepNext')
</script>

<style lang="scss" scoped>
:deep(.campaign-logo) {
  max-height: 6em;
}

:deep(ul) {
  padding-left: 1rem;
}
</style>
