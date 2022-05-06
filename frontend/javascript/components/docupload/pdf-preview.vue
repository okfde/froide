<template>
  <div class="card">
    <div class="card-body">
      <ol class="pages">
        <li v-for="page in pages" :key="page.pageNum" class="page">
          <a :href="document.site_url" target="_blank">
            <img v-if="page.url" :src="page.url" alt="" class="page-image" />
          </a>
          <div class="text-center">
            <span>{{ page.pageNum }}</span>
          </div>
        </li>
      </ol>
    </div>
  </div>
</template>

<script>
const range = (len) => [...Array(len).keys()]

export default {
  name: 'PdfPreview',
  props: ['config', 'document'],
  data() {
    return {
      progressTotal: null,
      progressCurrent: null,
      ready: false,
      pdf: null,
      numPages: null,
      pdfPages: []
    }
  },
  computed: {
    pages() {
      if (this.document.filetype === 'application/pdf') {
        return this.pdfPages
      }
      return this.document.pages
    }
  },
  created() {
    if (this.document.filetype === 'application/pdf') {
      import('pdfjs-dist')
        .then((PDFJS) => {
          this.PDFJS = PDFJS
          this.PDFJS.GlobalWorkerOptions.workerSrc =
            this.config.resources.pdfjsWorker
          console.log(this.config.resources.pdfjsWorker, this.PDFJS)
          this.loadDocument()
        })
        .catch((err) => {
          console.log(err)
        })
    }
  },
  mounted() {
    if (this.document.new) {
      window.setTimeout(() => this.$emit('notnew'), 2000)
    }
  },
  methods: {
    loadDocument() {
      console.log('Loading PDF', this.document.attachment.file_url)
      const loadingTask = this.PDFJS.getDocument({
        url: this.document.attachment.file_url,
        isEvalSupported: false
      })
      loadingTask.onProgress = (progress) => {
        this.progressCurrent = progress.loaded
        this.progressTotal = progress.total
      }
      return loadingTask.promise.then((pdfDocument) => {
        this.workingState = null
        this.ready = true
        this.pdf = pdfDocument
        this.numPages = this.pdf.pdfInfo.numPages
        range(this.numPages)
          .map((x) => x + 1)
          .forEach((pageNum) => {
            this.pdfPages.push({
              pageNum,
              url: null
            })
            this.loadPage(pageNum)
          })
      })
    },
    loadPage(pageNum) {
      return this.pdf.getPage(pageNum).then((page) => {
        const height = 120
        const viewport = page.getViewport({ scale: 1 })
        const scale = height / viewport.height
        const width = Math.round(viewport.width * scale)
        let canvas = this.getNewCanvas(width, height)
        let ctx = canvas.getContext('2d')
        page
          .render({
            canvasContext: ctx,
            viewport: page.getViewport({ scale: 1 })
          })
          .then(() => {
            this.pdfPages[pageNum - 1].url = canvas.toDataURL('image/png')
            ctx = null
            canvas = null
          })
      })
    },
    getNewCanvas(width, height) {
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      return canvas
    },
    drawRotated(canvas, ctx, img) {
      ctx.translate(canvas.width / 2, canvas.height / 2)

      // roate the canvas by +90% (==Math.PI/2)
      ctx.rotate(Math.PI / 2)

      // since images draw from top-left offset the draw by 1/2 width & height
      ctx.drawImage(img, -img.width / 2, -img.height / 2)

      // un-rotate the canvas by -90% (== -Math.PI/2)
      ctx.rotate(-Math.PI / 2)

      // un-translate the canvas back to origin==top-left canvas
      ctx.translate(-canvas.width / 2, -canvas.height / 2)
    },
    imageDataToImageDataUrl(imageData, width, height) {
      const canvas = this.getNewCanvas(width, height)
      const ctx = canvas.getContext('2d')
      ctx.putImageData(imageData, 0, 0)
      return canvas.toDataURL('image/png')
    },
    prepareImage() {
      return new Promise((resolve) => {
        const img = new window.Image()
        img.onload = () => {
          if (img.naturalWidth > img.naturalHeight) {
            const canvas = this.getNewCanvas(
              img.naturalHeight,
              img.naturalWidth
            )
            const ctx = canvas.getContext('2d')
            this.drawRotated(canvas, ctx, img)
            // let imgRotated = new window.Image()
            // imgRotated.onload = () => {
            //   this.image = imgRotated
            //   resolve(this.image)
            // }
            resolve(canvas.toDataURL('image/jpeg'))
          } else {
            this.image = img
            resolve(this.image)
          }
        }
        img.src = window.URL.createObjectURL(this.file)
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.pages {
  padding-left: 0;
  margin-bottom: 0;
  list-style-type: none;
  white-space: nowrap;
  overflow-x: scroll;
  overflow-scrolling: touch;
}
.page {
  display: inline-block;
  max-width: 90px;
  height: 120px;
  margin: 0 1rem;
}
.page-image {
  padding: 0 0.25rem;
  width: 100%;
  border: 1px solid #bbb;
}
</style>
