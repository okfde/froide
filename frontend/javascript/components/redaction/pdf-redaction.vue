<template>
  <div
    id="pdf-viewer"
    ref="top"
    class="pdf-redaction-tool container-xxl bg-dark-subtle d-flex flex-column"
    :class="{ 'pdf-redaction-tool--debug': debug }"
  >
    <div v-if="hasPassword && ready" class="row">
      <div class="col">
        <div class="alert alert-info mb-0" role="alert">
          {{ i18n.hasPassword }}
        </div>
      </div>
    </div>
    <div v-if="message" class="row bg-light pt-2">
      <div class="col">
        <div class="alert alert-info mb-0" role="alert">
          {{ message }}
        </div>
      </div>
    </div>
    <div v-if="errors" class="row bg-light pt-2">
      <div class="col">
        <div class="alert alert-danger mb-0" role="alert">
          {{ errors }}
        </div>
      </div>
    </div>
    <div v-if="working" class="row py-3 text-bg-light">
      <div class="col">
        <div class="text-center">
          <h3 v-if="loading">
            {{ i18n.loadingPdf }}
          </h3>
          <h3 v-if="redacting">
            {{ i18n.redacting }}
          </h3>
          <h3 v-if="sending">
            {{ i18n.sending }}
          </h3>
        </div>
        <div
          class="progress"
          role="progressbar"
          :aria-valuenow="progressPercent"
          aria-valuemin="0"
          aria-valuemax="100"
        >
          <div
            class="progress-bar"
            :class="{
              'progress-bar-striped progress-bar-animated': progressUnknown
            }"
            :style="progressWidth"
          />
        </div>
        <div class="text-center mt-3">
          <div class="spinner-border" role="status" />
        </div>
      </div>
    </div>
    <div class="row toolbar sticky-top z-3">
      <div
        v-if="ready"
        class="btn-toolbar col justify-content-md-around justify-content-lg-between bg-light"
      >
        <div
          class="btn-group me-1 justify-content-center justify-content-lg-start py-2"
        >
          <input
            type="radio"
            class="btn-check"
            name="pdfredaction-tool"
            value="paint"
            id="btn-check-paint"
            v-model="tool"
          />
          <!-- Pan/move does not send focusout event to the tooltips, so on mobile,
            they overstay their welcome and get in the way. As a simple workaround,
            we make them autohide after a timeout. -->
          <label
            class="btn btn-outline-secondary d-flex"
            :title="i18n.redact"
            for="btn-check-paint"
          >
            <!-- browser hardcodedly vertically center text in <button>s, we try to match this visually via flex -->
            <div class="align-self-center">
              <i class="fa fa-lg fa-paint-brush" />
              <small class="d-none d-xl-block">{{ i18n.redact }}</small>
            </div>
          </label>
          <input
            type="radio"
            class="btn-check"
            name="pdfredaction-tool"
            value="move"
            id="btn-check-move"
            v-model="tool"
          />
          <label
            class="btn btn-outline-secondary d-flex"
            :title="i18n.moveTool"
            for="btn-check-move"
          >
            <!-- browser hardcodedly vertically center text in <button>s, we try to match this visually via flex -->
            <div class="align-self-center">
              <i class="fa fa-lg fa-arrows" />
              <small class="d-none d-xl-block">{{ i18n.moveTool }}</small>
            </div>
          </label>
        </div>
        <div
          class="btn-group me-1 justify-content-center justify-content-lg-start py-2"
        >
          <button
            type="button"
            class="btn btn-outline-secondary"
            :disabled="!canUndo"
            :title="i18n.undo"
            @click="undo"
          >
            <i class="fa fa-lg fa-share fa-flip-horizontal" />
            <small class="d-none d-xxl-block">{{ i18n.undo }}</small>
          </button>
          <button
            type="button"
            class="btn btn-outline-secondary"
            :disabled="!canRedo"
            data-bs-toggle="tooltip"
            data-bs-placement="top"
            :title="i18n.redo"
            @click="redo"
          >
            <i class="fa fa-lg fa-share" />
            <small class="d-none d-xxl-block">{{ i18n.redo }}</small>
          </button>
          <button
            type="button"
            class="btn btn-outline-secondary"
            :disabled="!canUndo"
            :title="i18n.removeAllRedaction"
            @click="undoAll"
          >
            <i class="fa fa-lg fa-trash" />
            <small class="d-none d-xxl-block">{{
              i18n.removeAllRedaction
            }}</small>
          </button>
        </div>

        <div class="btn-group me-1 toolbar-modes py-2">
          <button
            type="button"
            class="btn"
            :class="{
              'btn-outline-secondary': !textOnly,
              'btn-secondary': textOnly
            }"
            :title="i18n.toggleText"
            @click.stop="toggleText"
          >
            <i class="fa fa-align-justify" />
            <small class="d-none d-xl-block">{{ i18n.toggleText }}</small>
          </button>
          <button
            type="button"
            class="btn"
            :class="{
              'btn-outline-secondary': !textDisabled,
              'btn-secondary': textDisabled
            }"
            :title="i18n.disableText"
            @click.stop="toggleDrawing"
          >
            <i class="fa fa-image" />
            <small class="d-none d-xl-block">{{ i18n.disableText }}</small>
          </button>
        </div>

        <div
          v-if="!bottomToolbar"
          class="input-group me-1 justify-content-center justify-content-lg-start py-2"
        >
          <button
            class="pdf-prev btn btn-outline-secondary"
            :disabled="!hasPrevious"
            @click="goPrevious"
          >
            &laquo;
            <span class="visually-hidden">{{ i18n.previousPage }}</span>
          </button>
          <span class="input-group-text pageOfTotal">
            {{ pageOfTotal }}
          </span>
          <button
            class="pdf-next btn btn-outline-secondary"
            :disabled="!hasNext"
            @click="goNext"
          >
            <span class="visually-hidden">{{ i18n.nextPage }}</span>
            &raquo;
          </button>
        </div>

        <div
          v-if="
            !hideDoneButton &&
            (hasRedactions || hasPassword || (canPublish && !hasPassword))
          "
          class="btn-group mt-lg-0 py-2 mw-lg-50 mw-xl-25"
        >
          <button
            v-if="hasRedactions || hasPassword"
            class="btn btn-dark"
            @click="redact"
          >
            <i class="fa fa-check me-2" />
            <template v-if="hasRedactions">
              {{ i18n.redactAndPublish }}
            </template>
            <template v-else-if="hasPassword">
              {{ i18n.removePasswordAndPublish }}
            </template>
          </button>
          <form
            v-if="canPublish && !hasPassword && !hasRedactions"
            method="post"
            id="redaction-submit-form"
            :action="config.urls.publishUrl"
          >
            <input
              type="hidden"
              name="csrfmiddlewaretoken"
              :value="csrfToken"
            />
            <button
              class="btn btn-dark"
              type="submit"
              @click="confirmNoRedactions"
            >
              <i class="fa fa-check me-2" />{{ i18n.publishWithoutRedaction }}
            </button>
          </form>
        </div>
      </div>
    </div>
    <div class="row flex-grow-1">
      <div
        class="preview position-relative"
        :class="{
          ['preview--do-paint']: doPaint,
          ['preview--text-only']: textOnly
        }"
        ref="containerWrapper"
        @wheel="mouseWheel"
        @pointerleave="pointerLeaveWrapper"
      >
        <div
          class="position-absolute top-0 bottom-0 start-0 px-2 py-4"
          :class="{
            'pe-none': isDragging
          }"
        >
          <div class="d-flex flex-column position-sticky z-1 previewToolbar">
            <div class="btn-group-vertical w-auto position-sticky z-1">
              <button type="button" class="btn btn-secondary" @click="zoomIn()">
                <i class="fa fa-lg fa-plus" />
              </button>
              <button
                type="button"
                class="btn btn-secondary"
                @click="zoomReset()"
              >
                <i class="fa fa-lg fa-compress" />
              </button>
              <button
                type="button"
                class="btn btn-secondary"
                @click="zoomOut()"
              >
                <i class="fa fa-lg fa-minus" />
              </button>
            </div>
          </div>
        </div>
        <div
          class="position-static row py-3 h-100"
          @pointerdown="pointerDown"
          @pointerup="pointerUp"
          @pointermove="pointerMove"
        >
          <div
            :id="containerId"
            ref="container"
            class="redactContainer"
            :class="{ invisible: working }"
          >
            <canvas v-show="!textOnly" :id="canvasId" class="redactLayer" />
            <canvas
              v-show="!textOnly"
              :id="redactCanvasId"
              class="redactLayer"
            />
            <div
              :id="textLayerId"
              class="textLayer"
              ref="textLayer"
              :class="{ textActive: textOnly, textDisabled: textDisabled }"
            />
          </div>
        </div>
      </div>
    </div>
    <div v-if="bottomToolbar" class="row sticky-bottom z-2">
      <div v-if="ready" class="btn-toolbar col bg-light py-2">
        <div class="input-group me-auto ms-auto">
          <button
            class="pdf-prev btn btn-outline-secondary"
            :disabled="!hasPrevious"
            @click="goPrevious"
          >
            &laquo;
            <span class="d-none d-md-inline-block">{{
              i18n.previousPage
            }}</span>
          </button>
          <span class="input-group-text pageOfTotal">
            {{ pageOfTotal }}
          </span>
          <button
            class="pdf-next btn btn-outline-secondary"
            :disabled="!hasNext"
            @click="goNext"
          >
            <span class="d-none d-md-inline-block">{{ i18n.nextPage }}</span>
            &raquo;
          </button>
        </div>
      </div>
    </div>
    <ConfirmNoRedaction
      :i18n="config.i18n"
      ref="confirmmodal"
      @submit="submitRedactions"
    />
  </div>
</template>

<script>
import ConfirmNoRedaction from './confirm-no-redaction'

import PDFJSWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.js?url'

import Panzoom from '@panzoom/panzoom'

import range from 'lodash.range'

import { Modal } from 'bootstrap'

import { bustCache, getData } from '../../lib/api.js'
import { toRaw } from 'vue'

import { useAttachments } from '../docupload/lib/attachments.js'
const { fetchAttachment, approveAttachment } = useAttachments()

// help with only Text mode debugging: show non-OCR original + highlight spans/divs
const debug = false

// 1000px are good enough to redact an A4 page with 10pt text
const minRenderWidth = 1000

// factor; 1.4 will add 20% on top+bottom on the pure getBoundingRect
const lineHeight = 1.4

// add constant padding on left+right of pure getBoundingRect,
// factor of the longer page side
// 1/297 will add ~1mm (assuming DIN A4 as default)
const paddingUnit = 1 / 297

let renderDensityFactor

const scaleCssProp = (styleObject, propName, factor) => {
  const value = parseFloat(styleObject[propName])
  if (!isNaN(value)) {
    // we'll assume they're all in px
    styleObject[propName] = value * factor + 'px'
  }
}

function isTouchDevice() {
  return matchMedia('(pointer: coarse)').matches
}

let panzoom

let resizeTimeout = false

export default {
  name: 'PdfRedaction',
  components: { ConfirmNoRedaction },
  props: {
    config: {
      type: Object,
      required: true
    },
    pdfPath: {
      type: String,
      required: true
    },
    attachmentId: {
      type: Number,
      required: true
    },
    attachmentUrl: {
      type: String,
      required: true
    },
    postUrl: {
      type: String
    },
    autoApprove: {
      type: Boolean,
      default: true
    },
    noRedirect: {
      type: Boolean,
      default: false
    },
    redactRegex: {
      type: Array,
      default: () => []
    },
    canPublish: {
      type: Boolean,
      default: false
    },
    hideDoneButton: {
      type: Boolean,
      default: false
    },
    bottomToolbar: {
      type: Boolean,
      default: false
    }
  },
  emits: ['uploaded', 'hasredactionsupdate'],
  data() {
    return {
      debug,
      doc: null,
      attachment: null,
      currentPage: null,
      page: null,
      numPages: null,
      containerId: 'container-' + String(Math.random()).substr(2),
      canvasId: 'canvas-' + String(Math.random()).substr(2),
      redactCanvasId: 'redactCanvas-' + String(Math.random()).substr(2),
      textLayerId: 'textlayer-' + String(Math.random()).substr(2),
      workingState: 'loading',
      ready: false,
      pageLoading: false,
      textOnly: false,
      textDisabled: true,
      actionsPerPage: {},
      actionIndexPerPage: {},
      rectanglesPerPage: {},
      password: null,
      startDrag: null,
      endDrag: null,
      isDragging: false,
      initialAutoRedact: {},
      errors: null,
      message: null,
      progressCurrent: null,
      progressTotal: null,
      hasTouch: isTouchDevice(),
      tool: isTouchDevice() ? 'move' : 'paint',
      doubleTap: false,
      altKey: false
    }
  },
  computed: {
    i18n() {
      return this.config.i18n
    },
    hasNext() {
      return this.currentPage < this.numPages && !this.pageLoading
    },
    hasPrevious() {
      return this.currentPage > 1 && !this.pageLoading
    },
    canUndo() {
      return this.actionIndexPerPage[this.currentPage] > 0
    },
    canRedo() {
      const actions = this.actionsPerPage[this.currentPage]
      if (actions === undefined) {
        return false
      }
      return this.actionIndexPerPage[this.currentPage] < actions.length
    },
    hasRedactions() {
      for (const p in this.rectanglesPerPage) {
        if (this.rectanglesPerPage[p].length > 0) {
          return true
        }
      }
      return false
    },
    hasPassword() {
      return this.password !== null
    },
    pageOfTotal() {
      if (this.numPages !== null) {
        return this.i18n.pageCurrentOfTotal
          .replace(/\$current/, this.currentPage)
          .replace(/\$total/, this.numPages)
      }
      return ''
    },
    regexList() {
      return this.redactRegex
        .map((r) => {
          r = r.replace(/ /g, '\\s+')
          if (r.length < 2) {
            return null
          }
          r = `\\b${r}\\b`
          return new RegExp(r, 'gi')
        })
        .filter((r) => r !== null)
    },
    container() {
      return this.$refs.container
    },
    canvas() {
      return document.getElementById(this.canvasId)
    },
    redactCanvas() {
      return document.getElementById(this.redactCanvasId)
    },
    textLayer() {
      return document.getElementById(this.textLayerId)
    },
    working() {
      return this.workingState !== null
    },
    loading() {
      return this.workingState === 'loading'
    },
    redacting() {
      return this.workingState === 'redacting'
    },
    sending() {
      return this.workingState === 'sending'
    },
    progressUnknown() {
      return this.progressCurrent === null || this.progressTotal === undefined
    },
    progressPercent() {
      if (!this.progressUnknown) {
        return (this.progressCurrent / this.progressTotal) * 100
      }
      return 100
    },
    progressWidth() {
      return `width: ${this.progressPercent}%`
    },
    csrfToken() {
      return document.querySelector('[name=csrfmiddlewaretoken]').value
    },
    doPaint() {
      return this.tool === 'paint'
    }
  },
  watch: {
    hasRedactions(newValue) {
      this.$emit('hasredactionsupdate', newValue)
    },
    doPaint(doPaint) {
      this.updateMode(doPaint)
    },
    altKey(altKey) {
      this.tool = altKey ? 'move' : 'paint'
    }
  },
  async created() {
    import('pdfjs-dist')
      .then((PDFJS) => {
        this.PDFJS = PDFJS
        this.PDFJS.GlobalWorkerOptions.workerSrc = PDFJSWorkerUrl
        console.log(PDFJSWorkerUrl, this.PDFJS)
        this.loadDocument().then(() => this.loadPage(1))
      })
      .catch((err) => {
        console.log(err)
      })
    this.attachment = await fetchAttachment(this.attachmentId)
  },
  mounted() {
    document.addEventListener('keydown', this.setAltKey)
    document.addEventListener('keyup', this.setAltKey)
    window.addEventListener('resize', this.reloadPageAfterResizeDebounced)

    panzoom = Panzoom(this.$refs.container, {
      canvas: true,
      pinchAndPan: true,
      cursor: 'move',
      noBind: true
    })
    this.updateMode(this.doPaint)
  },
  beforeUnmount() {
    document.removeEventListener('keydown', this.setAltKey)
    document.removeEventListener('keyup', this.setAltKey)
    window.removeEventListener('resize', this.reloadPageAfterResizeDebounced)
  },
  methods: {
    loadDocument() {
      const loadingTask = this.PDFJS.getDocument({
        url: this.pdfPath,
        isEvalSupported: false,
        httpHeaders: {
          pragma: 'no-cache',
          'cache-control': 'no-cache'
        }
      })
      loadingTask.onPassword = (passwordFunc, reason) => {
        let password
        if (reason === 1) {
          // need a password
          password = window.prompt(this.i18n.passwordRequired)
        }
        if (reason !== 1 || !password) {
          if (window.confirm(this.i18n.passwordCancel)) {
            this.errors = this.i18n.passwordMissing
            this.workingState = null
            this.ready = false
            return
          }
          password = window.prompt(this.i18n.passwordRequired)
        }
        this.password = password
        passwordFunc(password)
      }
      loadingTask.onProgress = (progress) => {
        this.progressCurrent = progress.loaded
        this.progressTotal = progress.total
      }
      return loadingTask.promise.then((pdfDocument) => {
        this.workingState = null
        this.ready = true
        this.doc = pdfDocument
        this.numPages = this.doc.numPages

        for (let i = 1; i <= this.numPages; i += 1) {
          this.actionsPerPage[i] = []
          this.actionIndexPerPage[i] = 0
        }
        this.currentPage = 1
      })
    },
    loadPage(pageNum) {
      this.pageLoading = true
      const doc = toRaw(this.doc)
      return doc.getPage(pageNum).then((page) => {
        this.page = page

        let maxWidth = this.$refs.containerWrapper.offsetWidth
        if (!this.$refs.containerWrapper) {
          console.error('containerWrapper is null?')
        }
        // subtract the paddings (from bootstrap's row child),
        // fall back to the value calculated in default settings (like base font size)
        // note: paddingLeft is the value set in CSS, so something like "12px",
        //   unlike offsetWidth, still this value is consistent across page zoom
        maxWidth -=
          parseInt(
            window.getComputedStyle(this.$refs.containerWrapper)?.paddingLeft
          ) * 2 || 24

        // We render/raster the PDF to roughly "viewport width pixels",
        // which is too low to be useful on mobile,
        // so we bump up the density on screens < minRenderWidth,
        // so the render fills the minRenderWidth.
        // On screens above, we use the full width
        // (which is capped by bootstrap container to ~1300px).
        // We could improve quality/comfort by further bumping the density
        // - on highdpi displays (e.g. by DPR or just 2x),
        // - or to leave headroom for zoom (e.g. sqrt(2)x for 1 level)
        // - but would have to limit effective canvas size to prevent crashes
        renderDensityFactor = Math.max(minRenderWidth / window.innerWidth, 1.0)

        // normalized to positive degrees, e.g. -90 ⇒ 270
        const rotation = (page.rotate + 360) % 360
        // is the page rotated by ±{90, 270}?
        const flipWidthHeight = rotation % 180 === 90
        this.intrinsicPageWidth = flipWidthHeight ? page.view[3] : page.view[2]
        this.intrinsicPageHeight = flipWidthHeight ? page.view[2] : page.view[3]

        // redaction "rects'" coordinates are stored in "intrinsic PDF viewport = document pixels",
        // and not in "browser/device pixels"
        // (which are affected by page zoom, bootstrap viewports and rendering artifacts)
        // so scaleFactor needs to be respected in many calculations in the component
        // (to "(re)project" between the two views)
        this.scaleFactor = (renderDensityFactor * maxWidth) / this.intrinsicPageWidth
        const viewport = page.getViewport({ scale: this.scaleFactor })

        this.viewport = viewport
        const canvas = this.canvas
        canvas.width = viewport.width
        canvas.height = viewport.height
        this.redactCanvas.width = viewport.width
        this.redactCanvas.height = viewport.height
        const wPx = viewport.width / renderDensityFactor + 'px'
        const hPx = viewport.height / renderDensityFactor + 'px'
        console.log('PdfRedaction loadPage', {
          flipWidthHeight,
          page,
          viewport,
          renderDensityFactor,
          scaleFactor: this.scaleFactor,
          maxWidth,
          canvasViewportSize: [viewport.width, viewport.height],
          canvasCss: [wPx, hPx],
          pageSize: [this.intrinsicPageWidth, this.intrinsicPageHeight]
        })
        canvas.style.width = wPx
        canvas.style.height = hPx
        this.redactCanvas.style.width = wPx
        this.redactCanvas.style.height = hPx
        this.textLayer.style.width = wPx
        this.textLayer.style.height = hPx
        this.container.style.width = wPx
        this.container.style.height = hPx
        this.zoomReset()
        const ctx = canvas.getContext('2d')
        const renderTask = page.render({
          canvasContext: ctx,
          viewport
        })
        const textPromise = page.getTextContent().then((content) => {
          // Content contains lots of information about the text layout and
          // styles, but we need only strings at the moment
          // remove all text layer elements
          while (this.textLayer.firstChild) {
            this.textLayer.removeChild(this.textLayer.firstChild)
          }
          // Rendering text layer as HTML.
          const task = this.PDFJS.renderTextLayer({
            textContent: content,
            container: this.textLayer,
            viewport,
            enhanceTextSelection: true
          })
          return task.promise
        })
        return Promise.all([renderTask.promise, textPromise])
          .then(this.textAvailable)
          .then(() => {
            this.pageLoading = false
          })
      })
    },
    reloadCurrentPage() {
      this.loadPage(this.currentPage)
    },
    goNext() {
      if (this.hasNext) {
        this.setCurrentPage(this.currentPage + 1)
      }
    },
    goPrevious() {
      if (this.hasPrevious) {
        this.setCurrentPage(this.currentPage - 1)
      }
    },
    setCurrentPage(pageNum) {
      this.currentPage = pageNum
      // Reset dragging before loading new page
      this.cancelDrag()
      return this.loadPage(pageNum)
    },
    toggleText() {
      this.cancelDrag()
      this.textOnly = !this.textOnly
      this.textDisabled = !this.textOnly
    },
    toggleDrawing() {
      this.cancelDrag()
      this.textDisabled = !this.textDisabled
      this.textOnly = !this.textDisabled
    },
    async redactOrApprove() {
      if (this.hasRedactions || this.hasPassword) {
        // .redact() handles autoApprove
        return this.redact()
      }
      if (this.autoApprove) {
        return this.approve()
      }
    },
    approve() {
      return approveAttachment(this.attachment).then(() => {
        this.$emit('uploaded')
      })
    },
    redact() {
      this.$refs.top.scrollIntoView({ behavior: 'smooth', block: 'start' })
      this.ready = false
      this.workingState = 'sending'
      this.progressCurrent = 0
      this.progressTotal = this.numPages + 1
      const pages = range(1, this.numPages + 1)
      const serialized = []
      return pages
        .reduce((sequence, pageNumber) => {
          return sequence.then(() => {
            return this.setCurrentPage(pageNumber).then(() => {
              this.progressCurrent = pageNumber
              serialized.push(this.serializePage(pageNumber))
            })
          })
        }, Promise.resolve())
        .then(() => {
          console.log(serialized)
          const data = {
            pages: serialized,
            password: this.password,
            auto_approve: this.autoApprove
          }
          this.progressCurrent = null
          return this.sendSerializedPages(data)
            .then((attachment) => {
              if (attachment) {
                this.progressCurrent = 100
                this.progressTotal = 100
                bustCache(attachment.file_url).then(() => {
                  if (this.noRedirect) {
                    this.$emit('uploaded')
                    return
                  }
                  document.location.href = this.config.urls.messageUpload
                })
              } else {
                this.workingState = null
                this.errors = this.i18n.redactionTimeout
                this.$refs.top.scrollIntoView(true)
              }
            })
            .catch((err) => {
              this.workingState = null
              console.error(err)
              this.ready = false
              this.errors = err
              this.$refs.top.scrollIntoView(true)
            })
        })
    },
    sendSerializedPages(serialized) {
      this.workingState = 'sending'
      this.progressCurrent = 5 // show at least some progress
      this.progressTotal = 100
      return new Promise((resolve, reject) => {
        const xhr = new window.XMLHttpRequest()
        const url = this.postUrl || document.location.href
        xhr.open('POST', url)
        xhr.setRequestHeader('Content-Type', 'application/json')
        xhr.setRequestHeader('X-CSRFToken', this.csrfToken)
        const xhrUpload = xhr.upload ? xhr.upload : xhr
        xhrUpload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            this.progressCurrent = e.loaded
            this.progressTotal = e.total
          } else {
            this.progressCurrent = null
          }
        })
        xhr.onreadystatechange = () => {
          if (xhr.readyState === 4) {
            if (xhr.status === 200) {
              try {
                this.progressCurrent = null
                this.workingState = 'redacting'
                this.waitOnAttachment(
                  JSON.parse(xhr.responseText),
                  serialized.auto_approve
                )
                  .then(resolve)
                  .catch(reject)
              } catch (e) {
                console.error('Failed to decode JSON', e, xhr.responseText)
                reject(this.i18n.redactionError)
              }
            } else {
              console.error('Non 200 response code', xhr.status)
              reject(this.i18n.redactionError)
            }
          }
        }
        xhr.send(JSON.stringify(serialized))
      })
    },
    waitOnAttachment(response, wasAutoApprove) {
      return new Promise((resolve, reject) => {
        const attachmentUrl = response.resource_uri
        let waitTime = 0
        const checkAttachment = () => {
          getData(attachmentUrl)
            .then((attachment) => {
              if (
                attachment.pending ||
                (wasAutoApprove && !attachment.approved)
              ) {
                waitTime += 5
                if (waitTime > 60 * 3) {
                  console.error('Timeout while waiting for redaction')
                  return reject(this.i18n.redactionTimeout)
                }
                if (this.errors === null) {
                  window.setTimeout(checkAttachment, 5 * 1000)
                }
                return
              }
              console.info('Attachment redacted.')
              resolve(attachment)
            })
            .catch(() => {
              console.err('Could not get attachment via API')
              return reject(this.i18n.redactionError)
            })
        }
        window.setTimeout(checkAttachment, 1000)
      })
    },
    serializePage(pageNumber) {
      const divs = this.textLayer.children
      const texts = Array.prototype.map.call(divs, (d) => {
        const pos = this.getDivRect(d)
        return {
          pos,
          fontSize: d.style.fontSize,
          text: d.textContent,
          // transform + fontFamily are ignored by add_text_on_pdf/redact.py; rotated boxes/pages won't match up
          // but moot because the text is invisible anyway?
          transform: d.style.transform,
          fontFamily: d.style.fontFamily
        }
      })
      return {
        width: this.intrinsicPageWidth,
        height: this.intrinsicPageHeight,
        pageNumber,
        rects: this.rectanglesPerPage[pageNumber],
        texts
      }
    },
    getOffset(e) {
      const target = e.target || e.srcElement
      const rect = target.getBoundingClientRect()
      let clientX = e.clientX
      let clientY = e.clientY
      if (e.touches && e.touches.length > 0) {
        clientX = e.touches[0].clientX
        clientY = e.touches[0].clientY
      } else if (e.changedTouches && e.changedTouches.length > 0) {
        clientX = e.changedTouches[0].clientX
        clientY = e.changedTouches[0].clientY
      }

      const scale = panzoom.getScale()
      const offsetX = (renderDensityFactor * (clientX - rect.left)) / scale
      const offsetY = (renderDensityFactor * (clientY - rect.top)) / scale
      return [offsetX, offsetY]
    },
    cancelDrag() {
      this.startDrag = null
      this.endDrag = null
    },
    mouseMove(e, override) {
      if (this.hasTouch && !override) {
        return
      }
      if (this.startDrag === null) {
        return
      }
      const selection = window.getSelection()
      if (!selection.isCollapsed) {
        return
      }
      this.endDrag = this.getOffset(e)
      this.drawRectangles()
    },
    mouseDown(e, override) {
      // throw out right/middle/context clicks
      if (e.button !== 0) return
      if (!this.doPaint && !override) {
        return
      }
      this.startDrag = this.getOffset(e)
      this.endDrag = null
    },
    mouseUp(_e, override) {
      if (this.hasTouch && !override) {
        return
      }
      const selection = window.getSelection()

      if (selection !== undefined && !selection.isCollapsed) {
        console.log(selection)
        this.startDrag = null
        this.handleSelection(selection)
        selection.removeAllRanges()
        return
      }

      if (this.startDrag === null) {
        return
      }

      const endDrag = this.endDrag
      this.endDrag = null
      if (endDrag === null) {
        console.log('Cancel malformed select')
        return
      }
      if (
        Math.abs(endDrag[0] - this.startDrag[0]) < 3 &&
        Math.abs(endDrag[1] - this.startDrag[1]) < 3
      ) {
        console.log('Cancel empty select')
        this.startDrag = null
        return
      }
      // getRect is "device vs document pixel" agnostic;
      // startDrag and endDrag are renderDensityFactor-aware, but not scaleFactor
      const [rx, ry, rw, rh] = this.getRect(this.startDrag, endDrag)
      if (isNaN(parseFloat(rx)) || isNaN(parseFloat(ry))) {
        return
      }
      const f = 1 / renderDensityFactor
      const x = rx * f
      const y = ry * f
      const w = rw * f
      const h = rh * f

      // find overlapping text and remove it completely
      const divs = this.textLayer.children
      const matches = Array.prototype.filter.call(divs, (d) => {
        const [dx, dy, dw, dh] = this.getDivRect(d)
        return x < dx + dw && x + w > dx && y < dy + dh && y + h > dy
      })
      const texts = matches.map((d) => {
        const action = this.redactText(d, 0, d.textContent)
        return action.texts[0]
      })

      this.addAction({
        type: 'redact',
        rects: [[rx / this.scaleFactor, ry / this.scaleFactor, rw / this.scaleFactor, rh / this.scaleFactor]],
        page: this.currentPage,
        texts
      })
      this.startDrag = null
    },
    pointerDown(e) {
      this.isDragging = true
      if (!this.doPaint) {
        panzoom.handleDown(e)
        return
      }
      // only click on canvas starts painting a rectangle
      if (e.target.tagName !== 'CANVAS') {
        return
      }
      this.mouseDown(e, true)
    },
    pointerUp(e) {
      this.isDragging = false
      if (!this.doPaint) {
        panzoom.handleUp(e)
        return
      }
      this.mouseUp(e, true)
    },
    pointerMove(e) {
      if (!this.doPaint) {
        panzoom.handleMove(e)
        return
      }
      // only click on canvas starts painting a rectangle
      if (e.target.tagName !== 'CANVAS') {
        return
      }
      this.mouseMove(e, true)
    },
    pointerLeaveWrapper(e) {
      this.isDragging = false
      if (!this.doPaint) {
        panzoom.handleUp(e)
      }
      this.mouseUp(e, true)
    },
    mouseWheel(e) {
      if (!this.doPaint) {
        panzoom.zoomWithWheel(e)
      }
    },
    zoomReset() {
      panzoom.reset({ force: true })
    },
    zoomIn() {
      panzoom.zoomIn({ force: true })
    },
    zoomOut() {
      panzoom.zoomOut({ force: true })
    },
    getRect(start, end) {
      let x, y, w, h
      if (start[0] < end[0]) {
        x = start[0]
        w = end[0] - x
      } else {
        x = end[0]
        w = start[0] - x
      }
      if (start[1] < end[1]) {
        y = start[1]
        h = end[1] - y
      } else {
        y = end[1]
        h = start[1] - y
      }
      return [x, y, w, h]
    },
    handleSelection(selection) {
      function getNextNode(node) {
        if (node.firstChild) {
          return node.firstChild
        }
        while (node) {
          if (node.nextSibling) {
            return node.nextSibling
          }
          node = node.parentNode
        }
      }

      function getNodesInRange(range) {
        const start = range.startContainer
        const end = range.endContainer
        const commonAncestor = range.commonAncestorContainer
        const nodes = []
        let node

        // walk parent nodes from start to common ancestor
        for (node = start.parentNode; node; node = node.parentNode) {
          nodes.push(node)
          if (node === commonAncestor) {
            break
          }
        }
        nodes.reverse()
        // walk children and siblings from start until end is found
        for (node = start; node; node = getNextNode(node)) {
          nodes.push(node)
          if (node === end) {
            break
          }
        }

        return nodes
      }

      const actions = []

      for (let i = 0; i < selection.rangeCount; i += 1) {
        const range = selection.getRangeAt(i)
        if (range.isCollapsed) {
          continue
        }
        // Easy if start and end same container
        if (range.startContainer === range.endContainer) {
          let node = range.startContainer
          if (node.nodeName === '#text') {
            node = node.parentNode
          }
          const action = this.redactRange(
            node,
            range.startOffset,
            range.endOffset
          )
          if (action !== null) {
            actions.push(action)
          }
          continue
        }
        // FIXME: weird other logic
        // from here https://stackoverflow.com/questions/667951/how-to-get-nodes-lying-inside-a-range-with-javascript
        const nodes = getNodesInRange(range)
        nodes.forEach((node) => {
          let start = 0
          let end = 0
          if (node.textContent !== null) {
            end = node.textContent.length
          }
          if (node === range.startContainer) {
            start = range.startOffset
          } else if (node === range.endContainer) {
            end = node.endOffset
          }
          if (node.nodeName === '#text') {
            node = node.parentNode
          }
          // console.log(node, start, end)
          if (
            node === null ||
            node.dataset === undefined ||
            node.dataset.index === undefined
          ) {
            return
          }
          const action = this.redactRange(node, start, end)
          if (action !== null) {
            actions.push(action)
          }
        })
      }
      const action = this.combineActions(actions)
      this.addAction(action)
    },
    combineActions(actions) {
      const texts = actions.reduce((a, b) => a.concat(b.texts), [])
      const rects = actions.reduce((a, b) => a.concat(b.rects), [])
      return {
        type: 'redact',
        texts,
        rects,
        page: this.currentPage
      }
    },
    textAvailable() {
      // mark every div with an index number
      // and shrink according to renderDensityFactor
      let i = 0
      let debugDiv
      if (debug) {
        debugDiv = document.createElement('div')
        debugDiv.id = 'getDivRect'
        this.container.appendChild(debugDiv)
      }
      Array.prototype.forEach.call(this.textLayer.children, (c) => {
        c.dataset.index = i
        i += 1
        scaleCssProp(c.style, 'left', 1 / renderDensityFactor)
        scaleCssProp(c.style, 'top', 1 / renderDensityFactor)
        scaleCssProp(c.style, 'fontSize', 1 / renderDensityFactor)
        if (debug) {
          c.onmouseenter = () => {
            const cRect = this.getDivRect(c)
            debugDiv.style.left = cRect[0] + 'px'
            debugDiv.style.top = cRect[1] + 'px'
            debugDiv.style.width = cRect[2] + 'px'
            debugDiv.style.height = cRect[3] + 'px'
          }
        }
      })
      if (this.initialAutoRedact[this.currentPage] === undefined) {
        this.regexList.forEach((r) => this.autoRedact(r))
        this.initialAutoRedact[this.currentPage] = true
      }
      this.applyActionsOnPageLoad()
    },
    drawRectangle(ctx, rect, doScale = false) {
      const [x, y, w, h] = rect
      const f = doScale ? this.scaleFactor : 1
      ctx.fillStyle = '#000'
      ctx.fillRect(x * f, y * f, w * f, h * f)
    },
    drawRectangles() {
      const ctx = this.redactCanvas.getContext?.('2d')
      if (!ctx) {
        console.log('drawRectangel assume text mode, bail')
        return
      }
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height)
      if (this.rectanglesPerPage[this.currentPage] !== undefined) {
        this.rectanglesPerPage[this.currentPage].forEach((r) => {
          this.drawRectangle(ctx, r, true)
        })
      }
      if (this.startDrag && this.endDrag) {
        this.drawRectangle(
          ctx,
          this.getRect(this.startDrag, this.endDrag),
          false
        )
      }
    },
    applyActionsOnPageLoad() {
      if (this.rectanglesPerPage[this.currentPage] === undefined) {
        this.rectanglesPerPage[this.currentPage] = []
      }
      this.actionsPerPage[this.currentPage].forEach((a) => {
        this.applyAction(a, true)
      })
      this.drawRectangles()
    },
    undo() {
      if (!this.canUndo) {
        return
      }
      let actionIndex = this.actionIndexPerPage[this.currentPage]
      actionIndex -= 1
      this.actionIndexPerPage[this.currentPage] = actionIndex
      const lastAction = this.actionsPerPage[this.currentPage][actionIndex]
      this.unapplyAction(lastAction)
    },
    undoAll() {
      while (this.canUndo) {
        this.undo()
      }
    },
    redo() {
      if (!this.canRedo) {
        return
      }
      let actionIndex = this.actionIndexPerPage[this.currentPage]
      const nextAction = this.actionsPerPage[this.currentPage][actionIndex]
      actionIndex += 1
      this.actionIndexPerPage[this.currentPage] = actionIndex
      this.applyAction(nextAction)
    },
    addAction(action) {
      let actions = this.actionsPerPage[action.page].slice()
      actions = actions.slice(0, this.actionIndexPerPage[action.page])
      actions.push(action)
      this.actionsPerPage[action.page] = actions

      this.actionIndexPerPage[action.page] =
        this.actionsPerPage[action.page].length

      this.applyAction(action)
    },
    applyAction(action, ignoreRects = false) {
      if (this.rectanglesPerPage[action.page] === undefined) {
        this.rectanglesPerPage[action.page] = []
      }
      if (action.rects !== undefined && !ignoreRects) {
        this.rectanglesPerPage[action.page] = [
          ...this.rectanglesPerPage[action.page],
          ...action.rects
        ]
        this.drawRectangles()
      }
      if (action.texts !== undefined && action.texts.length > 0) {
        action.texts.forEach((a) => {
          const div = this.textLayer.querySelector(
            `[data-index="${a.textIndex}"]`
          )
          if (div !== null) {
            div.textContent = a.textAfter
          }
        })
      }
    },
    unapplyAction(action) {
      if (action.rects !== undefined && action.rects.length > 0) {
        const newRects = this.rectanglesPerPage[action.page].filter((r) => {
          return (
            action.rects.filter((ar) => {
              const [x1, y1, w1, h1] = ar
              const [x2, y2, w2, h2] = r
              return x1 === x2 && y1 === y2 && w1 === w2 && h1 === h2
            }).length === 0
          )
        })
        this.rectanglesPerPage[action.page] = newRects
        this.drawRectangles()
      }
      if (action.texts !== undefined && action.texts.length > 0) {
        action.texts.forEach((a) => {
          const div = this.textLayer.querySelector(
            `[data-index="${a.textIndex}"]`
          )
          if (div !== null) {
            div.textContent = a.textBefore
          }
        })
      }
    },
    autoRedact(regex) {
      const divs = this.textLayer.children
      const matchFunc = (node) => node.textContent.match(regex)
      const matches = Array.prototype.filter.call(divs, matchFunc)
      matches.forEach((div) => {
        const text = div.textContent
        let result

        while ((result = regex.exec(text))) {
          const pos = result.index
          const match = result[0]
          const action = this.redactText(div, pos, match)
          if (action !== null) {
            this.addAction(action)
          }
        }
      })
      if (matches.length > 0) {
        this.message = this.i18n.autoRedacted
      }
    },
    getDivRect(div) {
      // more exact than clientLeft/offsetTop, which are ints
      const divRect = div.getBoundingClientRect()
      const parentRect = this.textLayer.getBoundingClientRect()
      const f = this.scaleFactor / renderDensityFactor // renderDensityFactor //  * scale
      const fx = f * this.intrinsicPageWidth / parentRect.width
      const fy = f * this.intrinsicPageHeight / parentRect.height
      const w = fx * divRect.width
      const h = fy * divRect.height
      const x = (divRect.left - parentRect.left)  * fx
      const y = (divRect.top - parentRect.top)  * fy
      return [x, y, w, h]
    },
    redactText(div, start, text) {
      return this.redactRange(div, start, start + text.length)
    },
    redactRange(div, start, end) {
      /*
        Measure the size of the match for the div
        Measure the offset of the match in the div
        Measure the size of a full redaction block
        Draw black rectangle on the canvas
        Replace text with redaction blocks of appropriate size
      */
      const blocks = [
        '\u2588',
        '\u2589',
        '\u258a',
        '\u258b',
        '\u258c',
        '\u258d',
        '\u258e',
        '\u258f'
      ]
      const blockSizes = [1, 7 / 8, 3 / 4, 5 / 8, 1 / 2, 3 / 8, 1 / 4, 1 / 8]
      const text = div.textContent
      const match = text.substr(start, end - start)

      div.textContent = blocks[0]
      const blockWidth = div.offsetWidth

      div.textContent = match
      const matchWidth = div.offsetWidth

      let replace = ''
      let fillWidth = matchWidth
      let blockIndex = 0
      while (blockIndex < blocks.length && fillWidth > 0) {
        const blockSize = blockWidth * blockSizes[blockIndex]
        if (blockSize > fillWidth) {
          blockIndex += 1
          continue
        }
        const n = Math.floor(fillWidth / blockSize)
        replace += blocks[blockIndex].repeat(n)
        fillWidth = (fillWidth % blockSize) / blockSize
        blockIndex += 1
      }

      const [baseX, baseY, baseWidth, baseHeight] = this.getDivRect(div)

      if (isNaN(baseX) || isNaN(baseY)) {
        console.warn('redactRage: getDivRect failed, bailing')
        return null
      }

      let width
      let height
      let x
      let y
      const padding = Math.max(this.intrinsicPageWidth, this.intrinsicPageHeight) * paddingUnit
      let paddingX = 0
      let paddingY = 0
      let dir
      const f1 = renderDensityFactor / this.scaleFactor
      // raw getBoundingClientRects, unlike getDivRect, are affected by panzoom's scale/zoom
      const f2  = f1 / panzoom.getScale()

      // PDFjs stretches lines; this is not reflected in offsetWidth
      // approach without getBoundlingClientRect:
      // const scaleX = parseFloat(div.style.transform?.match(/scaleX\(([\d.]+)\)/)?.[1]) || 1.0

      // we temporarily reset the text in its div to measure where the matched selected part begins
      // 200b is ZeroWidthSpace, to avoid the box losing its height (later needed for calculations;
      // we can ignore collapsing whitespace, since the box has white-space:pre)
      div.textContent = text.substr(0, start) || '\u200b'
      const startRect = div.getBoundingClientRect()
      // reset again to measure where matched part ends
      div.textContent = text.substr(0, start + match.length)
      const endRect = div.getBoundingClientRect()
      // and finally revert div's text
      div.textContent = text

      // we compare the two measured rects to figure out their intersection,
      // respecting the four directions
      // note how vertical/horizontal are not perfectly inverses;
      // due to how PDFjs handles x/y vs width/height - only one is rotated
      if (startRect.width !== endRect.width) {
        // horizontal, ltr or rtl
        if (startRect.x === endRect.x) {
          dir = 'ltr'
          x = baseX * f1 + startRect.width * f2
        } else {
          dir = 'rtl'
          x = baseX * f1 + baseWidth * f1 - endRect.width * f2
        }
        y = baseY * f1
        width = Math.abs(startRect.width - endRect.width) * f2
        height = baseHeight * f1
        // factor in line height, shift away from center first
        y -= height * ((lineHeight - 1.0) / 2)
        height *= lineHeight
        paddingX = padding
      } else {
        // vertical, top-to-bottom or bottom-to-top
        if (startRect.y === endRect.y) {
          dir = 'ttb'
          y = baseY * f1 + startRect.height * f2
        } else {
          dir = 'btt'
          y = baseY * f1 + baseHeight * f1 - endRect.height * f2
        }
        x = baseX * f1
        width = baseWidth * f1
        height = Math.abs(startRect.height - endRect.height) * f2
        x -= width * ((lineHeight - 1.0) / 2)
        width *= lineHeight
        paddingY = padding
      }

      console.log('redactRange', { scaleFactor: this.scaleFactor, renderDensityFactor, startRect, endRect, dir, baseX, baseY, baseWidth, baseHeight, x, y, width, height, padding, paddingUnit, paddingX, paddingY })

      return {
        type: 'redact',
        texts: [
          {
            textIndex: div.dataset.index,
            textBefore: text,
            // TODO: replace all occurences of match
            textAfter: text.replace(match, replace)
          }
        ],
        rects: [[
          x - paddingX,
          y - paddingY,
          width + paddingX * 2,
          height + paddingY * 2,
        ]],
        page: this.currentPage
      }
    },
    confirmNoRedactions(event) {
      if (this.hasRedactions) {
        event.preventDefault()
        const modal = Modal.getOrCreateInstance(this.$refs.confirmmodal.$el)
        modal.show()
      }
      if (this.noRedirect) {
        event.preventDefault()
        this.redactOrApprove()
      }
    },
    submitRedactions() {
      if (this.noRedirect) {
        this.redactOrApprove()
        return
      }
      document.getElementById('redaction-submit-form').submit()
    },
    updateMode(paint) {
      if (paint) {
        panzoom.setOptions({
          disableZoom: true,
          disablePan: true,
          cursor: 'auto'
        })
      } else {
        panzoom.setOptions({
          disableZoom: false,
          disablePan: false,
          cursor: 'move'
        })
      }
    },
    setAltKey(e) {
      if (this.doPaint || !e.altKey) this.altKey = e.altKey

      this.startDrag = null
      this.endDrag = null

      this.drawRectangles()
    },
    reloadPageAfterResizeDebounced() {
      if (resizeTimeout) {
        console.log('debounce resize timeout')
        window.clearTimeout(resizeTimeout)
      }
      resizeTimeout = window.setTimeout(() => {
        this.reloadCurrentPage()
        resizeTimeout = false
      }, 500)
    }
  }
}
</script>

<style lang="scss" scoped>
@import '../../../styles/variables';

.pdf-redaction-tool {
  min-height: calc(100vh - 10em);
}

.toolbar {
  padding: 5px;
  background-color: var(--#{$prefix}body-bg);
}

.toolbar button {
  hyphens: none;
}

.toolbar form {
  display: flex;
  display: contents;
}

.redactContainer {
  position: relative;
  padding: 0;
  margin: 0 auto;
}

.textLayer,
.redactLayer {
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
}

// user-select is usually disabled so it does not interfere with drag-to-pan.
// In textOnly mode, we need to allow it, but only then, and only when doPaint
// Otherwise, Firefox likes to select the whole div.redactContainer
// when the dragging cursor crosses the middle of the div.
// The whole div is then removed by selection.removeAllRanges()
.preview--do-paint.preview--text-only[style],
.preview--do-paint.preview--text-only .redactContainer[style] {
  user-select: text !important;
}

.preview--do-paint .redactLayer {
  cursor: crosshair;
}

.textLayer {
  opacity: 0.2;
  line-height: 1;
  background: white;
}

.textLayer > :deep(div),
.textLayer > :deep(span),
.textLayer > :deep(br) {
  color: transparent;
  position: absolute;
  white-space: pre;
  cursor: text;
  transform-origin: 0% 0%;
}

.preview:not(.preview--do-paint) {
  .textLayer > :deep(div),
  .textLayer > :deep(span),
  .textLayer > :deep(br) {
    pointer-events: none;
  }
}

.textLayer.textActive {
  opacity: 1;
}
.textLayer.textDisabled {
  visibility: hidden;
}

.textLayer.textActive > :deep(div),
.textLayer.textActive > :deep(span) {
  color: #000;
}

.toolbar {
  padding: 0;
}

.preview {
  box-shadow: inset 0 1em 1em -1em rgba(0, 0, 0, 0.5);
}

.previewToolbar {
  // leave enough space for the toolbars
  // (which break/wrap on narrow viewports)
  top: 8em;
  bottom: 0;
}

.pageOfTotal {
  // reduces jitter when variable-width numbers change
  font-variant-numeric: tabular-nums;
}

.pdf-redaction-tool--debug {
  // for onlyText show non-OCR original + highlight spans/divs on top

  .textLayer[style] {
    background: rgba(255, 255, 255, 0.2) !important;
  }

  .textLayer :deep(span) {
    outline: 1px solid red;
  }

  canvas.redactLayer {
    display: block !important;
  }

  :deep(#getDivRect) {
    position: absolute;
    top: 0;
    left: 0;
    width: 0;
    height: 0;
    z-index: 100;
    outline: 1px solid magenta;
    transition: all 400ms;
    pointer-events: none;
  }
}

</style>
