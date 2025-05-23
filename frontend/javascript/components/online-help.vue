<script setup>
import { inject, ref, onMounted } from 'vue'
import BsModal from './bs-modal.vue'

const i18n = inject('i18n')

const props = defineProps({
  path: String
})

const contents = ref('')

const bsModal = ref()

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
  bsModal.value.show()
}

onMounted(() => {
  if (props.path) fetchContents(props.path)
})

defineExpose({
  show
})
</script>

<template>
  <BsModal
    ref="bsModal"
    dialog-classes="modal-fullscreen modal-dialog-scrollable ms-auto modal-online-help"
    content-classes="bg-warning-subtle"
  >
    <template #header>
      <h5 class="modal-title">{{ i18n.help }}</h5>
    </template>
    <template #body>
      <span
        class="spinner spinner-border position-absolute top-50 start-50 translate-middle"
        v-show="isFetching"
      >
        <span class="sr-only">{{ i18n.attachmentsLoading }}</span>
      </span>
      <div v-html="contents"></div>
    </template>
  </BsModal>
</template>

<style lang="scss">
// unscoped, because getting scoped to work thorugh BsModal's Teleport is hard or not yet possible
// https://github.com/vuejs/core/issues/2669

// makes this into a "right-sidebar-like"
.modal-online-help.modal-fullscreen.ms-auto {
  max-width: 30em;
}
</style>
