<script setup>

import { inject, ref } from 'vue'
import BsModal from '../bs-modal.vue'
import PdfRedaction from '../redaction/pdf-redaction.vue'

const i18n = inject('i18n')
const config = inject('config')

const emit = defineEmits(['uploaded'])

const modal = ref()

const { attachment } = defineProps({
  attachment: {
    type: Object,
    required: true
  },
})

const uploaded = () => {
  modal.value.hide()
  emit('uploaded')
}

const show = () => {
  modal.value.show()
}

defineExpose({
  show
})
</script>

<template>
  <BsModal
    ref="modal"
    :key="attachment?.id"
    dialog-classes="modal-dialog-scrollable ms-auto modal-xl modal-fullscreen-lg-down"
    content-classes="h-100"
    body-classes="p-0"
    >
    <template #header>
      <h5 class="modal-title">
        {{ i18n.redact }}, {{ attachment.name }}
      </h5>
    </template>
    <template #body>
      <PdfRedaction
        ref="pdfRedaction"
        :pdf-path="attachment.file_url"
        :attachment-id="attachment.id"
        :attachment-url="attachment.anchor_url"
        :auto-approve="true"
        :post-url="
          config.url.redactAttachment.replace(
            '/0/',
            '/' + attachment.id + '/'
          )
        "
        :minimal-ui="true"
        :no-redirect="true"
        :can-publish="true"
        :config="config"
        @uploaded="uploaded"
        ></PdfRedaction>
    </template>
  </BsModal>
</template>