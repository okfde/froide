<template>
  <div class="page">
    <div class="row justify-content-center">
      <div class="scol" :style="pageContainerStyle">
        <img v-if="page.url" ref="pageImage" :src="page.url" alt="" class="page-image"
          :style="pageStyle"
          @load="imageLoaded"
        />
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
        :class="{'progress-bar-animated progress-bar-striped': progressUnknown}"
        :style="{'width': progressPercentLabel}"
        role="progressbar" :aria-valuenow="page.progress"
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
      pageContainerStyle: {}
    }
  },
  computed: {
    pageStyle () {
      let styles = {
        transform: `rotate(${this.totalRotate}deg)`
      }
      if (this.totalRotate % 180 !== 0) {
        styles.maxHeight = '120px'
        styles.maxWidth = '120px'
        styles.width = 'auto'
      } else {
        styles.maxWidth = '120px'
        styles.width = '100%'
      }
      return styles
    },
    totalRotate () {
      let rotDegree = (this.page.rotate || 0)
      if (this.$root.exifSupport) {
        return rotDegree
      }
      return rotDegree + (this.page.implicitRotate || 0)
    },
    pageNum () {
      return this.page.pageNum
    },
    isLast () {
      return this.page.pageNum === this.pageCount
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
      this.$emit('pageupdated', {
          pageNum: this.pageNum,
          data: {
            rotate: ((this.page.rotate || 0) + 90) % 360
          }
      })
      window.setTimeout(() => this.calculateContainerStyle(), 500)
    },
    calculateContainerStyle () {
      console.log('update container style')
      let pageImage = this.$refs.pageImage
        if (!pageImage) {
          return {}
        }
        let dims = this.$refs.pageImage.getBoundingClientRect()
        let styles = {}
        if (this.totalRotate % 180 !== 0) {
          styles = {
            // 'max-height': `${Math.min(120, dims.height)}px`,
            'max-width': `${dims.width}px`
          }
        } else {
          styles = {}
        }
        this.pageContainerStyle = styles
    },
    imageLoaded (e) {
      let width = e.target.width
      let height = e.target.height
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
    border: 1px solid #bbb;
    transform-origin: center center;
    transition: transform 0.5s linear;
    image-orientation: none; /* Always read exif ourselves */
  }
  .scol {
    flex-basis: 0;
    flex-grow: 1;
    max-width: 100%;
  }
</style>
