<script setup>
import { inject } from 'vue'
import { useAttachments } from './lib/attachments'
import ImageDocumentPagesSortable from './image-document-pages-sortable.vue'

const { attachments, convertImage } = useAttachments()

const i18n = inject('i18n')

const emit = defineEmits(['converted'])

const convertImagesClick = (idx) => {
  convertImage(idx)
    .then(() => {
      emit('converted')
    })
    .catch((err) => {
      console.error(err)
      window.alert(`${i18n.value.error}: ${err.message}`)
    })
}
</script>

<template>
  <div v-for="(image, idx) in attachments.images" :key="idx">
    <div class="card my-3">
      <div class="card-header">
        {{ i18n._('newDocumentPageCount', { count: image.pages.length }) }}
      </div>
      <div class="card-body">
        <p class="text-body-secondary">
          {{ i18n.imageDocumentExplanation }}
        </p>
        <label class="form-label" :for="'imagesConverterName' + idx">{{
          i18n.attachmentName
        }}</label>
        <input
          type="text"
          :id="'imagesConverterName' + idx"
          v-model="image.name"
          class="form-control"
          :placeholder="i18n.documentTitlePlaceholder"
        />
        <div class="position-relative">
          <ImageDocumentPagesSortable :idx="idx" show-rotate show-split />
        </div>
        <div>
          <button
            type="button"
            class="btn btn-primary"
            @click="convertImagesClick(idx)"
            :disabled="attachments.isConverting"
          >
            {{ i18n.convertImages }}
          </button>
          <span
            v-show="image.isConverting"
            class="spinner-border spinner-border-sm ms-3"
            role="status"
          >
            <span class="sr-only">{{ i18n.loading }}</span>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
