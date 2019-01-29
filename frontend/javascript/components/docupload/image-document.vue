<template>
  <div class="document mb-3">
    <div class="card">
      <div class="card-header">
        {{ i18n._('newDocumentPageCount', {count: numPages} ) }}
      </div>
      <div class="card-body" :class="{'is-new': document.new}">
        <div v-if="converting" class="progress">
          <div class="progress-bar"
          :class="{'progress-bar-animated progress-bar-striped': progressCurrent === null}"
          :style="{'width': progressCurrent ? progressCurrent : '100%'}"
          role="progressbar" :aria-valuenow="progressCurrent ? progressCurrent : 0"
          aria-valuemin="0" aria-valuemax="100"></div>
        </div>
        <div v-else>
          <div class="form-group">
            <label for="page-label">{{ i18n.documentTitle }}</label>
            <input v-model="documentName" type="text" class="form-control" :placeholder="i18n.documentTitlePlaceholder">
          </div>
          <draggable v-model="pages" @start="drag=true" @end="drag=false" class="pages">
            <div v-for="page in pages" :key="page.pageNum" class="page">
              <img v-if="page.url" :src="page.url" alt="" class="page-image"/>
              <div class="float-right" v-if="page.pageNum != pages.length">
                <button class="btn btn-sm text-muted small" @click="splitPages(page.pageNum)">
                  <span class="fa fa-scissors"></span>
                </button>
              </div>
              <div class="text-center">
                {{ page.pageNum }}
              </div>
              <div v-if="page.uploading" class="progress">
                <div class="progress-bar"
                  :class="{'progress-bar-animated progress-bar-striped': page.progressPercent === null}"
                  :style="{'width': page.progress ? page.progressPercentLabel : '100%'}"
                  role="progressbar" :aria-valuenow="page.progressPercent ? page.progressPercent : 0"
                  aria-valuemin="0" aria-valuemax="100"></div>
              </div>
            </div>
          </draggable>
        </div>
        <div class="row mt-3">
          <div class="col-md-8 text-muted">
            {{ i18n.imageDocumentExplanation }} 
          </div>
          <div class="col-md-4">
            <p class="text-right">
              <button class="btn btn-primary" :disabled="anyUploads || converting" @click="convertImages">
                {{ i18n.convertImages }}
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>

import draggable from 'vuedraggable'

import I18nMixin from '../../lib/i18n-mixin'

function postData (url = '', data = {}, csrfToken) {
  return window.fetch(url, {
    method: 'POST',
    cache: 'no-cache',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    body: JSON.stringify(data)
  }).then(response => response.json())
}

const range = (len) => [...Array(len).keys()]

export default {
  name: 'image-document',
  mixins: [I18nMixin],
  props: ['config', 'document'],
  components: {
    draggable
  },
  data () {
    return {
      progressTotal: null,
      progressCurrent: null,
      converting: false,
    }
  },
  mounted () {
    if (this.document.new) {
      window.setTimeout(() => this.$emit('notnew'), 2000);
    }
  },
  computed: {
    numPages () {
      return this.pages.length
    },
    pages: {
      get: function() {
        return this.document.pages
      },
      set: function (pages) {
        this.$emit('pageschanged', pages)
      }
    },
    documentName: {
      get: function() {
        return this.document.name
      },
      set: function (name) {
        this.$emit('namechanged', name)
      }
    },
    anyUploads () {
      return this.pages.some((p) => p.uploading)
    }
  },
  methods: {
    splitPages (pageNum) {
      if (pageNum)
      this.$emit('splitpages', pageNum)
    },
    convertImages () {
      this.converting = true
      let data = {
        action: 'convert_to_pdf',
        title: this.document.name,
        images: this.pages.map((p) => {
          return {
            id: p.attachment.id,
            rotate: 0
          }
        })
      }
      postData(
        this.$root.url.convertAttachments,
        data,
        this.$root.csrfToken
      ).then((response) => {
        this.$emit('imagesconverted', {
          document: response,
          imageDoc: this.document
        })
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
    max-width: 75px;
    height: 120px;
    margin: 0 1rem;
    cursor: move;
  }
  .page-image {
    padding: 0 0.25rem;
    width: 100%;
    border: 1px solid #bbb;
  }

</style>
