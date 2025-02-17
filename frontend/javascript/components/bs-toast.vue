<script setup>
import { vBsToast } from '../lib/vue-bootstrap'

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
    <div v-bs-toast class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="toast-body">
        <slot name="body"></slot>
      </div>
    </div> 
  </Teleport>
</template>