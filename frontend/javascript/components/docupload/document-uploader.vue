<template>
  <div class="document-uploader mb-3 mt-3">
    <div class="upload">
      <label :class="{'btn btn-primary isMobile': isMobile}">
        <i class="fa fa-cloud-upload"></i>
        <span v-if="isMobile">
          {{ i18n.takePicture }}
        </span>
        <span v-else>
          {{ i18n.uploadPdfOrPicture }}
          <br/>
        </span>
        <input v-show="!isMobile" type="file" @change="filesSelected" accept="image/*,application/pdf" multiple/>
      </label>
    </div>
    <div class="documents">
      <component
        v-for="doc in documents"
        v-bind:is="doc.component"
        :key="doc.id"
        :document="doc"
        :config="config"
        @pageschanged="pagesChanged(doc, $event)"
        @loadpdf="loadPdf(doc)"
        @splitpages="splitPages(doc, $event)"
        @imagesconverted="imagesConverted"
        @namechanged="doc.name = $event"
        @docupdated="documentUpdated(doc, $event)"
        @notnew="doc.new = false"
      ></component>
    </div>

    <div v-if="otherAttachments.length > 0">
      <p>
        <button class="btn btn-link" @click="showOther = !showOther">
          {{ i18n.showIrrelevantAttachments}}
        </button>
      </p>
      <ul v-if="showOther">
        <li v-for="other in otherAttachments" :key="other.name">
          <a :href="other.url" target="_blank">
            {{ other.name }}
          </a>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
import I18nMixin from '../../lib/i18n-mixin'

import PdfDocument from './pdf-document.vue'
import FullpdfDocument from './fullpdf-document.vue'
import ImageDocument from './image-document.vue'

// If smaller, likely not document image
const MIN_DOC_IMAGE_SIZE = 50 * 1024


export default {
  name: 'document-uploader',
  mixins: [I18nMixin],
  props: ['config', 'message'],
  components: {
    PdfDocument,
    ImageDocument,
    FullpdfDocument
  },
  data () {
    const [docs, other] = this.buildDocuments()
    return {
      documents: docs,
      otherAttachments: other,
      showOther: false,
      imageDocId: 0
    }
  },
  mounted () {
    this.$root.url = this.config.url
    this.$root.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value
  },
  computed: {
    isMobile () {
      // device detection
      return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
    },
  },
  methods: {
    buildDocuments () {
      const documents = []
      let images = []
      const other = []
      this.message.attachments.forEach((att) => {
        if (this.isDocumentAttachment(att)) {
          if (this.config.settings.pdf_filetypes.includes(att.filetype)) {
            documents.push({
              id: att.id,
              name: att.name,
              url: att.file_url,
              filetype: 'application/pdf',
              site_url: att.site_url,
              type: 'pdf',
              pending: att.pending,
              pages: null,
              component: 'pdf-document',
              attachment: att
            })
          } else {
            images.push({
              id: att.id,
              name: att.name,
              url: att.file_url,
              attachment: att
            })
          }
        } else {
          other.push({
            id: att.id,
            name: att.name,
            filetype: att.filetype,
            pending: att.pending,
            url: att.site_url,
            attachment: att
          })
        }
      })
      if (images.length > 0) {
        images = this.prepareImages(images)
        documents.unshift(
          this.getNewImageDoc({
            pages: images,
            new: false
          })
        )
      }
      return [documents, other]
    },
    isDocumentAttachment (att) {
      if (att.converted !== null) {
        return false
      }
      if (this.config.settings.document_filetypes.includes(att.filetype)) {
        return true
      }
      if (this.config.settings.image_filetypes.includes(att.filetype) && att.size <= MIN_DOC_IMAGE_SIZE) {
        return true
      }
      return false
    },
    prepareImages (images) {
      images = images.sort((a, b) => {
        if(a.name < b.name) return -1;
        if(a.name > b.name) return 1;
        return 0;
      }).map((x, i) => {
        x.pageNum = i + 1
        return x
      })
      return images
    },
    pagesChanged (doc, pages) {
      pages.forEach((p, i) => {
        p.pageNum = i + 1
      })
      doc.pages = pages
    },
    loadPdf (doc) {
      doc.component = 'fullpdf-document'
    },
    splitPages (doc, pageNum) {
      let newPages = doc.pages.slice(pageNum)
      doc.pages = doc.pages.slice(0, pageNum)
      doc.new = true
      this.documents = [
        ...this.documents.filter((d) => d.type === 'imagedoc'),
        this.getNewImageDoc({
          pages: newPages,
        }), 
        ...this.documents.filter((d) => d.type === 'pdf'),
      ]
    },
    getNewImageDoc (data) {
      this.imageDocId += 1
      return {
        id: 'imagedoc' + this.imageDocId,
        filetype: null,
        type: 'imagedoc',
        new: true,
        name: '',
        component: 'image-document',
        ...data
      }
    },
    imagesConverted ({document, imageDoc}) {
      this.documents = this.documents.filter((d) => d.id !== imageDoc.id)
      this.documents = [
        ...this.documents.filter((d) => d.type === 'imagedoc'),
        {
          id: document.id,
          name: document.name,
          url: document.file_url,
          filetype: 'application/pdf',
          site_url: document.site_url,
          type: 'pdf',
          new: true,
          pages: null,
          pending: true,
          component: 'pdf-document',
          attachment: document
        },
        ...this.documents.filter((d) => d.type === 'pdf')
      ]
    },
    documentUpdated (doc, update) {
      for (let key in update) {
        doc[key] = update[key]
      }
    },
    uploadPage (page) {
      page.progress = 0
      page.uploading = true
      page.progressTotal = null
      return new Promise((resolve, reject) => {
        var data = new FormData()
        data.append(`${this.config.settings.attachment_form_prefix}-files`, page.file)

        var xhr = new window.XMLHttpRequest()
        xhr.open('POST', this.config.url.addAttachment)
        xhr.setRequestHeader('X-CSRFToken', this.$root.csrfToken)
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest')
        let xhrUpload = xhr.upload ? xhr.upload : xhr
        xhrUpload.addEventListener("progress", (e) => {
          if (e.lengthComputable) {
            page.progress = e.loaded
            page.progressTotal = e.total
            page.progressPercent = Math.min(100, Math.round(page.progress / page.progressTotal * 100))
            page.progressPercentLabel = page.progressPercent + '%'
          } else {
            page.progress = null
            page.progressPercent = null
          }
        })
        xhr.onreadystatechange = function () {
          if (xhr.readyState === 4) {
            page.uploading = false
            let result;
            try {
              result = JSON.parse(xhr.responseText)
            } catch {
              page.failed = true
              return resolve(null)
            }
            let att
            if (result.added.length === 1) {
              att = result.added[0]
            } else {
              att = result.updated[0]
            }
            if (page.url && page.url.indexOf('blob:') === 0) {
              window.URL.revokeObjectURL(page.url);
            }
            page.url = att.file_url
            page.site_url = att.site_url
            page.filetype = att.filetype
            page.id = att.id
            page.attachment = att
            return resolve(page)
          }
        }
        xhr.send(data)
      })
    },
    filesSelected (event) {
      let files = event.target.files
      let pages = []
      let images = []
      for (let i = 0; i < files.length; i += 1) {
        let f = files[i]
        if (this.config.settings.pdf_filetypes.includes(f.type)) {
          pages.push({
            id: `${f.name}-${f.lastModified}-${f.size}`,
            filetype: f.type,
            file: f,
            size: f.size,
            progress: 0,
            type: 'pdf',
            new: true,
            name: f.name,
            component: 'pdf-document',
            url: window.URL.createObjectURL(f)
          })
        } else if (this.config.settings.image_filetypes.includes(f.type)) {
          let img = {
            id: `${f.name}-${f.lastModified}-${f.size}`,
            name: f.name,
            filetype: f.type,
            file: f,
            size: f.size,
            type: 'image',
            url: window.URL.createObjectURL(f)
          }
          images.push(img)
          pages.push(img)
        } else {
          pages.push({
            id: `${f.name}-${f.lastModified}-${f.size}`,
            name: f.name,
            file: f,
            filetype: f.type,
            type: 'other'
          })
        }
      }
      if (images.length > 0) {
        images = this.prepareImages(images)
        let imageDocs = this.documents.filter((d) => d.type === 'imagedoc')
        if (imageDocs.length === 0) {
          let i = images[0]
          this.documents = [
            this.getNewImageDoc({
              pages: images,
            }),
            ...this.documents
          ]
        } else {
          let imageDoc = imageDocs[0]
          imageDoc.pages = [
            ...imageDoc.pages,
            ...images.map((i, c) => {
              i.pageNum = imageDoc.pages.length + c + 1
              return i
            })
          ]
        }
      }
      this.otherAttachments = [
        ...this.otherAttachments,
        ...pages.filter((p) => p.type === 'other')
      ]
      this.documents = [
        ...pages.filter((p) => p.type === 'pdf'),
        ...this.documents,
      ]
      var p = Promise.resolve();
      pages.forEach(page => {
        p.uploading = true
        p = p.then(() => this.uploadPage(page))
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.upload label.isMobile {
  display: block;
  text-align: center;
}
</style>
