<script lang="ts" setup>
import { inject, ref, onMounted } from 'vue'
import BsModal from './bs-modal.vue'

const props = defineProps({
  path: { type: String, default: '' }
})

const i18n: any = inject('i18n')

const container = ref<HTMLDivElement>()
const contents = ref('')

const bsModal = ref()

const isFetching = ref(false)

const lowerHeadingLevel = (el: Element, from: number, to: number) => {
  el.querySelectorAll<HTMLHeadingElement>(`h${from}`).forEach((el) => {
    const h = document.createElement(`h${to}`)
    h.innerHTML = el.innerHTML
    el.replaceWith(h)
  })
}

const fetchContents = (url: string) => {
  isFetching.value = true
  return fetch(url)
    .then((response) => {
      if (!response.ok) {
        console.error('online help fetch error', response)
        return `<strong>${response.status} ${response.statusText}</strong>`
      }
      return response.text()
    })
    .then((response) => {
      container.value!.innerHTML = ''

      const root = document.createElement('div')
      root.innerHTML = response

      root.querySelectorAll('a').forEach((a) => {
        if (!a.target) a.target = '_blank'
      })

      // we need to adjust the lowest levels first, otherwise we would lower them multiple times
      const headlineLevels = [
        [3, 5],
        [2, 4],
        [1, 3]
      ]

      for (const [from, to] of headlineLevels) {
        lowerHeadingLevel(root, from, to)
      }

      container.value!.appendChild(root)
    })
    .catch((err) => {
      container.value!.innerHTML = 'Error: ' + err
    })
    .finally(() => {
      isFetching.value = false
    })
}

const show = (pathOrContent: string | { content: string }) => {
  if (typeof pathOrContent === 'string') {
    fetchContents(pathOrContent)
    bsModal.value.show()
  } else {
    const { content } = pathOrContent
    contents.value = content
    bsModal.value.show()
  }
}

onMounted(() => {
  if (props.path) fetchContents(props.path)
})

defineExpose({ show })
</script>

<template>
  <BsModal
    ref="bsModal"
    dialog-classes="modal-fullscreen modal-dialog-scrollable ms-auto modal-online-help"
    :body-classes="
      isFetching ? 'd-flex justify-content-center align-items-center' : ''
    "
  >
    <template #header>
      <h2 class="h5 modal-title">{{ i18n.help }}</h2>
    </template>
    <template #body>
      <span v-if="isFetching" class="spinner spinner-border" role="status">
        <span class="visually-hidden">{{ i18n.attachmentsLoading }}</span>
      </span>
      <div v-show="!isFetching" ref="container" />
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
