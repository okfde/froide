<template>
  <div>
    <div class="row">
      <!-- col-12 is slightly akward on medium viewports but will make sure it is front and center -->
      <div class="col-12 col-md-4 mb-4">
        <div class="card h-100">
          <div class="card-body d-flex flex-column">
            <slot name="campaign_main"></slot>
            <div class="mt-auto">
              <button
                type="button" class="btn btn-primary w-100"
                @click="emit('stepNext')"
                >{{ i18n.makeRequest }}</button>
            </div>
          </div>
        </div>
      </div>
      <slot name="campaigns"></slot>
    </div>
  </div>
</template>

<script setup>

import { inject } from 'vue'

const i18n = inject('i18n')

defineProps({
  config: {
    type: Object,
    required: true,
  }
})

const emit = defineEmits('stepNext')

</script>