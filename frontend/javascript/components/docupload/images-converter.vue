<script setup>

import { useAttachmentsStore } from './lib/attachments-store'
import ImageDocumentPagesSortable from './image-document-pages-sortable.vue'

const attachments = useAttachmentsStore()

</script>

<template>
  <div v-for="image in attachments.images" :key="image.id">
    <image-document-pages-sortable
      :dense="simple"
      :pages="image.pages"
      @resorted="image.pages = $event"
      @pageupdated="$emit('pageupdated', { document, ...$event })"
      @splitpages="splitPages" />
  </div>
</template>
