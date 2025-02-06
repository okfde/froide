<script setup>

import DjangoSlot from '../../lib/django-slot.vue'
import FileUploader from '../upload/file-uploader.vue'
import ImagesConverter from '../docupload/images-converter.vue'
import AttachmentsTable from './attachments-table.vue'
// TODO linter wrong? the two above are just fine...
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import OnlineHelp from '../online-help.vue'
import { useI18n } from '../../lib/i18n'
import { useAttachments } from './lib/attachments'

import { onMounted, nextTick, provide, ref, watch } from 'vue'

const props = defineProps(['config', 'message'])

const { i18n } = useI18n(props.config)
provide('i18n', i18n)
provide('config', props.config)

const { attachments, addFromUppy, refresh } = useAttachments({
  urls: {
    ...props.config.url,
    getAttachment: props.config.url.getAttachment.replace('/0/', '/') +
      '?belongs_to=' +
      props.message.id,
  },
  csrfToken: document.querySelector('[name=csrfmiddlewaretoken]').value,
  i18n,
})

onMounted(() => refresh())

const imagesConverterContainer = ref()

watch(
  () => attachments.images.length,
  (newValue) => {
    if (newValue > 0) {
      nextTick().then(() => {
        imagesConverterContainer.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      })
    }
  }
)

const onlineHelp = ref()

</script>

<template>
  <online-help ref="onlineHelp" />

  <p>
    <button
      type="button"
      class="btn btn-link text-decoration-underline ps-0"
      @click="onlineHelp.show(config.url.helpAttachmentsManagement)"
    >
      {{ i18n.helpNeeded }}
    </button>
  </p>

  <div
    v-show="attachments.isFetching" 
    class="spinner-border"></div>

  <div v-if="attachments.approved.length" class="my-5">
    <attachments-table
      :subset="attachments.approved"
      actions table-selection selection-actions badges-type badges-resolution
      />
  </div>

  <div v-if="attachments.notApproved.length" class="my-5">
    <django-slot name="notapproved-attachments" />
    <attachments-table
      :subset="attachments.notApproved"
      actions table-selection selection-actions badges-type
      />
  </div>

  <div v-if="attachments.irrelevant.length" class="my-5">
    <django-slot name="irrelevant-attachments" />
    <attachments-table
      :subset="attachments.irrelevant"
      actions table-selection selection-actions badges-type
      />
  </div>

  <div class="my-5">
    <django-slot name="upload-header" />
    <file-uploader
      :config="config"
      :allowed-file-types="config.settings.allowed_filetypes"
      :auto-proceed="true"
      @upload-success="addFromUppy"
      />
    <div ref="imagesConverterContainer">
      <images-converter />
    </div>
  </div>

</template>
