<script setup>
import { computed, inject } from 'vue'

import { useAttachments } from './lib/attachments';

const i18n = inject('i18n')

const { attachments } = useAttachments()

const { attachment } = defineProps({
  attachment: {
    type: Object,
    required: true
  }
})

const unconverted = computed(() => attachments.getUnconvertedAttachmentByResourceUri(attachment.resource_uri))
const unconvertedExtension = computed(() => unconverted.value?.name.match?.(/\.(\w+)$/)?.[1])

</script>

<template>
  <span v-if="attachment.is_image" class="badge text-bg-secondary">
    {{ i18n.imageFile }}
  </span>
  <span
    v-else-if="unconverted && !unconverted.is_image"
    class="badge text-bg-secondary text-uppercase"
    :title="unconverted.filetype"
    >
    {{ unconvertedExtension }}
  </span>
</template>