<script setup>

import { useAttachmentsStore } from './lib/attachments-store'
import ImageDocumentPagesSortable from './image-document-pages-sortable.vue'
import { pinia } from '../../lib/pinia'

const attachments = useAttachmentsStore(pinia)

</script>

<template>
  <div v-for="(image, idx) in attachments.images" :key="image.id">
    <image-document-pages-sortable
      :dense="simple"
      :image="image"
      :idx="idx"
      @resorted="image.pages = $event"
      @pageupdated="$emit('pageupdated', { document, ...$event })"
      @splitpages="splitPages" />
  </div>
</template>
