<script setup>
import DjangoSlot from '../../lib/django-slot.vue'
import FileUploader from '../upload/file-uploader.vue'
import ImagesConverter from '../docupload/images-converter.vue'
import AttachmentsTable from './attachments-table.vue'
import OnlineHelp from '../online-help.vue'
import BsToast from '../bs-toast.vue'
import { useI18n } from '../../lib/i18n'
import { useAttachments } from './lib/attachments'
import { csrfToken } from '../../api'

import { onMounted, nextTick, provide, ref, watch } from 'vue'

const props = defineProps(['config', 'message'])

const { i18n } = useI18n(props.config)
provide('i18n', i18n)
provide('config', props.config)

const { attachments, addFromUppy, refresh } = useAttachments({
  message: props.message,
  urls: {
    ...props.config.url
  },
  csrfToken,
  i18n
})

onMounted(() => refresh())

const imagesConverterContainer = ref()

watch(
  () => attachments.images.length,
  async (newValue) => {
    if (newValue > 0) {
      await nextTick()
      imagesConverterContainer.value?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest'
      })
    }
  }
)

const onlineHelp = ref()
</script>

<template>
  <OnlineHelp ref="onlineHelp" />

  <p>
    <button
      type="button"
      class="btn btn-link text-decoration-underline ps-0"
      @click="onlineHelp.show(config.url.helpAttachmentsManagement)"
    >
      {{ i18n.helpNeeded }}
    </button>
  </p>

  <div v-show="attachments.isFetching" class="spinner-border">
    <span class="sr-only">{{ i18n.attachmentsLoading }}</span>
  </div>

  <div v-if="attachments.approved.length" class="my-5">
    <AttachmentsTable
      :subset="attachments.approved"
      actions
      table-selection
      cards-selection
      selection-action-delete
      selection-action-make-result
      nudge-redaction
      badges-type
      badges-resolution
    />
  </div>

  <div v-if="attachments.notApproved.length" class="my-5">
    <DjangoSlot name="notapproved-attachments" />
    <AttachmentsTable
      :subset="attachments.notApproved"
      actions
      table-selection
      cards-selection
      selection-action-delete
      selection-action-approve
      nudge-redaction
      badges-type
    />
  </div>

  <div v-if="attachments.irrelevant.length" class="my-5">
    <DjangoSlot name="irrelevant-attachments" />
    <AttachmentsTable
      :subset="attachments.irrelevant"
      actions
      table-selection
      cards-selection
      selection-action-delete
      badges-type
    />
  </div>

  <div class="my-5">
    <DjangoSlot name="upload-header" />
    <FileUploader
      :config="config"
      :allowed-file-types="config.settings.allowed_filetypes"
      :auto-proceed="true"
      @upload-success="addFromUppy"
    />
    <div ref="imagesConverterContainer">
      <ImagesConverter />
    </div>
  </div>

  <BsToast
    v-for="(toast, toastIdx) in attachments.messages"
    :key="toastIdx"
    :color="toast.color"
  >
    <template #body>
      {{ toast.body }}
    </template>
  </BsToast>
</template>
