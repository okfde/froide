<script setup>
import { computed, ref } from 'vue'

import ExifReader from 'exifreader'

import { useExifSupport } from './lib/exif-support'
import { useAttachments } from './lib/attachments'

const { hasExifSupport } = useExifSupport()
const { splitPages, rotatePage } = useAttachments()

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

const loaded = ref(false)
const imgBitmap = ref(null)

const totalRotate = computed(() => {
  const rotDegree = page.rotate || 0
  if (hasExifSupport.value) {
    return rotDegree
  }
  return rotDegree + (page.implicitRotate || 0)
})

const isLast = computed(() => pageNum === pageCount)

const progressAlmostComplete = computed(() =>
  !progressUnknown.value && page.progress === page.progressTotal
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

const fetchImage = () => {
  fetch(page.file_url)
    .then((response) => {
      return response.blob()
    })
    .then((blob) => {
      return Promise.all([blob.arrayBuffer(), createImageBitmap(blob)])
    })
    .then(([ab, v]) => {
      const reader = ExifReader.load(ab, { expanded: true })
      const data = {
        exif: true,
        width: v.width,
        heigh: v.height,
        implicitRotate: 0
      }
      const orientation = reader.exif?.Orientation?.value
      if (orientation === 6) {
        data.implicitRotate = 90
      } else if (orientation === 8) {
        data.implicitRotate = 270
      } else if (orientation === 3) {
        data.implicitRotate = 180
      }
      imgBitmap.value = v
      loaded.value = true
    })
}

fetchImage()

</script>

<template>
  <div class="page">
    <div class="page-frame d-flex align-items-center justify-content-center position-relative">
      <img
        v-if="page.file_url"
        ref="pageImage"
        :alt="page.name"
        :title="page.name"
        class="page-image d-block mw-100 mh-100 border"
        :src="page.file_url"
        :style="{ transform: `rotate(${totalRotate}deg)`}"
        />
      <div
        class="page-control page-control--number position-absolute bottom-0 mb-1 start-0 ms-1 text-bg-primary badge rounded-pill fw-bold lh-sm">
        {{ pageNum }}
      </div>
    </div>
    <div class="page-controls d-flex align-items-center">
      <button
        v-if="showRotate"
        class="btn btn-sm text-body-secondary small"
        @click="rotatePage(page)">
        <span class="fa fa-rotate-right" />
      </button>
      <button
        v-if="showSplit && !isLast"
        class="btn btn-sm text-body-secondary small ms-auto"
        @click="splitPages(idx, pageNum)">
        <span class="fa fa-scissors" />
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
