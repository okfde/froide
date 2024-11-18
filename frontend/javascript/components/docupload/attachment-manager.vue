<script setup>

import FileUploader from '../upload/file-uploader.vue'
import ImagesConverter from '../docupload/images-converter.vue'
import { useAttachments } from './lib/attachments'
// import { useAttachmentsStore } from './lib/attachments-store'
// import { pinia } from '../../lib/pinia'

import { onMounted } from 'vue'

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



/* const { setup, attachments, addFromUppy } = useAttachments({
  url: props.config.url.getAttachment.replace('/0/', '/') +
    '?belongs_to=' +
    props.message.id,
  csrfToken: document.querySelector('[name=csrfmiddlewaretoken]').value,
  onDocumentsAdded: todo,
  onImagesAdded: todo,
}) */

onMounted(() => refresh())

</script>

<template>
  <hr/>
    ATTACHMENT MANAGER
    <table>
      <tr v-for="att in attachments.all" :key="att.id">
        <td>{{ att.id }}</td>
        <td>{{ att.type }}</td>
        <td>
          <a :href="att.file_url">
            {{ att.name }}
          </a>
        </td>
      </tr>
    </table>
    <pre>{{ attachments.images }}</pre>
  <file-uploader
    :config="config"
    :allowed-file-types="config.settings.allowed_filetypes"
    :auto-proceed="true"
    @upload-success="addFromUppy"
    />
  <images-converter
    />
  <pre>isConverting={{ attachments.isConverting }}</pre>
</template>
