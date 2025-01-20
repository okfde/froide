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
        @click="rotatePage">
        <span class="fa fa-rotate-right" />
      </button>
      <button
        v-if="showSplit && !isLast"
        class="btn btn-sm text-body-secondary small ms-auto"
        @click="splitPages">
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

<script>
import ExifReader from 'exifreader'

export default {
  name: 'ImagePage',
  props: {
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
  },
  data() {
    return {
      loaded: false,
      width: null,
      height: null,
      imgBitmap: null
    }
  },
  created() {
    this.fetchImage()
  },
  computed: {
    totalRotate() {
      const rotDegree = this.page.rotate || 0
      if (this.$root.exifSupport) {
        return rotDegree
      }
      return rotDegree + (this.page.implicitRotate || 0)
    },
    isLast() {
      return this.pageNum === this.pageCount
    },
    progressAlmostComplete() {
      return (
        !this.progressUnknown && this.page.progress === this.page.progressTotal
      )
    },
    progressUnknown() {
      return this.progressPercent === null
    },
    progressPercent() {
      if (!this.page.progressTotal) {
        return null
      }
      return (this.page.progress / this.page.progressTotal) * 100
    },
    progressPercentLabel() {
      if (this.progressPercent) {
        return `${this.progressPercent}%`
      }
      return '100%'
    }
  },
  methods: {
    splitPages() {
      this.$emit('splitpages')
    },
    rotatePage() {
      this.$emit('rotatepage')
    },
    fetchImage() {
      fetch(this.page.file_url)
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
          this.$emit('pageupdated', {
            pageNum: this.pageNum,
            data
          })
          this.imgBitmap = v
          this.loaded = true
        })
    }
  }
}
</script>

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
