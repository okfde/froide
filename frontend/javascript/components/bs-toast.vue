<script setup>
import { inject } from 'vue'
import { vBsToast } from '../lib/vue-bootstrap'

const i18n = inject('i18n')

const props = defineProps({
  color: {
    type: String,
    default: 'body'
  }
})

const emit = defineEmits('dismiss')

let teleportTo = document.getElementById('toastContainer')

if (!teleportTo) {
  teleportTo = document.createElement('div')
  teleportTo.id = 'toastContainer'
  teleportTo.classList = 'toast-container position-fixed bottom-0 end-0 p-3'
  document.body.appendChild(teleportTo)
}
</script>

<template>
  <Teleport :to="teleportTo">
    <div v-bs-toast :class="`toast show text-bg-${props.color}`" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body">
          <slot name="body"></slot>
        </div>
        <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" :aria-label="i18n.close" @click="emit('dismiss')"></button>
      </div>
    </div> 
  </Teleport>
</template>