<template>
  <div class="page" :class="{ 'page--dense': dense }">
    <div class="page-frame">
      <img
        v-if="pageUrl"
        ref="pageImage"
        :alt="page.name"
        :title="page.name"
        class="page-image"
        :src="pageUrl"
      />
    </div>
    <div class="page-controls">
      <div class="page-control" v-if="!hideRotate">
        <button
          class="btn btn-sm text-body-secondary small"
          @click="rotatePage"
        >
          <span class="fa fa-rotate-right" />
        </button>
      </div>
      <div
        class="page-control page-control--number"
        :class="{ 'text-center': !hideRotate }"
      >
        {{ page.pageNum }}
      </div>
      <div class="page-control text-end" v-if="!hideSplit && !isLast">
        <button
          class="btn btn-sm text-body-secondary small"
          @click="splitPages"
        >
          <span class="fa fa-scissors" />
        </button>
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
    },
    dense: {
      type: Boolean,
      default: false
    },
    hideRotate: {
      type: Boolean,
      default: false
    },
    hideSplit: {
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
  --page-width: 60px;

  @media (min-width: 800px) {
    --page-width: 120px;
  }

  position: relative;
  flex: 0 0 var(--page-width);
  padding: 0;
  margin: 0 0.5rem 2rem 0;
  cursor: move;
}
.page-frame {
  width: var(--page-width);
  height: calc(var(--page-width) * 1.414);
  display: flex;
  align-items: flex-end;
}
.page-image {
  display: block;
  max-width: 100%;
  max-height: 100%;
  border: 1px solid #bbb;
  image-orientation: none; /* Always read exif ourselves */
}
.page-controls {
  display: flex;
}
.page-control {
  flex-basis: 0;
  flex-grow: 1;
  max-width: 100%;
}
.page--dense .page-control--number {
  position: absolute;
  bottom: 0.2rem;
  left: 0.2rem;
  font-size: 60%;
  background: var(--bs-link-color);
  color: white;
  width: 1.75em;
  height: 1.75em;
  text-align: center;
  line-height: 1.75em;
  border-radius: 50%;
  font-weight: bolder;
}
</style>
