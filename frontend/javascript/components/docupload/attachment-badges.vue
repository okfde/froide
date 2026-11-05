<script setup>
import { useGettext } from 'vuepo/vue'

import AttachmentBadgeFiletype from './attachment-badge-filetype.vue'

const { gettext } = useGettext()

const { attachment, badgesNew, badgesRedaction, badgesType, badgesResolution } =
  defineProps({
    attachment: {
      type: Object,
      required: true
    },
    badgesNew: Boolean,
    badgesRedaction: Boolean,
    badgesType: Boolean,
    badgesResolution: Boolean
  })
</script>

<template>
  <AttachmentBadgeFiletype v-if="badgesType" :attachment="attachment" />
  <span
    v-if="attachment.pending || attachment.document?.pending"
    class="badge text-bg-secondary me-1"
  >
    <i class="fa fa-hourglass-half"></i>
    {{ gettext('Processing…') }}
  </span>
  <span v-if="badgesNew && attachment.new" class="badge text-bg-success me-1">{{
    gettext('New')
  }}</span>
  <span
    v-if="badgesRedaction && attachment.is_redacted"
    class="badge text-bg-success me-1"
    >{{ gettext('redacted') }}</span
  >
  <span
    v-if="badgesResolution && attachment.document"
    class="badge text-bg-success me-1"
    >{{ gettext('Resolution') }}</span
  >
  <span
    v-if="badgesRedaction && !attachment.is_redacted"
    class="badge text-bg-warning me-1"
    >{{ gettext('non-redacted') }}</span
  >
</template>
