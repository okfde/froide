<!--
Based on https://github.com/dexmo007/vue-image-redact
by dexmo007 licensed under MIT license
-->

<template>
  <canvas
    ref="canvas"
    @mousedown="mousedown"
    @touchstart="mousedown"
    @mouseup="mouseup"
    @touchend="mouseup"
    @mousemove="mousemove"
    @touchmove="mousemove"
    tabindex="1"
    @keyup.delete="deleteActives"
    :style="{
      maxWidth: '100%',
      cursor: cursor
    }"></canvas>
</template>

<script>
// Scale images down to 1200px
const MAX_WIDTH = 1200

export default {
  name: 'ProofRedact',
  props: {
    src: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      holding: false,
      drawing: false,
      moving: null,
      actives: [],
      rects: [],
      image: null,
      cursor: 'crosshair'
    }
  },
  created() {
    this.startRedaction()
  },
  computed: {
    canUndo() {
      return this.rects.length > 0
    }
  },
  methods: {
    startRedaction() {
      this.rects = []
      this.actives = []
      const image = new Image()
      image.crossOrigin = 'Anonymous'
      image.addEventListener('load', this.imageLoaded, false)
      image.src = this.src
      this.image = image
      this.$emit('hasredaction', this.rects.length > 0)
    },
    toDataURL() {
      return this.$refs.canvas.toDataURL()
    },
    imageLoaded() {
      const { canvas } = this.$refs
      if (this.image.width > MAX_WIDTH) {
        canvas.height = Math.floor(
          this.image.height * (MAX_WIDTH / this.image.width)
        )
        canvas.width = MAX_WIDTH
      } else {
        canvas.width = this.image.width
        canvas.height = this.image.height
      }
      this.renderAndUpdate()
    },
    renderCanvas() {
      const { canvas } = this.$refs
      const ctx = canvas.getContext('2d')
      ctx.clearRect(0, 0, canvas.width, canvas.height) // clear canvas
      ctx.drawImage(
        this.image,
        0,
        0,
        this.image.width,
        this.image.height,
        0,
        0,
        canvas.width,
        canvas.height
      )
      if (this.rects.length > 0) {
        this.rects.forEach(({ topLeft, width, height }) => {
          ctx.beginPath()
          ctx.rect(topLeft.x, topLeft.y, width, height)
          ctx.fillStyle = 'black'
          ctx.fill()
        })
      }
    },
    scaleOffsets(e) {
      return this.scale(e, 'offsetX', 'offsetY')
    },
    scaleMovement(e) {
      return this.scale(e, 'movementX', 'movementY')
    },
    scale(e, varX, varY) {
      const { canvas } = this.$refs
      return {
        x: (e[varX] / canvas.clientWidth) * canvas.width,
        y: (e[varY] / canvas.clientHeight) * canvas.height
      }
    },
    isWithinRect(e, rect) {
      function between(x, n, m) {
        if (n < m) {
          return x >= n && x <= m
        }
        return x >= m && x <= n
      }
      const { x, y } = this.scaleOffsets(e)
      return (
        between(x, rect.topLeft.x, rect.topLeft.x + rect.width) &&
        between(y, rect.topLeft.y, rect.topLeft.y + rect.height)
      )
    },
    getIntersectingRects(e) {
      return this.rects
        .map((rect, index) => ({ rect, index }))
        .filter(({ rect }) => this.isWithinRect(e, rect))
        .map(({ index }) => index)
    },
    mousedown(e) {
      // only listen to left click
      if (e.button !== 0) {
        return
      }

      this.holding = true
      this.actives = this.getIntersectingRects(e)
      if (this.actives.length > 0) {
        this.moving = this.actives
        return
      }
      this.drawing = true
      this.rects.push({
        topLeft: this.scaleOffsets(e),
        width: 0,
        height: 0
      })
    },
    mousemove(e) {
      if (!this.holding) {
        const intersecting = this.getIntersectingRects(e)
        if (intersecting.length > 0) {
          this.cursor = 'grab'
        } else {
          this.cursor = 'crosshair'
        }
        return
      }
      if (this.moving) {
        this.cursor = 'grabbing'
        this.moving.forEach((index) => {
          const { x, y } = this.scaleMovement(e)
          this.rects[index].topLeft.x += x
          this.rects[index].topLeft.y += y
        })
        this.renderCanvas()
        return
      }
      this.cursor = 'crosshair'
      const { x, y } = this.scaleOffsets(e)
      const rect = this.rects[this.rects.length - 1]
      rect.width = x - rect.topLeft.x
      rect.height = y - rect.topLeft.y
      this.renderCanvas()
    },
    mouseup() {
      if (!this.holding) {
        return
      }
      this.holding = false
      this.drawing = false
      this.moving = null
      const last = this.rects[this.rects.length - 1]
      if (last.width === 0 || last.height === 0) {
        this.rects.pop()
      } else {
        this.$emit('hasredaction', this.rects.length > 0)
      }
      this.renderAndUpdate()
    },
    renderAndUpdate() {
      this.renderCanvas()
      this.$refs.canvas.toBlob(
        (blob) => {
          this.$emit('redacted', blob)
        },
        'image/jpeg',
        0.85
      )
    },
    revert() {
      this.rects.pop()
      this.$emit('hasredaction', this.rects.length > 0)
      this.renderAndUpdate()
    },
    deleteActives() {
      if (this.actives.length === 0) {
        return
      }

      this.rects = this.rects.filter(
        (rect, index) => !this.actives.includes(index)
      )
      this.renderCanvas()
    }
  },
  watch: {
    src() {
      this.startRedaction()
    }
  }
}
</script>
