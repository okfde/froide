<template>
  <div class="page">
    <div class="row justify-content-center">
      <div class="scol" :style="pageContainerStyle">
        <img v-if="page.url" :src="page.url" alt="" class="page-image"
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
        :class="{'progress-bar-animated progress-bar-striped': page.progressPercent === null}"
        :style="{'width': page.progress ? page.progressPercentLabel : '100%'}"
        role="progressbar" :aria-valuenow="page.progressPercent ? page.progressPercent : 0"
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
      width: null,
      height: null
    }
  },
  computed: {
    pageStyle () {
      let rotDegree = (this.page.rotate || 0)
      let degree = rotDegree + (this.page.implicitRotate || 0)
      let styles = {
        transform: `rotate(${degree}deg)`
      }
      return styles
    },
    pageContainerStyle () {
      let rotDegree = (this.page.rotate || 0)
      let styles = {}
      if (this.page.width) {
        if (rotDegree % 180 !== 0) {
          styles.height = this.page.height + 'px'
        } else {
          styles.height = this.page.width + 'px'
        }
      }
      return styles
    },
    pageNum () {
      return this.page.pageNum
    },
    isLast () {
      return this.page.pageNum === this.pageCount
    }
  },
  methods: {
    splitPages () {
      this.$emit('splitpages', page.pageNum)
    },
    rotatePage () {
      this.$emit('pageupdated', {
          pageNum: this.pageNum,
          data: {
            rotate: ((this.page.rotate || 0) + 90) % 360
          }
      })
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
    },
  }
}

</script>

<style lang="scss" scoped>
  .page {
    display: inline-block;
    max-width: 120px;
    height: 120px;
    margin: 0 1rem;
    cursor: move;
  }
  .page-image {
    width: 100%;
    border: 1px solid #bbb;
    transform-origin: center center;
    transition: transform 0.5s linear;
  }
  .scol {
    flex-basis: 0;
    flex-grow: 1;
    max-width: 100%;
  }
</style>
