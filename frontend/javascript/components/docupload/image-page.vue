<script setup>
import { computed, inject } from 'vue'

import { useAttachments } from './lib/attachments'

const { splitPages, rotatePage } = useAttachments()

const i18n = inject('i18n')

const { idx, page, pageNum, pageCount, showRotate, showSplit } = defineProps({
  idx: {
    type: Number,
    required: true
  },
  page: {
    type: Object,
    required: true
  },
  pageNum: {
    type: Number,
    required: true
  },
  pageCount: {
    type: Number,
    required: true
  },
  showRotate: {
    type: Boolean,
    default: false
  },
  showSplit: {
    type: Boolean,
    default: false
  }
})

const totalRotate = computed(() => {
  return ((page.rotate || 0) + (page.metadata?.implicitRotate || 0)) % 360
})

const isLast = computed(() => pageNum === pageCount)

const progressAlmostComplete = computed(
  () => !progressUnknown.value && page.progress === page.progressTotal
)

const progressUnknown = computed(() => progressPercent.value === null)

const progressPercent = computed(() => {
  if (!page.progressTotal) {
    return null
  }
  return (page.progress / page.progressTotal) * 100
})

const progressPercentLabel = computed(() => {
  if (progressPercent.value) {
    return `${progressPercent.value}%`
  }
  return '100%'
})
</script>

<template>
  <div class="page">
    <div
      class="page-frame d-flex align-items-center justify-content-center position-relative"
    >
      <img
        v-if="page.file_url && !page.pending"
        ref="pageImage"
        :alt="page.name"
        :title="page.name"
        class="page-image d-block mw-100 mh-100 border"
        :src="page.file_url"
        :style="{ transform: `rotate(${totalRotate}deg)` }"
      />
      <div
        class="page-control page-control--number position-absolute bottom-0 mb-2 start-0 ms-1 text-bg-primary badge rounded-pill fw-bold lh-sm"
      >
        {{ pageNum }}
      </div>
    </div>
    <div class="page-controls d-flex align-items-center">
      <!-- btn-link is not "semantically" appropriate here, but needed for focus-visible
        btn-outline looks really noisy, unfortunately -->
      <button
        v-if="showRotate"
        class="btn btn-link btn-sm text-body-secondary small"
        type="button"
        @click="rotatePage(page)"
      >
        <span class="fa fa-rotate-right" aria-hidden="true" />
        <span class="visually-hidden">{{ i18n.rotatePage }}</span>
      </button>
      <button
        v-if="showSplit && !isLast"
        class="btn btn-link btn-sm text-body-secondary small ms-auto"
        type="button"
        @click="splitPages(idx, pageNum)"
      >
        <span class="fa fa-scissors" aria-hidden="true" />
        <span class="visually-hidden">{{ i18n.splitPagesHere }}</span>
      </button>
    </div>
    <div
      v-if="page.uploading"
      class="progress"
      role="progressbar"
      :aria-valuenow="document.progress"
      aria-valuemin="0"
      aria-valuemax="100"
    >
      <div
        class="progress-bar"
        :class="{
          'progress-bar-animated progress-bar-striped': progressAlmostComplete,
          'bg-info progress-bar-striped': progressUnknown
        }"
        :style="{ width: progressPercentLabel }"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page {
  --page-width: 60px;

  @media (min-width: 800px) {
    --page-width: 120px;
  }

  flex: 0 0 var(--page-width);
  cursor: move;
}
.page-frame {
  width: var(--page-width);
  height: var(--page-width);
}
.page-image {
  image-orientation: none; /* Always read exif ourselves */
  transition: transform 1s;
}
</style>
