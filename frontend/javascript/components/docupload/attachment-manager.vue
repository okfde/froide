<script setup>

import FileUploader from '../upload/file-uploader.vue'
import ImagesConverter from '../docupload/images-converter.vue'
import AttachmentsTable from './attachments-table.vue'
import { useI18n } from '../../lib/i18n'
import { useAttachments } from './lib/attachments'
// import { useAttachmentsStore } from './lib/attachments-store'
// import { pinia } from '../../lib/pinia'

import { computed, onMounted, provide } from 'vue'

const props = defineProps(['config', 'message'])

// const attachments = useAttachmentsStore(pinia)

const { attachments, addFromUppy, refresh } = useAttachments({
  urls: {
    ...props.config.url,
    getAttachment: props.config.url.getAttachment.replace('/0/', '/') +
      '?belongs_to=' +
      props.message.id,
  },
  csrfToken: document.querySelector('[name=csrfmiddlewaretoken]').value,
})

const { i18n } = useI18n(props.config)
provide('i18n', i18n)
provide('config', props.config)

/* const { setup, attachments, addFromUppy } = useAttachments({
  url: props.config.url.getAttachment.replace('/0/', '/') +
    '?belongs_to=' +
    props.message.id,
  csrfToken: document.querySelector('[name=csrfmiddlewaretoken]').value,
  onDocumentsAdded: todo,
  onImagesAdded: todo,
}) */

const tablesCardsThreshold = 5
const tablesCards = computed(() => [attachments.approved, attachments.notApproved, attachments.irrelevant].every(_ => _.length <= tablesCardsThreshold))

onMounted(() => refresh())

</script>

<template>
  <hr/>
  ATTACHMENT MANAGER
  <div :class="{ 'p-3': tablesCards, 'bg-body-tertiary': tablesCards }">
    <attachments-table actions multi-actions :subset="attachments.approved" :cards="tablesCards" />
  </div>
  <div :class="tablesCards ? 'p-3 bg-body-tertiary my-3' : ''">
    <h2 v-if="config.request_public">Nicht freigegeben</h2>
    <h2 v-else>Nicht öffentlich</h2>
    <attachments-table actions multi-actions :subset="attachments.notApproved" :cards="tablesCards" />
  </div>
  <h2>Unwichtige Anhänge</h2>
  <attachments-table actions multi-actions :subset="attachments.irrelevant" :cards="tablesCards" />

  <file-uploader
    :config="config"
    :allowed-file-types="config.settings.allowed_filetypes"
    :auto-proceed="true"
    @upload-success="addFromUppy"
    />
  <images-converter />
  <pre>isConverting={{ attachments.isConverting }}</pre>
</template>
