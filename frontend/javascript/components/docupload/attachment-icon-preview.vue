<script setup>

import { computed, inject, ref } from 'vue'

import AttachmentActions from './attachment-actions.vue'
import AttachmentDocumentFields from './attachment-document-fields.vue'

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
  big: Boolean,
})

const emit = defineEmits(['redactClick'])

const needsRedaction = computed(() =>
  !attachment.is_irrelevant && !attachment.approved && attachment.can_approve && !attachment.has_redacted && !(attachment.converted && !attachment.is_image) && !attachment.pending
)

const iconClick = () => {
  if (needsRedaction.value && nudgeRedaction) {
    emit('redactClick', attachment)
  } else {
    previewModal.value.show()
  }
}

const redactClick = (att) => {
  closePreviewModal()
  emit('redactClick', att)
}

const previewModal = ref()

const closePreviewModal = () => {
  previewModal.value.hide()
}

const iconTooltipTexts = computed(() => {
  if (attachment.is_image) return [i18n.value.preview]
  if (needsRedaction.value && nudgeRedaction) return [i18n.value.redact]
  return [
    i18n.value.preview,
    ...attachment.document
      ? [i18n.value.editTitle, i18n.value.editDescription]
      : []
  ]
})

</script>

<template>
  <!-- we need the one root div so parent can set class -->
  <div
    class="d-flex"
    :class="{ 'attachment-icon-preview--big': big }"
    >
    <div
      class="icon-with-name"
      :class="{ 'd-flex': !big }"
      v-bs-tooltip
      data-bs-toggle="tooltip"
      data-bs-placement="top"
      data-bs-html="true"
      :title="iconTooltipTexts.join('\n')"
      :data-bs-title="iconTooltipTexts.join('<br/>')"
      @click.prevent="iconClick"
      >
      <a
        v-if="attachment.is_image"
        :href="attachment.site_url"
        class="d-flex align-items-center justify-content-center icon--image position-md-static"
        :class="{ 'position-absolute': !big }"
        :style="{ width: size, height: size }"
        >
        <img
          v-if="!attachment.pending"
          :src="attachment.file_url"
          :alt="i18n.preview"
          class="object-fit-contain shadow-sm"
          :style="{ maxWidth: size, maxHeight: size }"
          />
      </a>
      <a
        v-else
        :href="attachment.site_url"
        class="lh-1 d-block p-0 me-2 icon--fa"
        :class="{
          'position-relative': big,
          'position-absolute': !big,
          'position-md-relative': !big,
        }"
        >
        <i class="fa fa-file" :style="{ fontSize: Size }" aria-hidden="true"></i>
        <span class="visually-hidden">
          {{ i18n.preview }}
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
        <div
          v-if="attachment.isApproving"
          class="position-absolute top-50 start-50 translate-middle"
          >
          <span
            style="font-size: 25%"
            class="spinner-border spinner-border-sm text-light"
            role="status"
            >
            <span class="sr-only">{{ i18n.loading }}</span>
          </span>
        </div>
      </a>
      <div class="name align-self-center no-hyphens text-break">
        {{ attachment.document?.title || attachment.name }}
      </div>
    </div>
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
                    @redact-click="redactClick"
                    />
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </BsModal>
    <!-- both Modals need to be within the root div for class set by parent -->
  </div>
</template>

<style lang="scss" scoped>
@use 'sass:map';
@import 'bootstrap/scss/functions';
@import '../../../styles/variables.scss';

.actions :deep(.btn) {
  text-align: left;
}

.icon-with-name:hover .name {
  text-decoration: underline;
  color: var(--bs-link-hover-color);
  cursor: pointer;
}

.icon--image {
  width: 1.5rem;
  height: 1.5rem;
  left: 1.5rem;

  img {
    max-width: 1.5rem;
    max-height: 1.5rem;
  }
}

.icon--fa {
  font-size: 1.5rem;
  left: 1.5rem;
}

@include media-breakpoint-up(md) {
  .icon--image {
    width: 2.5rem;
    height: 2.5rem;
    left: 0;

    img {
      max-width: 2.5rem;
      max-height: 2.5rem;
    }
  }

  .icon--fa {
    font-size: 2.5rem;
    left: 0;
  }
}

.attachment-icon-preview--big {
  .icon--fa,
  .icon--image {
    margin-left: auto !important;
    margin-right: auto !important;
    max-width: 4rem;
    width: 4rem;
    height: 4rem;
    left: 0;

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
