<script setup>

import { ref } from 'vue'

import AttachmentActions from './attachment-actions.vue'

import BsModal from '../bs-modal.vue'

const { attachment, size } = defineProps({
  attachment: {
    type: Object,
    required: true
  },
  size: {
    type: String,
    default: '2em'
  }
})

const previewModal = ref()

</script>

<template>
  <div>
    <a class="btn btn-link p-0" type="button" @click="previewModal.show()">
      <i class="fa fa-file" :style="{ fontSize: size }"></i>
    </a>
    <bs-modal
      ref="previewModal"
      dialog-classes="modal-dialog-scrollable ms-auto modal-lg"
      content-classes="h-100"
      >
      <template #header>
        <h2>{{  attachment.name }}</h2>
      </template>
      <template #body>
        <div class="row h-100">
          <div class="col-sm-8">
            <iframe
              loading="lazy"
              :src="attachment.file_url"
              class="h-100 w-100"
              ></iframe>
          </div>
          <div class="actions col-sm-4 d-flex flex-column">
            <attachment-actions :attachment="attachment" />
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
