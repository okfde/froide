<template>
  <div id="pdf-viewer">
    <div class="row toolbar">
      <div v-if="!loading" class="btn-toolbar col-lg-12">
        <div class="btn-group mr-2">
          <button class="btn" @click="undo" :disabled="!canUndo">
            <i class="fa fa-undo"></i>
          </button>
          <button class="btn" @click="redo" :disabled="!canRedo">
            <i class="fa fa-repeat"></i>
          </button>
        </div>
        <div class="btn-group mr-2">
          <button class="pdf-prev btn" @click="goPrevious" :disabled="!hasPrevious">
            &laquo; {{ i18n.previousPage}}
          </button>
          <span class="input-group-addon">
            {{ pageOfTotal }}
          </span>
          <button class="pdf-next btn" @click="goNext" :disabled="!hasNext">
            {{ i18n.nextPage }} &raquo;
          </button>
        </div>
        <div class="btn-group mr-2">
          <button class="btn btn-primary">
            {{ i18n.saveAndPublish }}
          </button>
        </div>
        <div class="btn-group mr-2">
          <button class="btn" :class="{'btn-outline-info': !textOnly, 'btn-info': textOnly}" @click.stop="toggleText">
            {{ i18n.toggleText }}
          </button>
        </div>
        <div class="btn-group mr-2">
          <a class="btn btn-secondary" :href="attachmentUrl">
            {{ i18n.cancel }}
          </a>
        </div>
      </div>
    </div>
    <div class="row mt-3">
      <div class="col-lg-12">
        <div v-if="ready" :id="containerId" class="redactContainer">
          <canvas v-show="!textOnly" :id="canvasId" class="redactLayer"></canvas>
          <canvas v-show="!textOnly" :id="redactCanvasId" class="redactLayer"></canvas>
          <div :id="textLayerId" class="textLayer" :class="{ textActive: textOnly }" @mousedown="mouseDown" @mouseup="mouseUp"></div>
        </div>
        <div class="redaction-progress">
          <p v-if="loading">
            {{ i18n.loadingPdf }}
          </p>
          <p v-if="redacting" class="redacting">
            {{ i18n.redacting }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Vue from 'vue'
import {PDFJS} from 'pdfjs-dist'

const PDF_TO_CSS_UNITS = 96.0 / 72.0

export default {
  name: 'redaction',
  props: ['config', 'pdfPath', 'attachmentUrl', 'redactRegex'],
  data () {
    return {
      doc: null,
      currentPage: null,
      numPages: null,
      containerId: 'container-' + String(Math.random()).substr(2),
      canvasId: 'canvas-' + String(Math.random()).substr(2),
      redactCanvasId: 'redactCanvas-' + String(Math.random()).substr(2),
      textLayerId: 'textlayer-' + String(Math.random()).substr(2),
      loading: true,
      ready: false,
      textOnly: false,
      redacting: false,
      scaleFactor: PDF_TO_CSS_UNITS,
      actionsPerPage: {},
      actionIndexPerPage: {},
      rectanglesPerPage: {},
      startDrag: null,
      initialAutoRedact: {}
    }
  },
  created () {
    PDFJS.workerSrc = this.config.resources.pdfjsWorker
    console.log(PDFJS)
    this.loadDocument().then(() => this.loadPage(1))
  },
  computed: {
    page () {
      return this.currentPage
    },
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
      return this.actionIndexPerPage[this.currentPage] < actions.length
    },
    pageOfTotal () {
      if (this.numPages !== null) {
        return this.i18n.pageCurrentOfTotal({
          current: this.currentPage,
          total: this.numPages
        })
      }
      return ''
    },
    regexList () {
      let list = []
      let splits = this.redactRegex.split('|')
      splits.forEach(r => {
        let lines = r.match(/[^\r\n]+/g)
        list = [...list, ...lines.map(r => new RegExp(r, 'gi'))]
      })
      return list
    },
    container () {
      return document.getElementById(this.containerId)
    },
    canvas () {
      return document.getElementById(this.canvasId)
    },
    redactCanvas () {
      return document.getElementById(this.redactCanvasId)
    },
    textLayer () {
      return document.getElementById(this.textLayerId)
    }
  },
  methods: {
    loadDocument () {
      let loadingTask = PDFJS.getDocument(this.pdfPath)
      return loadingTask.promise.then(pdfDocument => {
        this.loading = false
        this.ready = true
        this.doc = pdfDocument
        this.numPages = this.doc.pdfInfo.numPages

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
        var viewport = page.getViewport(this.scaleFactor)
        console.log('Size: ' + viewport.width + 'x' + viewport.height)
        console.log()
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
        page.getTextContent().then((content) => {
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
          return task.promise.then(this.textAvailable)
        })
        return renderTask.promise
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
      this.loadPage(pageNum)
    },
    toggleText () {
      this.textOnly = !this.textOnly
    },
    getOffset (e) {
      let offset = [
        (e.offsetX || e.originalEvent.layerX),
        (e.offsetY || e.originalEvent.layerY)
      ]
      if (e.target !== this.textLayer) {
        let x = parseInt(e.target.style.left.replace('px', ''))
        let y = parseInt(e.target.style.top.replace('px', ''))
        offset[0] += x
        offset[1] += y
      }
      return offset
    },
    mouseDown (e) {
      this.startDrag = this.getOffset(e)
    },
    mouseUp (e) {
      let selection = window.getSelection()

      if (selection !== undefined && !selection.isCollapsed) {
        console.log(selection)
        return this.handleSelection(selection)
      }

      let endDrag = this.getOffset(e)
      if (Math.abs(endDrag[0] - this.startDrag[0]) < 3 &&
          Math.abs(endDrag[1] - this.startDrag[1]) < 3) {
        console.log('Cancel empty select')
        return
      }
      let x, y, w, h
      if (this.startDrag[0] < endDrag[0]) {
        x = this.startDrag[0]
        w = endDrag[0] - x
      } else {
        x = endDrag[0]
        w = this.startDrag[0] - x
      }
      if (this.startDrag[1] < endDrag[1]) {
        y = this.startDrag[1]
        h = endDrag[1] - y
      } else {
        y = endDrag[1]
        h = this.startDrag[1] - y
      }

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
          this.addAction(action)
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
          this.addAction(action)
        })
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
      this.rectanglesPerPage[this.currentPage].forEach(r => this.drawRectangle(ctx, r))
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
          div.textContent = a.textAfter
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
          div.textContent = a.textBefore
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


<style>
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
    margin: 0;
  }
  .textLayer, .redactLayer {
    position: absolute;
    left: 0;
    top: 0;
    right: 0;
    bottom: 0;
    overflow: hidden;
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

  .textLayer.textActive > div {
    color: #000;
  }

</style>
