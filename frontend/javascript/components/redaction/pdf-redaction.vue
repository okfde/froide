<template>
  <div
    id="pdf-viewer"
    ref="top"
    class="pdf-redaction-tool container bg-dark-subtle">
    <div v-if="hasPassword && ready" class="row">
      <div class="col">
        <div class="alert alert-info" role="alert">
          {{ i18n.hasPassword }}
        </div>
      </div>
    </div>
    <div v-if="message" class="row">
      <div class="col">
        <div class="alert alert-info" role="alert">
          {{ message }}
        </div>
      </div>
    </div>
    <div v-if="errors" class="row">
      <div class="col">
        <div class="alert alert-danger" role="alert">
          {{ errors }}
        </div>
      </div>
    </div>
    <div v-if="working" class="row mt-5">
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
    <div class="row toolbar">
      <div
        v-if="ready"
        class="btn-toolbar col align-items-center justify-content-around justify-content-sm-between bg-light">
        <div
          class="btn-group me-1 toolbar-undo-redo justify-content-center justify-content-lg-start py-2">
          <input
            v-if="hasTouch"
            type="checkbox"
            class="btn-check"
            id="btn-check-paint"
            v-model="allowSingleTap" />
          <label
            v-if="hasTouch"
            class="btn btn-outline-secondary d-flex"
            for="btn-check-paint">
            <!-- browser hardcodedly vertically center text in <button>s, we try to match this visually via flex -->
            <div class="align-self-center">
              <i class="fa fa-lg fa-paint-brush" />
              <small class="d-none d-xl-block">{{ i18n.redact }}</small>
            </div>
          </label>
          <button
            type="button"
            class="btn btn-outline-secondary"
            :disabled="!canUndo"
            :title="i18n.undo"
            @click="undo">
            <i class="fa fa-lg fa-share fa-flip-horizontal" />
            <small class="d-none d-xl-block">{{ i18n.undo }}</small>
          </button>
          <button
            type="button"
            class="btn btn-outline-secondary"
            :disabled="!canRedo"
            data-bs-toggle="tooltip"
            data-bs-placement="top"
            :title="i18n.redo"
            @click="redo">
            <i class="fa fa-lg fa-share" />
            <small class="d-none d-xl-block">{{ i18n.redo }}</small>
          </button>
          <button
            type="button"
            class="btn btn-outline-secondary"
            :disabled="!canUndo"
            :title="'TODO'"
            @click="undoAll">
            <i class="fa fa-lg fa-eraser" />
            <small class="d-none d-xl-block"
              >Alle Schwärzungen<br />entfernen</small
            >
          </button>
        </div>

        <div v-if="!minimalUi" class="btn-group me-1 toolbar-modes py-2">
          <button
            class="btn"
            :class="{ 'btn-outline-info': !textOnly, 'btn-info': textOnly }"
            :title="i18n.toggleText"
            @click.stop="toggleText"
          >
            <i class="fa fa-align-justify" />
            <small class="d-none d-xl-block">{{ i18n.toggleText }}</small>
          </button>
          <button
            class="btn"
            :class="{
              'btn-outline-info': !textDisabled,
              'btn-info': textDisabled
            }"
            :title="i18n.disableText"
            @click.stop="toggleDrawing"
          >
            <i class="fa fa-image" />
            <small class="d-none d-xl-block">{{ i18n.disableText }}</small>
          </button>
        </div>

        <!-- TODO: hide if numPages === 1 ? -->
        <div
          class="input-group me-1 toolbar-pages justify-content-center justify-content-lg-start py-2">
          <button
            class="pdf-prev btn btn-outline-secondary"
            :disabled="!hasPrevious"
            @click="goPrevious"
          >
            &laquo;
            <span class="visually-hidden">{{ i18n.previousPage }}</span>
          </button>
          <span class="input-group-text">
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
          v-if="!minimalUi && (hasRedactions || hasPassword)"
          class="btn-group me-lg-1 ms-auto mt-1 mt-lg-0 py-2">
          <button class="btn btn-dark" @click="redact">
            <i class="fa fa-paint-brush me-2" />
            <template v-if="hasRedactions">
              {{ i18n.redactAndPublish }}
            </template>
            <template v-else-if="hasPassword">
              {{ i18n.removePasswordAndPublish }}
            </template>
          </button>
        </div>

        <div v-if="!minimalUi" class="btn-group ms-auto mt-1 mt-lg-0 py-2">
          <form
            v-if="canPublish && !hasPassword"
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
              class="btn"
              :class="{
                'btn-success': !hasRedactions,
                'btn-outline-secondary': hasRedactions
              }"
              type="submit"
              @click="confirmNoRedactions"
            >
              <i class="fa fa-check me-2" />{{ i18n.publishWithoutRedaction }}
            </button>
          </form>
          <a v-else class="btn btn-secondary" :href="attachmentUrl">
            {{ i18n.cancel }}
          </a>
        </div>

        <slot name="toolbar-right"></slot>
      </div>
    </div>
    <div class="py-3 row preview">
      <div ref="containerWrapper" class="overflow-auto">
        <div
          :id="containerId"
          ref="container"
          class="redactContainer"
          :class="{ 'hide-redacting': working }"
        >
          <canvas v-show="!textOnly" :id="canvasId" class="redactLayer" />
          <canvas
            v-show="!textOnly"
            :id="redactCanvasId"
            class="redactLayer"
            @mousedown="mouseDown"
            @mousemove="mouseMove"
            @mouseup="mouseUp"
            @touchstart="touchStart"
            @touchend="touchEnd"
            @touchmove="touchMove"
            @touchcancel="touchCancel"
          />
          <div
            :id="textLayerId"
            class="textLayer"
            :class="{ textActive: textOnly, textDisabled: textDisabled }"
            @mousedown="mouseDown"
            @mousemove="mouseMove"
            @mouseup="mouseUp"
            @touchstart="touchStart"
            @touchend="touchEnd"
            @touchmove="touchMove"
            @touchcancel="touchCancel"
          />
        </div>
      </div>
    </div>
    <div v-if="!minimalUi" class="row">
      <div v-if="ready" class="btn-toolbar col bg-light py-2">
        <div class="input-group me-auto ms-auto">
          <button
            class="pdf-prev btn btn-outline-secondary"
            :disabled="!hasPrevious"
            @click="goPrevious"
          >
            &laquo;
            {{ i18n.previousPage }}
          </button>
          <span class="input-group-text">
            {{ pageOfTotal }}
          </span>
          <button
            class="pdf-next btn btn-outline-secondary"
            :disabled="!hasNext"
            @click="goNext"
          >
            {{ i18n.nextPage }}
            &raquo;
          </button>
        </div>
      </div>
    </div>
    <confirm-no-redaction
      :i18n="config.i18n"
      ref="confirmmodal"
      @submit="submitRedactions"
    />
  </div>
</template>

<script>
import 'string.prototype.repeat'
import ConfirmNoRedaction from './confirm-no-redaction'

import PDFJSWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.js?url'

import range from 'lodash.range'

import { Modal } from 'bootstrap'

import { bustCache, getData } from '../../lib/api.js'
import { toRaw } from 'vue'

function isTouchDevice() {
  return 'ontouchstart' in window
}

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
    attachmentUrl: {
      type: String,
      required: true
    },
    postUrl: {
      type: String
    },
    approveUrl: {
      type: String
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
    minimalUi: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      doc: null,
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
      pageScaleFactor: {},
      actionsPerPage: {},
      actionIndexPerPage: {},
      rectanglesPerPage: {},
      password: null,
      maxWidth: null,
      startDrag: null,
      endDrag: null,
      initialAutoRedact: {},
      errors: null,
      message: null,
      progressCurrent: null,
      progressTotal: null,
      hasTouch: isTouchDevice(),
      allowSingleTap: true,
      doubleTap: false
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
    }
  },
  watch: {
    hasRedactions: function (newValue) {
      this.$emit('hasredactionsupdate', newValue)
    }
  },
  created() {
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
        console.log('# Page ' + pageNum)
        this.page = page
        if (this.maxWidth === null) {
          this.maxWidth = this.$refs.containerWrapper.offsetWidth
          // subtract the paddings (from bootstrap's row child),
          // fall back to the value calculated in default settings (like base font size)
          this.maxWidth -=
            parseInt(
              window.getComputedStyle(this.$refs.containerWrapper)?.paddingLeft
            ) * 2 || 24
        }

        if (this.pageScaleFactor[pageNum] === undefined) {
          // Make sure scaleFactor is fixed to page, doesn't change
          const scaleFactor = this.maxWidth / page.view[2]
          this.pageScaleFactor[pageNum] = scaleFactor
        }

        const scaleFactor = this.pageScaleFactor[pageNum]
        const viewport = page.getViewport({ scale: scaleFactor })

        this.viewport = viewport
        console.log(
          scaleFactor,
          'Size: ' + viewport.width + 'x' + viewport.height,
          'at maxwidth',
          this.maxWidth
        )
        const canvas = this.canvas
        canvas.width = viewport.width
        canvas.height = viewport.height
        this.redactCanvas.width = viewport.width
        this.redactCanvas.height = viewport.height
        this.container.style.width = Math.floor(viewport.width) + 'px'
        this.container.style.height = Math.floor(viewport.height) + 'px'
        this.textLayer.style.width = Math.floor(viewport.width) + 'px'
        this.textLayer.style.height = Math.floor(viewport.height) + 'px'
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
    redactOrApprove() {
      if (this.hasRedactions || this.hasPassword) {
        console.log('### redactOrApprove redact')
        return this.redact()
      } else {
        console.log('### redactOrApprove approve')
        return this.approve()
      }
    },
    approve() {
      // TODO like redact(), this should emulate what the form above does
      const url = this.approveUrl
      return fetch(url, {
        method: 'POST',
        headers: { 'X-CSRFToken': this.csrfToken }
      }).then((response) => {
        if (!response.ok) {
          console.error('approve error', response)
          throw new Error(`approve error: ${response.status}`)
        }
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
          const data = { pages: serialized, password: this.password }
          this.progressCurrent = null
          return this.sendSerializedPages(data)
            .then((attachment) => {
              if (attachment) {
                this.progressCurrent = 100
                this.progressTotal = 100
                bustCache(attachment.file_url).then(() => {
                  // FIXME WIP emit a success event here instead
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
        // TODO
        // should be like /anfrage/foo/redact/123456/
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
                this.waitOnAttachment(JSON.parse(xhr.responseText))
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
    waitOnAttachment(response) {
      return new Promise((resolve, reject) => {
        const attachmentUrl = response.resource_uri
        let waitTime = 0
        const checkAttachment = () => {
          getData(attachmentUrl)
            .then((attachment) => {
              if (attachment.pending || !attachment.approved) {
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
        const [dx, dy] = this.getDivPos(d)
        const dw = d.offsetWidth
        const dh = d.offsetHeight
        return {
          pos: [dx, dy, dw, dh],
          fontFamily: d.style.fontFamily,
          fontSize: d.style.fontSize,
          transform: d.style.transform,
          text: d.textContent
        }
      })
      return {
        width: this.viewport.width,
        height: this.viewport.height,
        scaleFactor: this.scaleFactor,
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
      const offsetX = clientX - rect.left
      const offsetY = clientY - rect.top
      return [offsetX, offsetY]
    },
    touchStart(e) {
      if (!this.doubleTap && !this.allowSingleTap) {
        this.doubleTap = true
        setTimeout(() => {
          this.doubleTap = false
        }, 500)
        return false
      }
      e.preventDefault()
      this.mouseDown(e, true)
    },
    touchEnd(e) {
      this.mouseUp(e, true)
    },
    touchMove(e) {
      this.mouseMove(e, true)
    },
    touchCancel() {
      this.cancelDrag()
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
      if (this.hasTouch && !override) {
        return
      }
      this.startDrag = this.getOffset(e)
      this.endDrag = null
    },
    mouseUp(e, override) {
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
      this.endDrag = null
      const endDrag = this.getOffset(e)
      if (
        Math.abs(endDrag[0] - this.startDrag[0]) < 3 &&
        Math.abs(endDrag[1] - this.startDrag[1]) < 3
      ) {
        console.log('Cancel empty select')
        this.startDrag = null
        return
      }
      const [x, y, w, h] = this.getRect(this.startDrag, endDrag)
      if (isNaN(parseFloat(x)) || isNaN(parseFloat(y))) {
        return
      }

      // find overlapping text and remove it completely
      const divs = this.textLayer.children
      const matches = Array.prototype.filter.call(divs, (d) => {
        const [dx, dy] = this.getDivPos(d)
        const dw = d.offsetWidth
        const dh = d.offsetHeight
        return x < dx + dw && x + w > dx && y < dy + dh && y + h > dy
      })
      const texts = matches.map((d) => {
        const action = this.redactText(d, 0, d.textContent)
        return action.texts[0]
      })

      this.addAction({
        type: 'redact',
        rects: [[x, y, w, h]],
        page: this.currentPage,
        texts
      })
      this.startDrag = null
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
          console.log(node, start, end)
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
      let i = 0
      Array.prototype.forEach.call(this.textLayer.children, (c) => {
        c.dataset.index = i
        i += 1
      })
      if (this.initialAutoRedact[this.currentPage] === undefined) {
        this.regexList.forEach((r) => this.autoRedact(r))
        this.initialAutoRedact[this.currentPage] = true
      }
      this.applyActionsOnPageLoad()
    },
    drawRectangle(ctx, rect) {
      const [x, y, w, h] = rect
      ctx.fillStyle = '#000'
      ctx.fillRect(x, y, w, h)
    },
    drawRectangles() {
      const ctx = this.redactCanvas.getContext('2d')
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height)
      if (this.rectanglesPerPage[this.currentPage] !== undefined) {
        this.rectanglesPerPage[this.currentPage].forEach((r) => {
          this.drawRectangle(ctx, r)
        })
      }
      if (this.startDrag && this.endDrag) {
        this.drawRectangle(ctx, this.getRect(this.startDrag, this.endDrag))
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
        /* eslint-disable no-cond-assign */
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
    getDivPos(div) {
      return [
        parseInt(div.style.left.replace('px', '')),
        parseInt(div.style.top.replace('px', ''))
      ]
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

      div.textContent = text.substr(0, start)
      const startWidth = div.offsetWidth

      div.textContent = text.substr(0, start + match.length)
      const endWidth = div.offsetWidth

      div.textContent = text

      const pos = this.getDivPos(div)
      let x = pos[0]
      const y = pos[1]
      if (isNaN(parseFloat(x)) || isNaN(parseFloat(y))) {
        return null
      }
      x += startWidth
      const width = endWidth - startWidth

      const height = Math.min(div.offsetHeight * 1.2, div.offsetHeight + 10)
      const padding = 2
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
        rects: [[x - padding, y, width + padding * 2, height]],
        page: this.currentPage
      }
    },
    confirmNoRedactions(event) {
      if (this.hasRedactions) {
        event.preventDefault()
        const modal = Modal.getOrCreateInstance(this.$refs.confirmmodal.$el)
        modal.show()
      }
    },
    submitRedactions() {
      document.getElementById('redaction-submit-form').submit()
    }
  }
}
</script>

<style lang="scss">
@import '../../../styles/variables';
.toolbar {
  position: sticky;
  top: 0;
  z-index: 100;
  opacity: 1;
  padding: 5px;
  background-color: var(--#{$prefix}body-bg);
}
.redactContainer {
  position: relative;
  padding: 0;
  margin: 0 auto;
}
.hide-redacting {
  visibility: hidden;
}

.textLayer,
.redactLayer {
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
  cursor: crosshair;
}
.textLayer {
  opacity: 0.2;
  line-height: 1;
}
.textLayer > div,
.textLayer > span,
.textLayer > br {
  color: transparent;
  position: absolute;
  white-space: pre;
  cursor: text;
  transform-origin: 0% 0%;
}

.textLayer.textActive {
  opacity: 1;
}
.textLayer.textDisabled {
  visibility: hidden;
}

.textLayer.textActive > div,
.textLayer.textActive > span {
  color: #000;
}

.toolbar {
  padding: 0;
}

.preview {
  box-shadow: inset 0 1em 1em -1em rgba(0, 0, 0, 0.5);
}
</style>
