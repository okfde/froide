<template>
  <div class="document mb-3" :id="attachmentId">
    <div class="card">
      <div class="card-header">
        <file-header :config="config" :document="document"></file-header>
      </div>
      <div class="card-body" :class="{'is-new': document.new}">
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
        <template v-if="ready">
          <file-review :config="config" :document="document"
            @docupdated="updateDocument"
            @loadpdf="$emit('loadpdf')"
            @makerelevant="$emit('makerelevant')"
            :can-preview="true"
          ></file-review>
        </template>
        <div v-else>
          <div class="spinner-border spinner-border-sm" role="status">
            <span class="sr-only">{{ i18n.loading }}</span>
          </div>
          <p v-if="document.pending">
            {{ i18n.documentPending }}
          </p>
          <p v-if="document.deleting">
            {{ i18n.documentDeleting }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import I18nMixin from '../../lib/i18n-mixin'
import DocumentMixin from './lib/document_mixin'

import FileReview from './file-review.vue'
import FileHeader from './file-header.vue'

const range = (len) => [...Array(len).keys()]

export default {
  name: 'file-document',
  mixins: [I18nMixin, DocumentMixin],
  props: ['config', 'document'],
  components: {
    FileReview, FileHeader
  },
  data () {
    return {
        progressTotal: null,
        progressCurrent: null,
        pdf: null,
        numPages: null,
        pdfPages: []
    }
  },
  mounted () {
    if (this.document.new) {
      window.setTimeout(() => this.$emit('notnew'), 2000);
    }
    if (this.document.pending) {
      this.checkProgress()
    }
  },
  computed: {
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
    approveUrl () {
      return this.config.url.approveAttachment.replace('/0/', `/${this.document.id}/`)
    },
    attachmentUrl () {
      return this.config.url.getAttachment.replace('/0/', `/${this.document.id}/`)
    },
    deleteUrl () {
      return this.config.url.deleteAttachment.replace('/0/', `/${this.document.id}/`)
    },
    attachmentId () {
      return `attachment-${this.document.id}`
    }
  },
  methods: {

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
              component: 'fullpdf-document',
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
  .document {
    margin-top: 2rem;
  }
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
</style>
