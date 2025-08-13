<template>
  <AttachmentBadgeFiletype
    v-if="badgesType"
    :attachment="attachment"
    />
  <span
    v-if="attachment.pending || attachment.document?.pending"
    class="badge text-bg-secondary me-1">
    <i class="fa fa-hourglass-half"></i>
    {{ i18n.pending}}
  </span>
  <span
    v-if="badgesNew && attachment.new"
    class="badge text-bg-success me-1"
    >{{ i18n.new }}</span>
  <span
    v-if="badgesRedaction && attachment.is_redacted"
    class="badge text-bg-success me-1"
    >{{ i18n.redacted }}</span>
  <span
    v-if="badgesResolution && attachment.document"
    class="badge text-bg-success me-1"
    >{{ i18n.resolution }}</span>
  <span
    v-if="badgesRedaction && !attachment.is_redacted"
    class="badge text-bg-warning me-1"
    >{{ i18n.nonRedacted }}</span>
</template>

<script setup>

import { inject } from 'vue'

import AttachmentBadgeFiletype from './attachment-badge-filetype.vue'

const i18n = inject('i18n')

const { attachment, badgesNew, badgesRedaction, badgesType, badgesResolution } = defineProps({
  attachment: {
    type: Object,
    required: true
  },
  badgesNew: Boolean,
  badgesRedaction: Boolean,
  badgesType: Boolean,
  badgesResolution: Boolean,
})

</script>