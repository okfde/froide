<template>
  <div class="document mb-3">
    <div class="card">
      <div class="card-header" ref="top">
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
          <draggable v-model="pages" @start="drag=true" @end="drag=false" class="row pages bg-light">
              <image-page v-for="page in pages" :key="page.pageNum"
                :page="page"
                :page-count="pages.length"
                @pageupdated="$emit('pageupdated', {document, ...$event})"
                @splitpages="splitPages"
              ></image-page>
          </draggable>
        </div>
        <div class="row mt-3">
          <div class="col-md-8 text-muted">
            {{ i18n.imageDocumentExplanation }} 
          </div>
          <div class="col-md-4">
            <p class="text-right">
              <button class="btn btn-primary mt-2" :disabled="anyUploads || converting" @click="convertImages">
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

import ImagePage from './image-page.vue'

import I18nMixin from '../../lib/i18n-mixin'
import {postData} from '../../lib/api.js'

const range = (len) => [...Array(len).keys()]

export default {
  name: 'image-document',
  mixins: [I18nMixin],
  props: ['config', 'document'],
  components: {
    draggable,
    ImagePage
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
      return !this.pages.every((p) => {
        return p.attachment && p.attachment.id
      })
    },
  },
  methods: {
    splitPages (pageNum) {
      this.$emit('splitpages', pageNum)
    },
    convertImages () {
      this.converting = true
      this.$refs.top.scrollIntoView(true)
      let data = {
        action: 'convert_to_pdf',
        title: this.document.name,
        images: this.pages.map((p) => {
          return {
            id: p.attachment.id,
            rotate: (p.rotate || 0) + (p.implicitRotate || 0)
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
    display: flex;
    flex-wrap: nowrap;
    align-items: baseline;
    overflow: auto;
    overflow-x: scroll;
    overflow-scrolling: touch;
    padding-bottom: 2rem;
  }

</style>
