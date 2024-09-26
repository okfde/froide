<template>
  <div class="page col-2 mt-3">
    <div class="row justify-content-center">
      <div class="col-auto">
        <img
          v-if="pageUrl"
          ref="pageImage"
          :alt="page.name"
          :title="page.name"
          class="page-image"
          :src="pageUrl"
        />
      </div>
    </div>
    <div class="row justify-content-center">
      <div class="scol">
        <div class="text-start">
          <button
            class="btn btn-sm text-body-secondary small"
            @click="rotatePage"
          >
            <span class="fa fa-rotate-right" />
          </button>
        </div>
      </div>
      <div class="scol">
        <div class="text-center">
          {{ page.pageNum }}
        </div>
      </div>
      <div class="scol">
        <div v-if="!isLast" class="text-end">
          <button
            class="btn btn-sm text-body-secondary small"
            @click="splitPages"
          >
            <span class="fa fa-scissors" />
          </button>
        </div>
      </div>
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
    pageCount: {
      type: Number,
      required: true
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
    pageUrl() {
      if (!this.loaded) {
        return false
      }
      return this.rotateImage(this.totalRotate)
    },
    pageNum() {
      return this.page.pageNum
    },
    isLast() {
      return this.page.pageNum === this.pageCount
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
      this.$emit('splitpages', this.page.pageNum)
    },
    rotatePage() {
      const degree = ((this.page.rotate || 0) + 90) % 360
      this.$emit('pageupdated', {
        pageNum: this.pageNum,
        data: {
          rotate: degree
        }
      })
    },
    rotateImage(degree) {
      if (!this.imgBitmap) {
        return null
      }
      const canvas = document.createElement('canvas')
      if (degree % 180 === 0) {
        canvas.width = this.imgBitmap.width
        canvas.height = this.imgBitmap.height
      } else {
        canvas.width = this.imgBitmap.height
        canvas.height = this.imgBitmap.width
      }
      const ctx = canvas.getContext('2d')
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.save()

      ctx.translate(canvas.width / 2, canvas.height / 2)
      ctx.rotate((degree * Math.PI) / 180)
      ctx.drawImage(
        this.imgBitmap,
        -this.imgBitmap.width / 2,
        -this.imgBitmap.height / 2
      )

      ctx.restore()
      return canvas.toDataURL('image/jpeg', 1.0)
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
  flex: 0 0 120px;
  padding: 0 15px;
  margin: 0 1rem;
  cursor: move;
}
.page-image {
  display: block;
  width: 100%;
  max-width: 100%;
  border: 1px solid #bbb;
  image-orientation: none; /* Always read exif ourselves */
}
.scol {
  flex-basis: 0;
  flex-grow: 1;
  max-width: 100%;
}
</style>
