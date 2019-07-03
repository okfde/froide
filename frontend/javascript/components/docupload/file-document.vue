<template>
  <div class="document mb-1" :id="attachmentId" :class="{'is-new': document.new}">
    <div class="row">
      <div class="col-auto">
        <input v-if="ready" v-model="selected" type="checkbox"/>
        <div v-else class="spinner-border spinner-border-sm" role="status">
          <span class="sr-only">{{ i18n.loading }}</span>
        </div>
      </div>
      <div class="col px-0">
        <small v-if="document.pending">
          {{ i18n.documentPending }}
        </small>
        <small v-if="document.deleting">
          {{ i18n.documentDeleting }}
        </small>

        <small :title="attachment.name">{{ documentTitle }}</small>

        <a v-if="canOpen" :href="attachment.site_url" :title="i18n.openAttachmentPage">
          <i class="fa fa-external-link"></i>
        </a>

        <div v-if="document.uploading" class="progress">
          <div class="progress-bar"
            :class="{
              'progress-bar-animated progress-bar-striped': progressAlmostComplete,
              'bg-info progress-bar-striped': progressUnknown,
            }"
            :style="{'width': progressPercentLabel}"
            role="progressbar" :aria-valuenow="document.progress"
            aria-valuemin="0" aria-valuemax="100"></div>
        </div>
      </div>
      <div class="col-auto doc-status">
        <template v-if="hasAttachment">
          <span v-if="!approved" class="badge badge-pill badge-secondary" data-toggle="tooltip" data-placement="top" :title="i18n.notPublic">
            &nbsp;
          </span>
          <span v-if="isRedacted" class="badge badge-pill badge-dark" data-toggle="tooltip" data-placement="top" :title="i18n.redacted">
            &nbsp;
          </span>
          <span v-if="isProtected" class="badge badge-pill badge-info" data-toggle="tooltip" data-placement="top" :title="i18n.protectedOriginalExplanation">
            &nbsp;
          </span>
        </template>
      </div>
      <div class="col-md-2 text-center">
        <button v-if="canMakeResult" class="btn btn-sm btn-outline-success"
          :disabled="attachment.document"
          @click="makeResult"
          data-toggle="tooltip" data-placement="top" :title="i18n.makeResultExplanation"
        >
          <i class="fa fa-certificate"></i>
          {{ i18n.isResult }}
        </button>
        <template v-else-if="hasDocument">
          <a :href="attachment.site_url" target="_blank">
            <i class="fa fa-certificate"></i>
          </a>
          <button class="btn btn-sm ml-1"
            :class="{'btn-light': !editDocumentMeta, 'btn-secondary': editDocumentMeta}"
            @click.prevent="editDocumentMeta = !editDocumentMeta"
          >
            <span class="sr-only">{{ i18n.edit }}</span>
            <i class="fa fa-edit"></i>
          </button>
        </template>
      </div>
      <div class="col-md-4">
        <template v-if="ready">
          <file-review :config="config" :document="document"
            @docupdated="updateDocument"
            @makerelevant="$emit('makerelevant')"
          ></file-review>
        </template>
      </div>
      <div class="col-auto">
        <button v-if="ready && attachment.is_pdf" class="btn btn-sm"
          :class="{'btn-light': !document.previewPdf, 'btn-secondary': document.previewPdf}"
          @click.prevent="$emit('docupdated', {previewPdf: !document.previewPdf})"
        >
          <i class="fa" :class="{'fa-caret-square-o-right': !document.previewPdf, 'fa-caret-square-o-down': document.previewPdf}"></i>
          <!-- {{ i18n.loadPreview }} -->
        </button>
      </div>
    </div>
    <div v-if="editDocumentMeta" class="row">
      <div class="col mt-1">
        <div class="card">
          <div class="card-body">
            <form @submit.prevent="saveDocumentMeta">
              <div class="form-group row">
                <label class="col-sm-2 col-form-label" :for="'doc-title' + doc.id">{{ i18n.documentTitle }}</label>
                <div class="col-sm-10">
                  <input v-model="title" type="text" class="form-control" :id="'doc-title' + doc.id" :placeholder="i18n.title">
                  <small class="form-text text-muted">{{ i18n.documentTitleHelp }}</small>
                </div>
              </div>
              <div class="form-group row mb-0">
                <label class="col-sm-2 col-form-label" :for="'doc-title' + doc.id">{{ i18n.description }}</label>
                <div class="col-sm-10">
                  <textarea v-model="description" :id="'doc-description' + doc.id" class="form-control" rows="3"></textarea>
                  <small class="form-text text-muted">{{ i18n.descriptionHelp }}</small>
                </div>
              </div>
              <p class="text-right mb-0">
                <button type="submit" class="btn btn-primary">{{ i18n.save }}</button>
              </p>
            </form>
          </div>
        </div>
      </div>
    </div>
    <div v-if="document.previewPdf" class="row">
      <div class="col mt-1">
        <pdf-preview :config="config" :document="document"></pdf-preview>
      </div>
    </div>
  </div>
</template>

<script>
import I18nMixin from '../../lib/i18n-mixin'
import {DocumentMixin} from './lib/document_utils'

import FileReview from './file-review.vue'
import PdfPreview from './pdf-preview.vue'

const range = (len) => [...Array(len).keys()]

export default {
  name: 'file-document',
  mixins: [I18nMixin, DocumentMixin],
  props: ['config', 'document'],
  components: {
    FileReview, PdfPreview
  },
  data () {
    return {
      progressTotal: null,
      progressCurrent: null,
      pdf: null,
      numPages: null,
      pdfPages: [],
      editDocumentMeta: false,
      title: null,
      description: null
    }
  },
  mounted () {
    if (this.document.new) {
      window.setTimeout(() => this.$emit('notnew'), 2000);
    }
    if (this.document.pending) {
      this.checkProgress()
    }
    this.title = this.hasDocument ? this.doc.title : null
    this.description = this.hasDocument ? this.doc.description : null
    if (this.hasDocument && this.documentTitle.indexOf('.pdf') !== -1) {
      this.editDocumentMeta = true
    }
  },
  computed: {
    attachment () {
      return this.document.attachment
    },
    doc () {
      return this.document.attachment.document
    },
    documentTitle () {
      return this.hasDocument ? this.doc.title : this.attachment.name
    },
    hasAttachment () {
      return !!this.document.attachment
    },
    hasDocument () {
      return this.hasAttachment && !!this.attachment.document
    },
    working () {
      return this.document.approving || this.document.deleting
    },
    canApprove () {
      return this.attachment && !this.attachment.approved && this.attachment.can_approve
    },
    canDelete () {
      return this.attachment && this.attachment.can_delete && !this.document.approving
    },
    canReview () {
      return this.attachment && this.attachment.can_redact
    },
    canOpen () {
      return !this.canApprove || !this.canReview
    },
    canMakeResult () {
      return !this.hasDocument && this.attachment && this.attachment.is_pdf && !(
        this.attachment.redacted || this.attachment.converted || this.creatingDocument
      )
    },
    isProtected () {
      return (this.attachment.converted && !this.attachment.approved) || this.attachment.redacted
    },
    isRedacted () {
      return this.attachment.is_redacted
    },
    approved () {
      return this.attachment.approved
    },
    pages () {
      return this.document.pages
    },
    ready () {
      return !this.document.pending && !this.document.deleting
    },
    progressAlmostComplete () {
      return !this.progressUnknown && this.document.progress === this.document.progressTotal
    },
    progressUnknown () {
      return this.progressPercent === null
    },
    progressPercent () {
      if (!this.document.progressTotal) {
        return null
      }
      return this.document.progress / this.document.progressTotal * 100
    },
    progressPercentLabel () {
      if (this.progressPercent) {
        return `${this.progressPercent}%`
      }
      return '100%'
    },
    attachment () {
      return this.document.attachment
    },
    attachmentId () {
      return `attachment-${this.document.id}`
    },
    selected: {
      get () {
        return !!this.document.selected
      },
      set () {
        this.$emit('docupdated', {selected: !this.document.selected})
      }
    }
  },
  methods: {
    makeResult () {
      this.updateDocument({
        creatingDocument: true
      })
    },
    saveDocumentMeta () {
      this.editDocumentMeta = false
      this.updateDocument({
        updatingDocument: {
          title: this.title,
          description: this.description
        }
      }).catch((err) => {
        this.editDocumentMeta = true
        alert(err)
      })
    },
    checkProgress () {
      window.fetch(`/api/v1/attachment/${this.document.id}/`)
        .then(response => response.json()).then((data) => {
          if (data.pending === true) {
            window.setTimeout(() => this.checkProgress(), 5000);
            return
          } else if (data.pending === false) {
            this.$emit('docupdated', {
              pending: false,
              new: true,
              site_url: data.site_url,
              file_url: data.file_url,
            })
          } else {
            document.location.reload()
          }
        }).catch(() => {
          window.setTimeout(() => this.checkProgress(), 5000);
        })
    }
  }
}
</script>

<style lang="scss" scoped>
  .pages {
    padding-left: 0;
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
  .document:not(:last-child) {
    padding-bottom: 5px;
    border-bottom: 1px solid #ccc;
  }
  .doc-status .badge {
    cursor: help;
  }
</style>
