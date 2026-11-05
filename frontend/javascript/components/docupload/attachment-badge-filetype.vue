<script setup>
import { computed } from 'vue'
import { useGettext } from 'vuepo/vue'

import { useAttachments } from './lib/attachments'

const { gettext } = useGettext()

const { attachments } = useAttachments()

const { attachment } = defineProps({
  attachment: {
    type: Object,
    required: true
  }
})

const unconverted = computed(() =>
  attachments.getUnconvertedAttachmentByResourceUri(attachment.resource_uri)
)
const unconvertedExtension = computed(
  () => unconverted.value?.name.match?.(/\.(\w+)$/)?.[1]
)
</script>

<template>
  <span v-if="attachment.is_image" class="badge text-bg-secondary me-1">
    {{ gettext('Image file') }}
  </span>
  <span
    v-else-if="unconverted && !unconverted.is_image"
    class="badge text-bg-secondary text-uppercase me-1"
    :title="unconverted.filetype"
  >
    {{ unconvertedExtension }}
  </span>
</template>
