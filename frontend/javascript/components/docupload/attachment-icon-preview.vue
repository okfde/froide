<script setup>

import { computed, inject, ref, nextTick } from 'vue'
import { useAttachments } from './lib/attachments'
const { refresh: refreshAttachments } = useAttachments()

import AttachmentActions from './attachment-actions.vue'
import AttachmentDocumentFields from './attachment-document-fields.vue'
import PdfRedactionModal from './pdf-redaction-modal.vue'

import { vBsTooltip } from '../../lib/vue-bootstrap'
import BsModal from '../bs-modal.vue'

import DocumentViewer from './document-viewer.vue'

const i18n = inject('i18n')
const config = inject('config')

const { attachment, actions, nudgeRedaction, big } = defineProps({
  attachment: {
    type: Object,
    required: true
  },
  actions: Boolean,
  nudgeRedaction: Boolean,
  big: Boolean
})

const pdfRedactionAtt = ref(null)
const pdfRedactionModal = ref()

const pdfRedactionUploaded = () => {
  pdfRedactionAtt.value = null
  refreshAttachments()
}

const needsRedaction = computed(() =>
  !attachment.is_irrelevant && !attachment.approved && attachment.can_approve && !attachment.has_redacted && !(attachment.converted && !attachment.is_image) && !attachment.pending
)

const iconClick = () => {
  if (needsRedaction.value && nudgeRedaction) {
    pdfRedactionAtt.value = attachment
    nextTick().then(() => pdfRedactionModal.value.show())
  } else {
    previewModal.value.show()
  }
}

const previewModal = ref()

const closePreviewModal = () => {
  previewModal.value.hide()
}

const iconTooltipTexts = computed(() => (needsRedaction.value && nudgeRedaction)
  ? [i18n.value.redact]
  : [
    i18n.value.preview,
    ...attachment.document ? [i18n.value.editTitle, i18n.value.editDescription] : []
  ]
)

const maxRetries = 3

let retries = maxRetries

const retryLoad = (evt) => {
  if (retries === 0) return
  console.log('AttachmentIconPreview img failed to load, retrying', retries, evt)
  retries--
  // back off slightly, first retry wait 3s, last 10s
  window.setTimeout(() => {
    const sep = evt.target.src.indexOf('?') > 0 ? '&' : '?'
    evt.target.src = evt.target.src + sep + 'retry=' + Date.now()
  }, 10000 / (retries + 1))
}

</script>

<template>
  <div :class="big ? 'attachment-icon-preview--big': ''">
    <a
      v-if="attachment.is_image"
      :href="attachment.site_url"
      class="d-flex align-items-center justify-content-center icon--image"
      :style="{ width: size, height: size }"
      @click.prevent="previewModal.show()"
      v-bs-tooltip
      data-bs-toggle="tooltip"
      data-bs-placement="top"
      :title="i18n.preview"
      >
      <img
        v-if="!attachment.pending"
        :src="attachment.file_url"
        :alt="i18n.preview"
        class="object-fit-contain shadow-sm"
        :style="{ maxWidth: size, maxHeight: size }"
        @error="retryLoad"
        />
    </a>
    <a
      v-else
      :href="attachment.site_url"
      class="btn btn-link lh-1 d-block p-0 me-2 icon--fa position-relative"
      @click.prevent="iconClick"
      v-bs-tooltip
      data-bs-toggle="tooltip"
      data-bs-placement="top"
      data-bs-html="true"
      :title="iconTooltipTexts.join('\n')"
      :data-bs-title="iconTooltipTexts.join('<br/>')"
      >
      <i class="fa fa-file" :style="{ fontSize: Size }" aria-hidden="true"></i>
      <span class="visually-hidden">
        {{ i18n.preview }}.
      </span>
      <span
        v-if="attachment.document"
        style="font-size: 25%"
        class="position-absolute top-0 start-0 translate-middle badge rounded-pill bg-secondary">
        <i class="fa fa-edit" aria-hidden="true"></i>
        <span class="visually-hidden">
          {{ i18n.editTitle }},
          {{ i18n.editDescription }}
        </span>
      </span>
      <span
        v-else-if="needsRedaction && nudgeRedaction"
        style="font-size: 25%"
        class="position-absolute top-0 start-0 translate-middle badge rounded-pill bg-secondary">
        <i class="fa fa-paint-brush" aria-hidden="true"></i>
        <span class="visually-hidden">
          {{ i18n.redact }}
        </span>
      </span>
    </a>
    <BsModal
      ref="previewModal"
      :key="attachment.id"
      dialog-classes="modal-dialog-scrollable ms-auto modal-xl modal-fullscreen-lg-down"
      content-classes="h-100"
      >
      <template #header>
        <h2>{{ attachment.document?.title || attachment.name }}</h2>
      </template>
      <template #body>
        <div class="row h-100">
          <div class="col-sm-8 mb-3">
            <DocumentViewer
              v-if="attachment.document && !attachment.document.pending"
              :document-url="attachment.document.resource_uri"
              :document-preview="attachment.document"
              :config="config"
              :defaults="{ maxHeight: '100%' }"
              ></DocumentViewer>
            <img
              v-else-if="attachment.is_image"
              :src="attachment.file_url"
              loading="lazy"
              class="w-100"
              />
            <iframe
              v-else
              loading="lazy"
              :src="attachment.file_url"
              class="h-100 w-100"
              ></iframe>
          </div>
          <div class="col-sm-4 d-flex flex-column">
            <div
              v-if="attachment.size || attachment.filetype || attachment.document"
              class="card mb-3"
              >
              <div class="card-body">
                <h5 class="card-title">
                  {{ i18n.properties }}
                </h5>
                <div v-if="attachment.size">
                  {{ i18n.size }}:
                  {{ Math.round(attachment.size / 1000) }}&nbsp;kB
                </div>
                <div v-if="attachment.filetype">
                  {{ i18n.fileType }}:
                  {{ attachment.filetype }}
                </div>
              </div>
              <div v-if="attachment.document" class="card-body border-top">
                <AttachmentDocumentFields :attachment="attachment" />
              </div>
            </div>
            <div
              v-if="actions"
              class="card actions"
              >
              <div class="card-body">
                <h5 class="card-title">
                  {{ i18n.actions }}
                </h5>
                <div class="d-flex flex-column">
                  <AttachmentActions
                    :attachment="attachment"
                    @action-done="closePreviewModal"
                    @action-delete="closePreviewModal"
                    />
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </BsModal>
    <PdfRedactionModal
      ref="pdfRedactionModal"
      :attachment="pdfRedactionAtt"
      @uploaded="pdfRedactionUploaded"
      />
  </div>
</template>

<style lang="scss" scoped>
@use 'sass:map';
@import 'bootstrap/scss/functions';
@import '../../../styles/variables.scss';

.actions :deep(.btn) {
  text-align: left;
}

.icon--image {
  width: 1.5rem;
  height: 1.5rem;

  img {
    max-width: 1.5rem;
    max-height: 1.5rem;
  }
}

.icon--fa {
  font-size: 1.5rem;
}

@include media-breakpoint-up(md) {
  .icon--image {
    width: 2.5rem;
    height: 2.5rem;

    img {
      max-width: 2.5rem;
      max-height: 2.5rem;
    }
  }

  .icon--fa {
    font-size: 2.5rem;
  }
}

.attachment-icon-preview--big {
  .icon--image {
    width: 4rem;
    height: 4rem;

    img {
      max-width: 4rem;
      max-height: 4rem;
    }
  }

  .icon--fa {
    font-size: 4rem;
  }
}

</style>
