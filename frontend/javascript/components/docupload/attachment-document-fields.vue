<script setup>

import { inject, reactive, ref } from 'vue'

import { useAttachments } from './lib/attachments';

const i18n = inject('i18n')

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
  updateDocument(attachment, fields)
    .finally(() => {
      isSubmitting.value = false
    })
}

</script>

<template>
  <div class="mb-3">
    <label
      class="form-label fw-bold"
      :for="'documentTitle' + attachment.document.id"
      >{{ i18n.documentTitle }}</label>
    <input
      type="text"
      class="form-control"
      :id="'documentTitle' + attachment.document.id"
      v-model="fields.title"
      :disabled="isDocumentSubmitting"
      :placeholder="i18n.documentTitlePlaceholder"
      />
    <small class="form-text text-body-secondary">{{ i18n.documentTitleHelp }}</small>
  </div>
  <div class="mb-3">
    <label
      class="form-label fw-bold"
      :for="'documentDescription' + attachment.document.id"
      >{{ i18n.description }}</label>
    <textarea
      class="form-control"
      :id="'documentDescription' + attachment.document.id"
      rows="4"
      v-model="fields.description"
      :disabled="isDocumentSubmitting"
      ></textarea>
    <small class="form-text text-body-secondary">{{ i18n.descriptionHelp }}</small>
  </div>
  <button
    type="button"
    @click="submitClick"
    class="btn btn-secondary"
    :disabled="isSubmitting"
    >
    {{ i18n.save }}
  </button>
</template>