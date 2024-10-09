<script setup>
import { ref, onMounted } from 'vue'
import { Modal } from 'bootstrap'

const props = defineProps({
  path: String
})

const contents = ref('')

// "Vue3 Bootstrap Modal" adapted from https://stackoverflow.com/a/71461086/629238
// this could be probably spun out into a reusable component
const modalEl = ref()
let bsModal

const isFetching = ref(false)

const fetchContents = (url) => {
  isFetching.value = true
  return fetch(url)
    .then((response) => {
      if (!response.ok) {
        console.error('online help fetch error', response)
        return `<h1>${response.status} ${response.statusText}</h1>`
      }
      return response.text()
    })
    .then((response) => {
      contents.value = response
    })
    .catch((err) => {
      contents.value = 'Error: ' + err
    })
    .finally(() => {
      isFetching.value = false
    })
}

const show = (path) => {
  fetchContents(path)
  bsModal.show()
}

const hide = () => {
  bsModal.hide()
}

onMounted(() => {
  bsModal = new Modal(modalEl.value)
  if (props.path) fetchContents(props.path)
})

defineExpose({
  show
})
</script>

<template>
  <Teleport to="body">
    <div
      ref="modalEl"
      class="modal"
      tabindex="-1"
      role="dialog"
      id="onlinehelp-modal">
      <div
        class="modal-dialog modal-fullscreen modal-dialog-scrollable ms-auto"
        role="document">
        <div class="modal-content bg-warning-subtle">
          <div class="modal-header">
            <h5 class="modal-title">Hilfe</h5>
            <button
              @click="hide"
              type="button"
              class="btn-close"
              aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <span
              class="spinner spinner-border position-absolute top-50 start-50 translate-middle"
              v-show="isFetching" />
            <div v-html="contents"></div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style lang="scss" scoped>
// makes this into a "right-sidebar-like"
.modal-fullscreen.ms-auto {
  max-width: 30em;
}
</style>
