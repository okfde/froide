<template>
  <div class="page col-2 mt-3">
    <div class="row justify-content-center">
      <div class="col-auto">
        <img v-if="pageUrl" ref="pageImage" :src="pageUrl" alt="" class="page-image"/>
      </div>
    </div>
    <div class="row justify-content-center">
      <div class="scol">
        <div class="text-left">
          <button class="btn btn-sm text-muted small" :class="{'btn-info': page.needsRotation}" @click="rotatePage">
            <span class="fa fa-rotate-right"></span>
          </button>
        </div>
      </div>
      <div class="scol">
        <div class="text-center">
          {{ page.pageNum }}
        </div>
      </div>
      <div class="scol">
        <div class="text-right" v-if="!isLast">
          <button class="btn btn-sm text-muted small" @click="splitPages">
            <span class="fa fa-scissors"></span>
          </button>
        </div>
      </div>
    </div>
    <div v-if="page.uploading" class="progress">
      <div class="progress-bar"
        :class="{
          'progress-bar-animated progress-bar-striped': progressAlmostComplete,
          'bg-info progress-bar-striped': progressUnknown,
        }"
        :style="{'width': progressPercentLabel}"
        role="progressbar" :aria-valuenow="document.progress"
        aria-valuemin="0" aria-valuemax="100"></div>
    </div>
  </div>
</template>

<script>

import EXIF from 'exif-js'

export default {
  name: 'image-page',
  // mixins: [I18nMixin],
  props: ['page', 'pageCount'],
  data () {
    return {
      loaded: false,
      width: null,
      height: null,
    }
  },
  computed: {
    totalRotate () {
      let rotDegree = (this.page.rotate || 0)
      if (this.$root.exifSupport) {
        return rotDegree
      }
      return rotDegree + (this.page.implicitRotate || 0)
    },
    image () {
      this.loaded = false
      const image = new window.Image()
      image.onload = this.imageLoaded
      image.src = this.page.url
      return image
    },
    pageUrl () {
      if (!this.page.url) {
        return false
      }
      if (this.image) {
        if (this.totalRotate === 0) {
          return this.page.url
        }
        return this.rotateImage(this.totalRotate) 
      }
      return false
    },
    pageNum () {
      return this.page.pageNum
    },
    isLast () {
      return this.page.pageNum === this.pageCount
    },
    progressAlmostComplete () {
      return !this.progressUnknown && this.page.progress === this.page.progressTotal
    },
    progressUnknown () {
      return this.progressPercent === null
    },
    progressPercent () {
      if (!this.page.progressTotal) {
        return null
      }
      return this.page.progress / this.page.progressTotal * 100
    },
    progressPercentLabel () {
      if (this.progressPercent) {
        return `${this.progressPercent}%`
      }
      return '100%'
    }
  },
  methods: {
    splitPages () {
      this.$emit('splitpages', this.page.pageNum)
    },
    rotatePage () {
      const degree = ((this.page.rotate || 0) + 90) % 360
      this.$emit('pageupdated', {
          pageNum: this.pageNum,
          data: {
            rotate: degree
          }
      })
    },
    rotateImage (degree) {
      if (!this.loaded) {
        return null
      }
      const img = this.image
      const canvas = document.createElement('canvas')
      if (degree % 180 === 0) {
        canvas.width = this.width
        canvas.height = this.height
      } else {
        canvas.width = this.height
        canvas.height = this.width
      }
      const ctx = canvas.getContext('2d')
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.save()
      
      ctx.translate(canvas.width / 2, canvas.height / 2)
      ctx.rotate(degree * Math.PI / 180)
      ctx.drawImage(img, -img.width / 2, -img.height / 2)

      ctx.restore()
      return canvas.toDataURL('image/jpeg', 1.0)
    },
    imageLoaded (e) {
      this.loaded = true
      let width = this.width = e.target.width
      let height = this.height = e.target.height
      let page = this.page
      if (page.exif === undefined) {
        let self = this
        EXIF.getData(e.target, function() {
          let data = {
            exif: true,
            width,
            height
          }
          let orientation = EXIF.getTag(this, "Orientation");
          if(orientation === 6) {
            data.implicitRotate = 90
          }
          else if (orientation === 8) {
            data.implicitRotate = 270
          } else if (orientation === 3) {
            data.implicitRotate = 180
          }
          if (self.width > self.height && data.implicitRotate % 180 === 0) {
            data.needsRotation = true
          }
          self.$emit('pageupdated', {
            pageNum: self.pageNum,
            data: data
          })
        })
      }
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
