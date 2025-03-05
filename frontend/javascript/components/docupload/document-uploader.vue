<template>
  <div class="document-uploader mb-3 mt-3">
    <button
      v-if="debug"
      type="button"
      @click="refreshAttachments"
      style="font-size: 50%">
      DEBUG: refresh
    </button>
    <div v-if="imageDocuments.length > 0" class="images mt-5">
      <django-slot name="convert-images" />
      <image-document
        v-for="doc in imageDocuments"
        :key="doc.id"
        :document="doc"
        :config="config"
        :hide-selection="hideSelection"
        :basic-operations="fileBasicOperations"
        :simple="imagesSimple"
        ref="imageDocument"
        @pageschanged="pagesChanged(doc, $event)"
        @splitpages="splitPages(doc, $event)"
        @imagesconverted="imagesConverted"
        @namechanged="doc.name = $event"
        @docupdated="documentUpdated(doc, $event)"
        @pageupdated="pageUpdated"
        @notnew="doc.new = false" />
    </div>
    <component
      v-if="pdfDocuments.length > 0 && (!hidePdf || debug)"
      :is="hidePdf && debug ? 'details' : 'div'"
      class="documents mt-5">
      <summary v-if="debug && hidePdf" class="debug">
        DEBUG: pdf documents
      </summary>
      <django-slot name="documents" />
      <div class="mt-3 mb-3">
        <div
          class="row bg-body-secondary pb-2 pt-2 mb-2 border-bottom"
          v-if="!hideStatusTools || !hideSelectionBar">
          <div class="col-auto me-md-auto" v-if="!hideSelectionBar">
            <input
              v-model="selectAll"
              type="checkbox"
              @click="clickSelectAll" />
          </div>
          <div class="col-auto ms-auto" v-if="!hideStatusTools">
            <button
              v-if="canMakeDocument && canMakeResult"
              class="btn btn-sm"
              :class="{ 'btn-success': canMakeResult }"
              :disabled="!canMakeResult"
              :title="i18n.makeResultsExplanation"
              @click="makeResults">
              <i class="fa fa-certificate" />
              {{ i18n.markAllAsResult }}
            </button>
            <button
              v-if="canApprove"
              class="btn btn-sm ms-2"
              :class="{ 'btn-success': canApprove }"
              :disabled="!canApprove"
              @click="approveSelected">
              <i class="fa fa-check" />
              {{ i18n.approveAll }}
            </button>
          </div>
        </div>
        <file-document
          v-for="doc in pdfDocuments"
          :key="doc.id"
          :document="doc"
          :config="config"
          :hide-selection="hideSelection"
          :icon-style="iconStyle"
          :show-auto-approve="showAutoApprove"
          :show-basic-operations="fileBasicOperations"
          :hide-advanced-operations="hideAdvancedOperations"
          :highlight-redaction="highlightRedactions"
          @pageschanged="pagesChanged(doc, $event)"
          @splitpages="splitPages(doc, $event)"
          @imagesconverted="imagesConverted"
          @namechanged="doc.name = $event"
          @docupdated="documentUpdated(doc, $event)"
          @pageupdated="pageUpdated"
          @notnew="doc.new = false" />
        <div class="row" v-if="showAutoApprove">
          <div class="col-auto ms-auto">
            {{ i18n.documentsApproveLater }}
            ⮥
          </div>
        </div>
      </div>
    </component>

    <div style="color: red" v-else-if="debug">DEBUG: no pdf documents</div>

    <component
      v-if="otherAttachments.length > 0 && (!hideOther || debug)"
      :is="hideOther ? 'details' : 'div'"
      class="mt-5">
      <summary v-if="hideOther && debug" class="debug">
        DEBUG: other attachments
      </summary>
      <hr />
      <django-slot name="other-files" />
      <file-document
        v-for="doc in otherAttachments"
        :key="doc.id"
        :document="doc"
        :config="config"
        :hide-selection="hideSelection"
        :basic-operations="fileBasicOperations"
        @docupdated="documentUpdated(doc, $event)"
        @makerelevant="makeRelevant(doc)"
        @notnew="doc.new = false" />
    </component>

    <div v-if="canUpload && showUpload" class="upload mt-5">
      <django-slot name="upload-header" />
      <file-uploader
        class="mb-3 mt-2"
        :config="config"
        :auto-proceed="true"
        :allowed-file-types="config.settings.allowed_filetypes"
        @upload-success="uploadSuccess" />
      <slot name="fileuploader-after"></slot>
    </div>
  </div>
</template>

<script>
import { postData } from '../../lib/api.js'
import DjangoSlot from '../../lib/django-slot.vue'
import I18nMixin from '../../lib/i18n-mixin'

import FileUploader from '../upload/file-uploader.vue'
import FileDocument from './file-document.vue'
import ImageDocument from './image-document.vue'
import { approveAttachment, createDocument } from './lib/document_utils'

export default {
  name: 'DocumentUploader',
  components: {
    DjangoSlot,
    ImageDocument,
    FileDocument,
    FileUploader
  },
  mixins: [I18nMixin],
  props: {
    debug: {
      type: Boolean,
      default: false
    },
    slots: {
      type: Object,
      default: () => ({})
    },
    config: {
      type: Object,
      required: true
    },
    message: {
      type: Object,
      required: true
    },
    showUpload: {
      type: Boolean,
      default: true
    },
    imagesSimple: {
      type: Boolean,
      default: false
    },
    showAutoApprove: {
      type: Boolean,
      default: false
    },
    fileBasicOperations: {
      type: Boolean,
      default: false
    },
    iconStyle: {
      type: String,
      default: ''
    },
    hideSelection: {
      type: Boolean,
      default: false
    },
    hideSelectionBar: {
      type: Boolean,
      default: false
    },
    hideStatusTools: {
      type: Boolean,
      default: false
    },
    hideAdvancedOperations: {
      type: Boolean,
      default: false
    },
    hidePdf: {
      type: Boolean,
      default: false
    },
    hideOther: {
      type: Boolean,
      default: false
    },
    imagesDocumentFilename: {
      type: String,
      default: ''
    },
    highlightRedactions: {
      type: Boolean,
      default: false
    }
  },
emits: {'selectionupdated': null, 'imagesconverted': null, 'imagesadded': null, 'documentsadded': null},
  data() {
    return {
      documents: [],
      imageDocId: 0,
      uploadCount: 0,
      exifSupport: null,
      names: {},
      selectAll: false
    }
  },
  computed: {
    isMobile() {
      // device detection
      return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
        navigator.userAgent
      )
    },
    canUpload() {
      return this.message.kind === 'post'
    },
    imageDocuments() {
      return this.documents.filter(
        (d) => !d.irrelevant && d.type === 'imagedoc'
      )
    },
    pdfDocuments() {
      return this.documents.filter((d) => {
        let ret = !d.irrelevant && d.type !== 'imagedoc'
        if (this.highlightRedactions) {
          ret = ret && !d.has_redacted
        }
        return ret
      })
    },
    otherAttachments() {
      return this.documents.filter((d) => d.irrelevant)
    },
    selectedDocuments() {
      return this.documents.filter((d) => d.selected)
    },
    canMakeResultDocs() {
      return this.pdfDocuments.filter((d) => {
        return (
          d.selected &&
          d.creatingDocument === undefined &&
          d.attachment &&
          d.attachment.is_pdf &&
          !(d.document || d.attachment.document) &&
          !(d.attachment.redacted || d.attachment.converted)
        )
      })
    },
    canMakeDocument() {
      return this.config.settings.can_make_document
    },
    canMakeResult() {
      return this.canMakeDocument && this.canMakeResultDocs.length > 0
    },
    approvableDocs() {
      return this.pdfDocuments.filter((d) => {
        return (
          d.approving === undefined &&
          d.attachment &&
          !d.attachment.approved &&
          d.attachment.can_approve
        )
      })
    },
    approvableSelectedDocs() {
      return this.approvableDocs.filter((d) => d.selected)
    },
    canApprove() {
      return this.approvableSelectedDocs.length > 0
    }
  },
  watch: {
    selectedDocuments() {
      console.log(
        '# watch selectedDocuments, emit',
        this.selectedDocuments.length
      )
      this.$emit('selectionupdated', this.selectedDocuments)
    },
    imagesDocumentFilename(newName) {
      if (!this.imageDocuments.length) {
        console.warn('imagesDocumentFilename changed, but no imageDocuments')
        return
      }
      // there is only one
      this.imageDocuments[0].name = newName
    }
  },
  mounted() {
    // TODO: this is modifying $root ?!
    this.$root.exifSupport = this.exifSupport = null
    this.testExifSupport()
    this.$root.url = this.config.url
    this.$root.csrfToken = document.querySelector(
      '[name=csrfmiddlewaretoken]'
    ).value
    this.documents = this.buildDocuments(this.message.attachments)
  },
  methods: {
    uploadSuccess({ uppy, response, file }) {
      this.addAttachmentFromTus(response.uploadURL).then(() => {
        uppy.removeFile(file.id)
      })
    },
    testExifSupport() {
      /*
      From Modernizr feature detection:
      https://github.com/Modernizr/Modernizr/blob/master/feature-detects/img/exif-orientation.js
      */
      const img = new Image()
      img.src =
        'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/4QAiRXhpZgAASUkqAAgAAAABABIBAwABAAAABgASAAAAAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAIDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD+/iiiigD/2Q=='
      img.onload = () => {
        this.$root.exifSupport = this.exifSupport = img.height === 2
      }
      img.onerror = () => {
        this.$root.exifSupport = this.exifSupport = false
      }
    },
    addAttachmentFromTus(uploadUrl) {
      return postData(
        this.config.url.convertAttachments,
        {
          action: 'add_tus_attachment',
          upload: uploadUrl
        },
        this.$root.csrfToken
      ).then((result) => {
        if (result.error) {
          throw new Error(result.message)
        }
        const att = result.added[0]
        this.addAttachment(att)
      })
    },
    buildDocuments(attachments, extra = {}) {
      const documents = []
      let images = []
      attachments.forEach((att) => {
        const doc = {
          id: att.id,
          name: att.name,
          filetype: att.filetype,
          pending: att.pending,
          file_url: att.file_url,
          is_redacted: att.is_redacted,
          has_redacted: !!att.redacted,
          pages: null,
          attachment: att,
          auto_approve: true,
          ...extra
        }
        let imagePage = false

        if (att.is_irrelevant) {
          doc.irrelevant = true
        } else if (att.is_pdf) {
          doc.type = 'pdf'
        } else if (att.is_image) {
          if (att.converted) {
            doc.irrelevant = true
          } else {
            imagePage = true
            images.push({
              id: att.id,
              name: att.name,
              attachment: att,
              file_url: att.file_url
            })
          }
        }
        if (!imagePage) {
          documents.push(doc)
        }
        this.names[att.name] = true
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
      return documents
    },
    prepareImages(images) {
      images = images
        .sort((a, b) => {
          if (a.name < b.name) return -1
          if (a.name > b.name) return 1
          return 0
        })
        .map((x, i) => {
          x.pageNum = i + 1
          return x
        })
      return images
    },
    pagesChanged(doc, pages) {
      pages.forEach((p, i) => {
        p.pageNum = i + 1
      })
      doc.pages = pages
    },
    pageUpdated({ document, pageNum, data }) {
      const page = document.pages[pageNum - 1]
      for (const key in data) {
        page[key] = data[key]
      }
    },
    splitPages(doc, pageNum) {
      const newPages = doc.pages.slice(pageNum)
      newPages.forEach((p, i) => {
        p.pageNum = i + 1
      })
      doc.pages = doc.pages.slice(0, pageNum)
      doc.new = true
      this.documents = [
        ...this.documents.filter((d) => d.type === 'imagedoc'),
        this.getNewImageDoc({
          pages: newPages
        }),
        ...this.documents.filter((d) => d.type !== 'imagedoc')
      ]
    },
    getNewImageDoc(data) {
      this.imageDocId += 1
      return {
        id: 'imagedoc' + this.imageDocId,
        filetype: null,
        type: 'imagedoc',
        new: true,
        name: '',
        ...data
      }
    },
    imagesConverted({ attachment, imageDoc }) {
      // Remove image doc
      this.documents = this.documents.filter((d) => d.id !== imageDoc.id)
      // add new attachment to top
      this.documents = [
        ...this.documents.filter((d) => d.type === 'imagedoc'),
        ...this.buildDocuments([attachment], {
          new: true
        }),
        ...this.documents.filter((d) => d.type !== 'imagedoc')
      ]
      this.$emit('imagesconverted')
    },
    documentUpdated(doc, update) {
      if (update === null) {
        this.documents = this.documents.filter((d) => d.id !== doc.id)
        return
      }
      for (const key in update) {
        if (key === 'document') {
          doc.attachment[key] = update[key]
        } else {
          doc[key] = update[key]
        }
      }
    },
    makeRelevant(doc) {
      if (doc.attachment.is_image) {
        const imageDoc = this.documents.filter((d) => d.type === 'imagedoc')
        if (imageDoc.length > 0) {
          doc.pageNum = imageDoc[0].pages.length + 1
          imageDoc[0].pages = [...imageDoc[0].pages, doc]
        } else {
          doc.pageNum = 1
          this.documents = [
            ...this.documents,
            this.getNewImageDoc({
              pages: [doc],
              new: true
            })
          ]
        }
        this.documents = this.documents.filter((d) => d.id !== doc.id)
      } else {
        doc.irrelevant = false
      }
    },
    setAllSelect(value) {
      this.pdfDocuments.forEach((d) => {
        d.selected = value
      })
    },
    clickSelectAll() {
      this.pdfDocuments.forEach((d) => {
        d.selected = !this.selectAll
      })
    },
    approveUnredacted () {
      return Promise.all(
        this.approvableDocs
          .filter((d) => !d.has_redacted && !d.is_redacted && !d.approved && d.auto_approve)
          .map((d) => {
            d.approving = true
            return approveAttachment(d, this.config, this.$root.csrfToken).then(
              (att) => {
                d.approving = false
                d.attachment = att
              }
            )
          })
      )
    },
    approveSelected() {
      return Promise.all(
        this.approvableSelectedDocs.map((d) => {
          d.approving = true
          return approveAttachment(d, this.config, this.$root.csrfToken).then(
            (att) => {
              d.approving = false
              d.attachment = att
            }
          )
        })
      )
    },
    addImages(images) {
      const imageDocs = this.documents.filter((d) => d.type === 'imagedoc')
      if (imageDocs.length === 0) {
        this.documents = [
          this.getNewImageDoc({
            pages: images.map((i, c) => {
              i.pageNum = c + 1
              return i
            })
          }),
          ...this.documents
        ]
      } else {
        const imageDoc = imageDocs[0]
        imageDoc.pages = [
          ...imageDoc.pages,
          ...images.map((i, c) => {
            i.pageNum = imageDoc.pages.length + c + 1
            return i
          })
        ]
      }
      this.$emit('imagesadded')
    },
    addAttachment(att) {
      if (att.is_image) {
        this.addImages([att])
      } else {
        this.documents = [
          ...this.buildDocuments([att], { new: true }),
          ...this.documents
        ]
        this.$emit('documentsadded')
      }
    },
    makeResults() {
      return Promise.all(
        this.canMakeResultDocs.map((d) => {
          d.creatingDocument = false
          return createDocument(d, this.config, this.$root.csrfToken).then(
            (data) => {
              d.attachment.document = data
              d.creatingDocument = null
            }
          )
        })
      )
    },
    refreshAttachmentsIfIdNotPresent(id) {
      if (this.documents.find((d) => d.id === id)) {
        return Promise.resolve(false)
      }
      return this.refreshAttachments().then(() => true)
    },
    refreshAttachments() {
      const url =
        this.config.url.getAttachment.replace('/0/', '/') +
        '?belongs_to=' +
        this.message.id
      return fetch(url, {
        headers: { 'X-CSRFToken': this.$root.csrfToken }
      })
        .then((response) => {
          if (!response.ok) {
            console.error('fetch attachment error', url, response)
            // TODO
            throw new Error(response.message)
          }
          return response.json()
        })
        .then((response) => {
          console.log(response)
          if (response.meta.next) {
            // TODO
            // the API has a hardcoded limit/pagesize of 50
            // would have to fetch multiple times to get all
            console.warn('not all attachments fetched')
          }
          const savedAttrs = this.documents.reduce((a, d) => {
            a[d.id] = {
              selected: d.selected,
              auto_approve: d.auto_approve
            }
            return a
          }, {})
          this.documents = this.buildDocuments(response.objects)
            .map((d) => ({ ...d, ...savedAttrs[d.id] }))
        })
    }
  }
}
</script>

<style lang="scss" scoped>
@import '@uppy/core/dist/style.css';
@import '@uppy/dashboard/dist/style.css';

.upload label.isMobile {
  display: block;
  text-align: center;
}
</style>
