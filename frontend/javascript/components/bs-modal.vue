<script setup lang="ts">
import { inject, nextTick, onMounted, ref, useId } from 'vue'
import { Modal } from 'bootstrap'

const props = defineProps({
  dialogClasses: {
    type: String,
    default: ''
  },
  contentClasses: {
    type: String,
    default: ''
  },
  bodyClasses: {
    type: String,
    default: ''
  },
  keepAlive: Boolean
})

const i18n: any = inject('i18n')

const modalEl = ref()
const titleId = useId()
let bsModal
let returnFocusTo: Element | null = null

// Current behavior is "keep-alive"-ish:
// modal markup will be rendered on first show,
// then hidden, not unmounted.
// Consider using a v-model here...
const doRender = ref(false)

const show = async () => {
  returnFocusTo = document.activeElement
  if (!doRender.value) {
    doRender.value = true
    await nextTick()
    initialize()
  }
  bsModal.show()
}

const hide = () => {
  bsModal.hide()
  if (!props.keepAlive) {
    doRender.value = false
  }
}

const initialize = () => {
  bsModal = new Modal(modalEl.value)
  // Bootstrap only does this for modals that are opened by a data-bs-toggle trigger
  modalEl.value.addEventListener('hidden.bs.modal', () => {
    if (returnFocusTo instanceof HTMLElement) returnFocusTo.focus()
  })
}

onMounted(() => {
  if (props.showOnMounted) {
    show()
  }
})

defineExpose({
  show,
  hide
})
</script>

<template>
  <Teleport to="body">
    <div
      ref="modalEl"
      class="modal"
      tabindex="-1"
      role="dialog"
      :aria-labelledby="titleId"
      v-if="doRender"
    >
      <div :class="'modal-dialog ' + dialogClasses">
        <div :class="'modal-content ' + contentClasses">
          <div class="modal-header">
            <div :id="titleId" class="text-break">
              <slot name="header"></slot>
            </div>
            <button
              @click="hide"
              type="button"
              class="btn-close"
              :aria-label="i18n.close"
            ></button>
          </div>
          <div :class="'modal-body ' + bodyClasses">
            <slot name="body"></slot>
          </div>
          <div v-if="$slots.footer" class="modal-footer">
            <slot name="footer"></slot>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
