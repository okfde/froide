<script setup>

import FileUploader from '../upload/file-uploader.vue'
import ImagesConverter from '../docupload/images-converter.vue'
import { useAttachments } from './lib/attachments'
import { useAttachmentsStore } from './lib/attachments-store'

const props = defineProps(['config', 'message'])

const attachments = useAttachmentsStore()

const todo = () => {}

const { addFromUppy } = useAttachments({
  attachments,
  url: props.config.url.getAttachment.replace('/0/', '/') +
    '?belongs_to=' +
    props.message.id,
  csrfToken: document.querySelector('[name=csrfmiddlewaretoken]').value,
  onDocumentsAdded: todo,
  onImagesAdded: todo,
})

</script>

<template>
  <hr/>
  <pre>
    ATTACHMENT MANAGER
    {{ attachments }}
  </pre>
  <file-uploader
    :config="config"
    :allowed-file-types="config.settings.allowed_filetypes"
    :auto-proceed="true"
    @upload-success="addFromUppy"
    />
  <images-converter
    />
  <button>convert images</button>
</template>
