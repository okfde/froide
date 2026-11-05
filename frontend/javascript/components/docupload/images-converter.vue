<script setup>
import { t } from 'vuepo'
import { useGettext } from 'vuepo/vue'
import { useAttachments } from './lib/attachments'
import ImageDocumentPagesSortable from './image-document-pages-sortable.vue'

const { attachments, convertImage } = useAttachments()

const { gettext, ngettext } = useGettext()

const emit = defineEmits(['converted'])

const convertImagesClick = (idx) => {
  convertImage(idx)
    .then(() => {
      emit('converted')
    })
    .catch((err) => {
      console.error(err)
      window.alert(`${gettext('Error')}: ${err.message}`)
    })
}
</script>

<template>
  <div v-for="(image, idx) in attachments.images" :key="idx">
    <div class="card my-3">
      <div class="card-header">
        {{
          ngettext(
            'New document with one page',
            t`New document with ${count} pages`,
            image.pages.length
          )
        }}
      </div>
      <div class="card-body">
        <p class="text-body-secondary">
          {{
            gettext(
              'Here you can combine your uploaded images to a PDF document. You can rearrange the pages and split it into multiple documents. You can redact the PDF in the next step.'
            )
          }}
        </p>
        <label class="form-label" :for="'imagesConverterName' + idx">{{
          gettext('Name of attachment to create')
        }}</label>
        <input
          type="text"
          :id="'imagesConverterName' + idx"
          v-model="image.name"
          class="form-control"
          :placeholder="gettext('e.g. Letter from date')"
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
            {{ gettext('Convert images to document') }}
          </button>
          <span
            v-show="image.isConverting"
            class="spinner-border spinner-border-sm ms-3"
            role="status"
          >
            <span class="sr-only">{{ gettext('Loading...') }}</span>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
