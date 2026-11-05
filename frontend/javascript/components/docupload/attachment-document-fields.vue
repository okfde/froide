<script setup>
import { reactive, ref } from 'vue'
import { useGettext } from 'vuepo/vue'

import { useAttachments } from './lib/attachments'

const { gettext } = useGettext()

const { updateDocument } = useAttachments()

const { attachment } = defineProps({
  attachment: {
    type: Object,
    required: true
  }
})

const fields = reactive({
  title: attachment.document?.title,
  description: attachment.document?.description
})

const isSubmitting = ref(false)

const submitClick = () => {
  isSubmitting.value = true
  updateDocument(attachment, fields).finally(() => {
    isSubmitting.value = false
  })
}
</script>

<template>
  <div class="mb-3">
    <label
      class="form-label fw-bold"
      :for="'documentTitle' + attachment.document.id"
      >{{ gettext('Document title') }}</label
    >
    <input
      type="text"
      class="form-control"
      :id="'documentTitle' + attachment.document.id"
      :aria-describedby="'documentTitleHelp' + attachment.document.id"
      v-model="fields.title"
      :disabled="isDocumentSubmitting"
      :placeholder="gettext('e.g. Letter from date')"
    />
    <small
      :id="'documentTitleHelp' + attachment.document.id"
      class="form-text text-body-secondary"
      >{{ gettext('Give this document a proper title') }}</small
    >
  </div>
  <div class="mb-3">
    <label
      class="form-label fw-bold"
      :for="'documentDescription' + attachment.document.id"
      >{{ gettext('Description') }}</label
    >
    <textarea
      class="form-control"
      :id="'documentDescription' + attachment.document.id"
      :aria-describedby="'documentDescriptionHelp' + attachment.document.id"
      rows="4"
      v-model="fields.description"
      :disabled="isDocumentSubmitting"
    ></textarea>
    <small
      :id="'documentDescriptionHelp' + attachment.document.id"
      class="form-text text-body-secondary"
      >{{ gettext('Describe the contents of the document') }}</small
    >
  </div>
  <button
    type="button"
    @click="submitClick"
    class="btn btn-secondary"
    :disabled="isSubmitting"
  >
    {{ gettext('Save') }}
  </button>
</template>
