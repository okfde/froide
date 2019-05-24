<template>
  <div id="pdf-viewer" class="pdf-redaction-tool" ref="top">
    <div v-if="message" class="row">
      <div class="col-lg-12">
        <div class="alert alert-info" role="alert">{{ message }}</div>
      </div>
    </div>
    <div v-if="errors" class="row">
      <div class="col-lg-12">
        <div class="alert alert-error" role="alert">{{ errors }}</div>
      </div>
    </div>
    <div class="row mt-5" v-if="working">
      <div class="col-lg-12">
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
        <div class="progress">
          <div class="progress-bar" :class="{'progress-bar-striped progress-bar-animated': progressUnknown}" role="progressbar" :aria-valuenow="progressPercent" aria-valuemin="0" aria-valuemax="100" :style="progressWidth"></div>
        </div>
        <div class="text-center mt-3">
          <div class="spinner-border" role="status">
          </div>
        </div>
      </div>
    </div>
    <div class="row toolbar">
      <div v-if="ready" class="btn-toolbar col-lg-12">
        <div class="btn-group mr-1">
          <button class="btn btn-light" @click="undo" :disabled="!canUndo" :title="i18n.undo">
            <i class="fa fa-step-backward"></i>
          </button>
          <button class="btn btn-light" @click="redo" :disabled="!canRedo"
            data-toggle="tooltip" data-placement="top" :title="i18n.redo">
            <i class="fa fa-step-forward"></i>
          </button>
        </div>

        <div class="btn-group mr-1">
          <button class="btn" :class="{'btn-outline-info': !textOnly, 'btn-info': textOnly}" @click.stop="toggleText" :title="i18n.toggleText">
            <i class="fa fa-align-justify"></i>
          </button>
          <button class="btn" :class="{'btn-outline-info': !textDisabled, 'btn-info': textDisabled}" @click.stop="toggleDrawing" :title="i18n.disableText">
            <i class="fa fa-image"></i>
          </button>
        </div>

        <div class="btn-group mr-1">
          <button class="pdf-prev btn btn-light" @click="goPrevious" :disabled="!hasPrevious">
            &laquo;
            <span class="sr-only">{{ i18n.previousPage}}</span>
          </button>
          <span class="input-group-text">
            {{ pageOfTotal }}
          </span>
          <button class="pdf-next btn btn-light" @click="goNext" :disabled="!hasNext">
            <span class="sr-only">{{ i18n.nextPage }}</span>
            &raquo;
          </button>
        </div>

        <div class="btn-group mr-lg-1 ml-auto mt-1 mt-lg-0">
          <button class="btn btn-dark" @click="redact">
            <i class="fa fa-paint-brush"></i>
            {{ i18n.redactAndPublish }}
          </button>
        </div>
        <div class="btn-group ml-auto mt-1 mt-lg-0" >
          <form v-if="canPublish" method="post" :action="config.config.publishUrl">
            <input type="hidden" name="csrfmiddlewaretoken" :value="csrfToken"/>
            <button class="btn btn-success" type="submit">
              <i class="fa fa-check"></i>
              {{ i18n.publishWithoutRedaction }}
            </button>
          </form>
          <a v-else  class="btn btn-secondary" :href="attachmentUrl">
            {{ i18n.cancel }}
          </a>
        </div>
      </div>
    </div>
    <div class="row mt-3">
      <div class="col-lg-12 overflow-auto" ref="containerWrapper">
        <div :id="containerId" ref="container" class="redactContainer" :class="{'hide-redacting': working}">
          <canvas v-show="!textOnly" :id="canvasId" class="redactLayer"></canvas>
          <canvas v-show="!textOnly" :id="redactCanvasId" class="redactLayer"
            @mousedown="mouseDown"
            @mousemove="mouseMove"
            @mouseup="mouseUp"
            @touchstart="touchStart"
            @touchend="touchEnd"
            @touchmove="touchMove"
            @touchcancel="touchCancel"
          ></canvas>
          <div :id="textLayerId" class="textLayer"
            :class="{ textActive: textOnly, textDisabled: textDisabled }"
            @mousedown="mouseDown"
            @mousemove="mouseMove"
            @mouseup="mouseUp"
            @touchstart="touchStart"
            @touchend="touchEnd"
            @touchmove="touchMove"
            @touchcancel="touchCancel"
          ></div>
        </div>
      </div>
    </div>
    <div class="row">
      <div v-if="ready" class="btn-toolbar col-lg-12">
        <div class="btn-group mr-auto ml-auto">
          <button class="pdf-prev btn btn-light" @click="goPrevious" :disabled="!hasPrevious">
            &laquo;
            {{ i18n.previousPage}}
          </button>
          <span class="input-group-text">
            {{ pageOfTotal }}
          </span>
          <button class="pdf-next btn btn-light" @click="goNext" :disabled="!hasNext">
            {{ i18n.nextPage }}
            &raquo;
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import 'string.prototype.repeat'

import range from 'lodash.range'

import Vue from 'vue'

import PDFJS from 'pdfjs-dist'

import {bustCache, getData} from '../../lib/api.js'

const PDF_TO_CSS_UNITS = 96.0 / 72.0

function isTouchDevice() {
  return 'ontouchstart' in window;
}

export default {
  name: 'redaction',
  props: ['config', 'pdfPath', 'attachmentUrl', 'redactRegex', 'canPublish'],
  data () {
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
      textOnly: false,
      textDisabled: true,
      pageScaleFactor: {},
      actionsPerPage: {},
      actionIndexPerPage: {},
      rectanglesPerPage: {},
      maxWidth: null,
      startDrag: null,
      endDrag: null,
      initialAutoRedact: {},
      errors: null,
      message: null,
      progressCurrent: null,
      progressTotal: null,
      hasTouch: isTouchDevice(),
      doubleTap: false,
    }
  },
  created () {
    PDFJS.GlobalWorkerOptions.workerSrc = this.config.resources.pdfjsWorker
    console.log(this.config.resources.pdfjsWorker, PDFJS)
    this.loadDocument().then(() => this.loadPage(1))
  },
  computed: {
    i18n () {
      return this.config.i18n
    },
    hasNext () {
      return this.currentPage < this.numPages
    },
    hasPrevious () {
      return this.currentPage > 1
    },
    canUndo () {
      return this.actionIndexPerPage[this.currentPage] > 0
    },
    canRedo () {
      let actions = this.actionsPerPage[this.currentPage]
      if (actions === undefined) {
        return false
      }
      return this.actionIndexPerPage[this.currentPage] < actions.length
    },
    pageOfTotal () {
      if (this.numPages !== null) {
        return this.i18n.pageCurrentOfTotal.replace(/\$current/, this.currentPage).replace(/\$total/, this.numPages)
      }
      return ''
    },
    regexList () {
      return this.redactRegex.map(r => {
        r = r.replace(/ /g, '\\s+')
        r = `\\b${r}\\b`
        return new RegExp(r, 'g')
      })
    },
    container () {
      return this.$refs.container
    },
    canvas () {
      return document.getElementById(this.canvasId)
    },
    redactCanvas () {
      return document.getElementById(this.redactCanvasId)
    },
    textLayer () {
      return document.getElementById(this.textLayerId)
    },
    working () {
      return this.workingState !== null
    },
    loading () {
      return this.workingState === 'loading'
    },
    redacting () {
      return this.workingState === 'redacting'
    },
    sending () {
      return this.workingState === 'sending'
    },
    progressUnknown () {
      return this.progressCurrent === null || this.progressTotal === undefined
    },
    progressPercent () {
      if (!this.progressUnknown) {
        return this.progressCurrent / this.progressTotal * 100
      }
      return 100
    },
    progressWidth () {
      return `width: ${this.progressPercent}%`
    },
    csrfToken () {
      return document.querySelector('[name=csrfmiddlewaretoken]').value
    }
  },
  methods: {
    loadDocument () {
      let loadingTask = PDFJS.getDocument({
        url: this.pdfPath,
        isEvalSupported: false,
        httpHeaders: {
          'pragma': 'no-cache',
          'cache-control': 'no-cache'
        }
      })
      loadingTask.onProgress = (progress) => {
        this.progressCurrent = progress.loaded
        this.progressTotal = progress.total
      }
      return loadingTask.promise.then(pdfDocument => {
        this.workingState = null
        this.ready = true
        this.doc = pdfDocument
        this.numPages = this.doc.numPages

        for (var i = 1; i <= this.numPages; i += 1) {
          Vue.set(this.actionsPerPage, i, [])
          Vue.set(this.actionIndexPerPage, i, 0)
        }
        this.currentPage = 1
      })
    },
    loadPage (pageNum) {
      return this.doc.getPage(pageNum).then((page) => {
        console.log('# Page ' + pageNum)
        this.page = page
        if (this.maxWidth === null) {
          this.maxWidth = this.$refs.containerWrapper.offsetWidth
        }

        if (this.pageScaleFactor[pageNum] === undefined) {
          // Make sure scaleFactor is fixed to page, doesn't change
          let scaleFactor = PDF_TO_CSS_UNITS
          let viewport = page.getViewport(PDF_TO_CSS_UNITS)
          if (viewport.width > this.maxWidth) {
            scaleFactor = this.maxWidth / viewport.width
          }
          this.pageScaleFactor[pageNum] = scaleFactor
        }

        let scaleFactor = this.pageScaleFactor[pageNum]
        let viewport = page.getViewport(scaleFactor)

        this.viewport = viewport
        console.log(scaleFactor, 'Size: ' + viewport.width + 'x' + viewport.height, 'at maxwidth', this.maxWidth)
        var canvas = this.canvas
        canvas.width = viewport.width
        canvas.height = viewport.height
        this.redactCanvas.width = viewport.width
        this.redactCanvas.height = viewport.height
        this.container.style.width = Math.floor(viewport.width) + 'px'
        this.container.style.height = Math.floor(viewport.height) + 'px'
        this.textLayer.style.width = Math.floor(viewport.width) + 'px'
        this.textLayer.style.height = Math.floor(viewport.height) + 'px'
        var ctx = canvas.getContext('2d')
        var renderTask = page.render({
          canvasContext: ctx,
          viewport: viewport
        })
        var textPromise = page.getTextContent().then((content) => {
          // Content contains lots of information about the text layout and
          // styles, but we need only strings at the moment
          // remove all text layer elements
          while (this.textLayer.firstChild) {
            this.textLayer.removeChild(this.textLayer.firstChild)
          }
          // Rendering text layer as HTML.
          var task = PDFJS.renderTextLayer({
            textContent: content,
            container: this.textLayer,
            viewport,
            enhanceTextSelection: true
          })
          return task.promise
        })
        return Promise.all([renderTask.promise, textPromise])
          .then(this.textAvailable)
      })
    },
    goNext () {
      if (this.hasNext) {
        this.setCurrentPage(this.currentPage + 1)
      }
    },
    goPrevious () {
      if (this.hasPrevious) {
        this.setCurrentPage(this.currentPage - 1)
      }
    },
    setCurrentPage (pageNum) {
      this.currentPage = pageNum
      return this.loadPage(pageNum)
    },
    toggleText () {
      this.textOnly = !this.textOnly
      this.textDisabled = !this.textOnly
    },
    toggleDrawing () {
      this.textDisabled = !this.textDisabled
      this.textOnly = !this.textDisabled
    },
    redact () {
      this.$refs.top.scrollIntoView({behavior: "smooth", block: "start"})
      this.ready = false
      this.workingState = 'sending'
      this.progressCurrent = 0
      this.progressTotal = this.numPages + 1
      let pages = range(1, this.numPages + 1)
      let serialized = []
      return pages.reduce((sequence, pageNumber) => {
        return sequence.then(() => {
          return this.setCurrentPage(pageNumber).then(() => {
            this.progressCurrent = pageNumber
            serialized.push(this.serializePage(pageNumber))
          })
        })
      }, Promise.resolve())
        .then(() => {
          console.log(serialized)
          this.progressCurrent = null
          return this.sendSerializedPages(serialized).then((attachment) => {
            if (attachment) {
              this.progressCurrent = 100
              this.progressTotal = 100
              bustCache(attachment.file_url).then(() => {
                document.location.href = attachment.anchor_url
              })
            } else {
              this.workingState = null
              this.errors = res || i18n.redactionTimeout
              this.$refs.top.scrollIntoView(true)
            }
          }).catch((err) => {
            this.workingState = null
            console.error(err)
            this.ready = false
            this.errors = err
            this.$refs.top.scrollIntoView(true)
          })
        })
    },
    sendSerializedPages (serialized) {
      this.workingState = 'sending'
      this.progressCurrent = 5 // show at least some progress
      this.progressTotal = 100
      return new Promise((resolve, reject) => {
        var xhr = new window.XMLHttpRequest()
        xhr.open('POST', document.location.href)
        xhr.setRequestHeader('Content-Type', 'application/json')
        xhr.setRequestHeader('X-CSRFToken', this.csrfToken)
        let xhrUpload = xhr.upload ? xhr.upload : xhr
        xhrUpload.addEventListener("progress", (e) => {
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
                  JSON.parse(xhr.responseText)
                ).then(resolve).catch(reject)
                return
              } catch (e) {
                console.error('Failed to decode JSON', e, xhr.responseText)
                reject(this.i18n.redactionError)
                return
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
    waitOnAttachment (response) {
      return new Promise((resolve, reject) => {
        let attachmentUrl = response.resource_uri
        let waitTime = 0
        const checkAttachment = () => {
          getData(attachmentUrl).then((attachment) => {
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
            console.error('Attachment redacted.')
            resolve(attachment)
          }).catch(() => {
            console.err('Could not get attachment via API')
            return reject(this.i18n.redactionError)
          })
        }
        window.setTimeout(checkAttachment, 1000)
      })
    },
    serializePage (pageNumber) {
      let divs = this.textLayer.children
      let texts = Array.prototype.map.call(divs, d => {
        let [dx, dy] = this.getDivPos(d)
        let dw = d.offsetWidth
        let dh = d.offsetHeight
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
        pageNumber: pageNumber,
        rects: this.rectanglesPerPage[pageNumber],
        texts
      }
    },
    getOffset (e) {
      let target = e.target || e.srcElement
      let rect = target.getBoundingClientRect()
      let clientX = e.clientX
      let clientY = e.clientY
      if (e.touches && e.touches.length > 0) {
        clientX = e.touches[0].clientX
        clientY = e.touches[0].clientY
      } else if (e.changedTouches && e.changedTouches.length > 0) {
        clientX = e.changedTouches[0].clientX
        clientY = e.changedTouches[0].clientY
      }
      let offsetX = clientX - rect.left
      let offsetY = clientY - rect.top
      return [offsetX, offsetY]
    },
    touchStart (e) {
      if(!this.doubleTap) {
        this.doubleTap = true;
        setTimeout( () => { this.doubleTap = false; }, 500 );
        return false;
      }
      e.preventDefault()
      this.mouseDown(e, true)
    },
    touchEnd (e) {
      this.mouseUp(e, true);
    },
    touchMove (e) {
      this.mouseMove(e, true)
    },
    touchCancel (e) {
      this.startDrag = null
    },
    mouseMove (e, override) {
      if (this.hasTouch && !override) {
        return
      }
      if (this.startDrag === null) {
        return
      }
      let selection = window.getSelection()
      if (!selection.isCollapsed) {
        return
      }
      this.endDrag = this.getOffset(e)
      this.drawRectangles()
    },
    mouseDown (e, override) {
      if (this.hasTouch && !override) {
        return
      }
      this.startDrag = this.getOffset(e)
    },
    mouseUp (e, override) {
      if (this.hasTouch && !override) {
        return
      }
      let selection = window.getSelection()

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

      let endDrag = this.getOffset(e)
      if (Math.abs(endDrag[0] - this.startDrag[0]) < 3 &&
          Math.abs(endDrag[1] - this.startDrag[1]) < 3) {
        console.log('Cancel empty select')
        this.startDrag = null
        return
      }
      let [x, y, w, h] = this.getRect(this.startDrag, endDrag)

      // find overlapping text and remove it completely
      let divs = this.textLayer.children
      let matches = Array.prototype.filter.call(divs, d => {
        let [dx, dy] = this.getDivPos(d)
        let dw = d.offsetWidth
        let dh = d.offsetHeight
        return (x < (dx + dw) && (x + w) > dx &&
                y < (dy + dh) && (y + h) > dy)
      })
      let texts = matches.map(d => {
        let action = this.redactText(d, 0, d.textContent)
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
    getRect (start, end) {
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
    handleSelection (selection) {
      function getNextNode (node) {
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

      function getNodesInRange (range) {
        var start = range.startContainer
        var end = range.endContainer
        var commonAncestor = range.commonAncestorContainer
        var nodes = []
        var node

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

      let actions = []

      for (var i = 0; i < selection.rangeCount; i += 1) {
        let range = selection.getRangeAt(i)
        if (range.isCollapsed) { continue }
        // Easy if start and end same container
        if (range.startContainer === range.endContainer) {
          let node = range.startContainer
          if (node.nodeName === '#text') {
            node = node.parentNode
          }
          let action = this.redactRange(node, range.startOffset, range.endOffset)
          actions.push(action)
          continue
        }
        // FIXME: weird other logic
        // from here https://stackoverflow.com/questions/667951/how-to-get-nodes-lying-inside-a-range-with-javascript
        let nodes = getNodesInRange(range)
        nodes.forEach(node => {
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
          if (node === null || node.dataset === undefined ||
              node.dataset.index === undefined) {
            return
          }
          let action = this.redactRange(node, start, end)
          actions.push(action)
        })
      }
      let action = this.combineActions(actions)
      this.addAction(action)
    },
    combineActions (actions) {
      let texts = actions.reduce((a, b) => a.concat(b.texts), [])
      let rects = actions.reduce((a, b) => a.concat(b.rects), [])
      return {
        type: 'redact',
        texts: texts,
        rects: rects,
        page: this.currentPage
      }
    },
    textAvailable () {
      // mark every div with an index number
      var i = 0
      Array.prototype.forEach.call(this.textLayer.children, (c) => {
        c.dataset.index = i
        i += 1
      })
      if (this.initialAutoRedact[this.currentPage] === undefined) {
        this.regexList.forEach(r => this.autoRedact(r))
        Vue.set(this.initialAutoRedact, this.currentPage, true)
      }
      this.applyActionsOnPageLoad()
    },
    drawRectangle (ctx, rect) {
      let [x, y, w, h] = rect
      ctx.fillStyle = '#000'
      ctx.fillRect(x, y, w, h)
    },
    drawRectangles () {
      let ctx = this.redactCanvas.getContext('2d')
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height)
      if (this.rectanglesPerPage[this.currentPage] !== undefined) {
        this.rectanglesPerPage[this.currentPage].forEach(r => {
          this.drawRectangle(ctx, r)
        })
      }
      if (this.startDrag && this.endDrag) {
        this.drawRectangle(ctx, this.getRect(this.startDrag, this.endDrag))
      }
    },
    applyActionsOnPageLoad () {
      if (this.rectanglesPerPage[this.currentPage] === undefined) {
        Vue.set(this.rectanglesPerPage, this.currentPage, [])
      }
      this.actionsPerPage[this.currentPage].forEach(a => {
        this.applyAction(a, true)
      })
      this.drawRectangles()
    },
    undo () {
      if (!this.canUndo) {
        return
      }
      let actionIndex = this.actionIndexPerPage[this.currentPage]
      actionIndex -= 1
      Vue.set(this.actionIndexPerPage, this.currentPage, actionIndex)
      let lastAction = this.actionsPerPage[this.currentPage][actionIndex]
      this.unapplyAction(lastAction)
    },
    redo () {
      if (!this.canRedo) {
        return
      }
      let actionIndex = this.actionIndexPerPage[this.currentPage]
      let nextAction = this.actionsPerPage[this.currentPage][actionIndex]
      actionIndex += 1
      Vue.set(this.actionIndexPerPage, this.currentPage, actionIndex)
      this.applyAction(nextAction)
    },
    addAction (action) {
      let actions = this.actionsPerPage[action.page].slice()
      actions = actions.slice(0, this.actionIndexPerPage[action.page])
      actions.push(action)
      Vue.set(this.actionsPerPage, action.page, actions)
      Vue.set(this.actionIndexPerPage, action.page,
        this.actionsPerPage[action.page].length)

      this.applyAction(action)
    },
    applyAction (action, ignoreRects = false) {
      if (this.rectanglesPerPage[action.page] === undefined) {
        Vue.set(this.rectanglesPerPage, action.page, [])
      }
      if (action.rects !== undefined && !ignoreRects) {
        Vue.set(this.rectanglesPerPage, action.page, [
          ...this.rectanglesPerPage[action.page],
          ...action.rects
        ])
        this.drawRectangles()
      }
      if (action.texts !== undefined && action.texts.length > 0) {
        action.texts.forEach(a => {
          let div = this.textLayer.querySelector(`[data-index="${a.textIndex}"]`)
          if (div !== null) { 
            div.textContent = a.textAfter
          }
        })
      }
    },
    unapplyAction (action) {
      if (action.rects !== undefined && action.rects.length > 0) {
        let newRects = this.rectanglesPerPage[action.page].filter((r) => {
          return action.rects.filter(ar => {
            let [x1, y1, w1, h1] = ar
            let [x2, y2, w2, h2] = r
            return x1 === x2 && y1 === y2 && w1 === w2 && h1 === h2
          }).length === 0
        })
        Vue.set(this.rectanglesPerPage, action.page, newRects)
        this.drawRectangles()
      }
      if (action.texts !== undefined && action.texts.length > 0) {
        action.texts.forEach(a => {
          let div = this.textLayer.querySelector(`[data-index="${a.textIndex}"]`)
          if (div !== null) {
            div.textContent = a.textBefore
          }
        })
      }
    },
    autoRedact (regex) {
      let divs = this.textLayer.children
      let matchFunc = node => node.textContent.match(regex)
      let matches = Array.prototype.filter.call(divs, matchFunc)
      matches.forEach(div => {
        let text = div.textContent
        let result
        /* eslint-disable no-cond-assign */
        while (result = regex.exec(text)) {
          let pos = result.index
          let match = result[0]
          let action = this.redactText(div, pos, match)
          this.addAction(action)
        }
      })
      if (matches.length > 0) {
        this.message = this.i18n.autoRedacted
      }
    },
    getDivPos (div) {
      return [
        parseInt(div.style.left.replace('px', '')),
        parseInt(div.style.top.replace('px', ''))
      ]
    },
    redactText (div, start, text) {
      return this.redactRange(div, start, start + text.length)
    },
    redactRange (div, start, end) {
      /*
        Measure the size of the match for the div
        Measure the offset of the match in the div
        Measure the size of a full redaction block
        Draw black rectangle on the canvas
        Replace text with redaction blocks of appropriate size
      */
      const blocks = [
        '\u2588', '\u2589', '\u258a', '\u258b',
        '\u258c', '\u258d', '\u258e', '\u258f'
      ]
      const blockSizes = [
        1, 7 / 8, 3 / 4, 5 / 8,
        1 / 2, 3 / 8, 1 / 4, 1 / 8
      ]
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
        let blockSize = (blockWidth * blockSizes[blockIndex])
        if (blockSize > fillWidth) {
          blockIndex += 1
          continue
        }
        let n = Math.floor(fillWidth / blockSize)
        replace += blocks[blockIndex].repeat(n)
        fillWidth = (fillWidth % blockSize) / blockSize
        blockIndex += 1
      }

      div.textContent = text.substr(0, start)
      const startWidth = div.offsetWidth

      div.textContent = text.substr(0, start + match.length)
      const endWidth = div.offsetWidth

      div.textContent = text

      let [x, y] = this.getDivPos(div)
      x += startWidth
      let width = endWidth - startWidth

      const height = Math.min(div.offsetHeight * 1.2, div.offsetHeight + 10)
      const padding = 2
      return {
        type: 'redact',
        texts: [{
          textIndex: div.dataset.index,
          textBefore: text,
          // TODO: replace all occurences of match
          textAfter: text.replace(match, replace)
        }],
        rects: [[x - padding, y, width + (padding * 2), height]],
        page: this.currentPage
      }
    }
  }
}
</script>


<style lang="scss">
  .toolbar {
    position: sticky;
    top: 0;
    z-index: 100;
    opacity: 1.0;
    padding: 5px;
    background-color: #fff;
  }
  .redactContainer {
    position: relative;
    padding: 0;
    margin: 0 auto;
  }
  .hide-redacting {
    visibility: hidden;
  }

  .textLayer, .redactLayer {
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
    line-height: 1.0;
  }
  .textLayer > div {
    color: transparent;
    position: absolute;
    white-space: pre;
    cursor: text;
    transform-origin: 0% 0%;
  }

  .textLayer.textActive {
    opacity: 1.0;
  }
  .textLayer.textDisabled {
    visibility: hidden;
  }

  .textLayer.textActive > div {
    color: #000;
  }

</style>
