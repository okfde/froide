<script setup>

import { inject, ref } from 'vue'

import AttachmentActions from './attachment-actions.vue'

import BsModal from '../bs-modal.vue'

const i18n = inject('i18n')

const { attachment, iconSize, thumbnailSize } = defineProps({
  attachment: {
    type: Object,
    required: true
  },
  iconSize: {
    type: String,
    default: '2em'
  },
  thumbnailSize: {
    type: String,
    default: '4em'
  }
})

const previewModal = ref()

</script>

<template>
  <div>
    <a
      v-if="attachment.is_image"
      :href="attachment.site_url"
      class="d-flex align-items-center justify-content-center"
      :style="{ width: thumbnailSize, height: thumbnailSize }"
      @click.prevent="previewModal.show()"
      >
      <img
        :src="attachment.file_url"
        class="object-fit-contain shadow-sm"
        :style="{ maxWidth: thumbnailSize, maxHeight: thumbnailSize }"
        />
    </a>
    <a
      v-else
      :href="attachment.site_url"
      class="btn btn-link d-block p-0 me-2"
      type="button"
      @click.prevent="previewModal.show()">
      <i class="fa fa-file" :style="{ fontSize: iconSize }"></i>
    </a>
    <bs-modal
      ref="previewModal"
      dialog-classes="modal-dialog-scrollable ms-auto modal-xl modal-fullscreen-lg-down"
      content-classes="h-100"
      >
      <template #header>
        <h2>{{  attachment.name }}</h2>
      </template>
      <template #body>
        <div class="row h-100">
          <div class="col-sm-8 mb-3">
            <img
              v-if="attachment.is_image"
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
              v-if="attachment.size || attachment.filetype"
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
            </div>
            <div class="card actions">
              <div class="card-body">
                <h5 class="card-title">
                  {{ i18n.actions }}
                </h5>
                <attachment-actions :attachment="attachment" />
              </div>
            </div>
          </div>
        </div>
      </template>
    </bs-modal>
  </div>
</template>

<style lang="scss" scoped>
.actions :deep(.btn) {
  text-align: left;
}
</style>
