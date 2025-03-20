<script setup>

import { computed, inject, ref } from 'vue'

import AttachmentActions from './attachment-actions.vue'
import AttachmentDocumentFields from './attachment-document-fields.vue'

import { vBsTooltip } from '../../lib/vue-bootstrap'
import BsModal from '../bs-modal.vue'

import DocumentViewer from './document-viewer.vue'

const i18n = inject('i18n')
const config = inject('config')

const { attachment, actions, big } = defineProps({
  attachment: {
    type: Object,
    required: true
  },
  actions: Boolean,
  big: Boolean
})

const previewModal = ref()

const closePreviewModal = () => {
  previewModal.value.hide()
}

const iconTooltipTexts = computed(() => [
  i18n.value.preview,
  ...attachment.document ? [i18n.value.editTitle, i18n.value.editDescription] : []
])

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
        :src="attachment.file_url"
        :alt="i18n.preview"
        class="object-fit-contain shadow-sm"
        :style="{ maxWidth: size, maxHeight: size }"
        />
    </a>
    <a
      v-else
      :href="attachment.site_url"
      class="btn btn-link lh-1 d-block p-0 me-2 icon--fa position-relative"
      @click.prevent="previewModal.show()"
      v-bs-tooltip
      data-bs-toggle="tooltip"
      data-bs-placement="top"
      data-bs-html="true"
      :title="iconTooltipTexts.join('\n')"
      :data-bs-title="iconTooltipTexts.join('<br/>')"
      >
      <i class="fa fa-file" :style="{ fontSize: Size }"></i>
      <span class="sr-only">
        {{ i18n.preview }}
      </span>
      <span
        v-if="attachment.document"
        style="font-size: 25%"
        class="position-absolute top-0 start-0 translate-middle badge rounded-pill bg-secondary">
        <i class="fa fa-edit"></i>
        <span class="sr-only">
          {{ i18n.editTitle }}<br/>
          {{ i18n.editDescription }}
        </span>
      </span>
    </a>
    <bs-modal
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
            <document-viewer
              v-if="attachment.document && !attachment.document.pending"
              :document-url="attachment.document.resource_uri"
              :document-preview="attachment.document"
              :config="config"
              :defaults="{ maxHeight: '100%' }"
              ></document-viewer>
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
                <attachment-document-fields :attachment="attachment" />
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
                  <attachment-actions
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
    </bs-modal>
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
  font-size: 1.5rem;
  width: 1em;
  height: 1em;

  img {
    max-width: 1em;
    max-height: 1em;
  }
}

.icon--fa {
  font-size: 1.5rem;
}

@include media-breakpoint-up(md) {
  .icon--image,
  .icon--fa {
    font-size: 2.5rem;
  }
}

.attachment-icon-preview--big {
  .icon--image,
  .icon--fa {
    font-size: 4rem;
  }
}

</style>
