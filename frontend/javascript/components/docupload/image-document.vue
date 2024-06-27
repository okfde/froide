<template>
  <div class="document mb-3">
    <div :class="{ card: !simple }">
      <div v-show="!simple" ref="top" class="card-header">
        {{ i18n._('newDocumentPageCount', { count: numPages }) }}
      </div>
      <div :class="{ 'is-new': document.new, 'card-body': !simple }">
        <div
          v-if="converting"
          class="progress"
          role="progressbar"
          :aria-valuenow="progressCurrent ? progressCurrent : 0"
          aria-valuemin="0"
          aria-valuemax="100">
          <div
            class="progress-bar"
            :class="{
              'progress-bar-animated progress-bar-striped':
                progressCurrent === null
            }"
            :style="{ width: progressCurrent ? progressCurrent : '100%' }" />
        </div>
        <div v-else>
          <p v-if="!simple" class="text-body-secondary">
            {{ i18n.imageDocumentExplanation }}
          </p>
          <div v-if="!simple" class="mb-3">
            <label class="form-label" for="page-label">{{
              i18n.attachmentName
            }}</label>
            <input
              v-model="documentName"
              type="text"
              class="form-control"
              :placeholder="i18n.documentTitlePlaceholder" />
          </div>
          <!-- FIXME WIP: vuedraggable is not compatible with Vue3,
            could migrate to https://github.com/SortableJS/vue.draggable.next,
            but it is pracitically unmaintained and incompatible with our vue version?
            https://github.com/SortableJS/vue.draggable.next/issues/234
            there is an alternative
            https://github.com/SortableJS/vue.draggable.next/issues/186
            but it would not install with our current package.json/yarn.lock,
            `yarn add` just runs out of memory (circular dependency somehow?
            in an empty project it adds just fine)
          -->
          <!--
          <draggable
            v-model="pages"
            class="row pages bg-body-secondary"
            item-key="id"
            @start="drag = true"
            @end="drag = false">
            <template #item="{page}">
              <image-page
                :x-key="page.pageNum"
                :page="page"
                :page-count="pages.length"
                @pageupdated="$emit('pageupdated', { document, ...$event })"
                @splitpages="splitPages" />
            </template>
            <template #header>
              <span>header</span>
            </template>
            <template #footer>
              <span>footer</span>
            </template>
          </draggable>
          -->
          <!--
          <sortable
            :list="pages"
            item-key="id"
            tag="div"
            :options="{}">
            <template #header>
              <span>header</span>
            </template>
            <template #footer>
              <span>footer</span>
            </template>
            <template #item="{page, index}">
              <image-page
                :x-key="page.pageNum"
                :page="page"
                :page-count="pages.length"
                @pageupdated="$emit('pageupdated', { document, ...$event })"
                @splitpages="splitPages" />
            </template>
          </sortable>
          -->
          <div class="would-be-draggable">
            <image-page
              v-for="page in pages"
              :key="page.pageNum"
              :page="page"
              :page-count="pages.length"
              @pageupdated="$emit('pageupdated', { document, ...$event })"
              @splitpages="splitPages" />
          </div>
        </div>
        <div v-if="!simple" class="row mt-3">
          <div class="col-md-12">
            <p class="text-end">
              <button
                class="btn btn-primary mt-2"
                data-ref="image-document-convert-button"
                :disabled="anyUploads || converting"
                @click="convertImages">
                {{ i18n.convertImages }}
              </button>
              <file-review
                v-if="!basicOperations"
                :config="config"
                :document="document"
                @docupdated="updateDocument" />
              <file-basic-operations
                v-else
                :config="config"
                :document="document"
                @docupdated="updateDocument" />
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
// import draggable from 'vuedraggable'
// import { Sortable } from 'sortablejs-vue3'

import ImagePage from './image-page.vue'
import FileReview from './file-review.vue'
import FileBasicOperations from './file-basic-operations.vue'

import I18nMixin from '../../lib/i18n-mixin'
import { DocumentMixin } from './lib/document_utils'

import { postData } from '../../lib/api.js'

export default {
  name: 'ImageDocument',
  components: {
    // draggable,
    ImagePage,
    FileReview,
    FileBasicOperations
  },
  mixins: [I18nMixin, DocumentMixin],
  props: {
    config: {
      type: Object,
      required: true
    },
    document: {
      type: Object,
      required: true
    },
    simple: {
      type: Boolean,
      default: false
    },
    basicOperations: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      progressTotal: null,
      progressCurrent: null,
      converting: false
    }
  },
  computed: {
    numPages() {
      return this.pages.length
    },
    pages: {
      get: function () {
        return this.document.pages
      },
      set: function (pages) {
        this.$emit('pageschanged', pages)
      }
    },
    documentName: {
      get: function () {
        return this.document.name
      },
      set: function (name) {
        this.$emit('namechanged', name)
      }
    },
    anyUploads() {
      return !this.pages.every((p) => {
        return p && p.id
      })
    }
  },
  mounted() {
    if (this.document.new) {
      window.setTimeout(() => this.$emit('notnew'), 2000)
    }
  },
  methods: {
    splitPages(pageNum) {
      this.$emit('splitpages', pageNum)
    },
    convertImages() {
      this.converting = true
      this.$refs.top.scrollIntoView(true)
      const data = {
        action: 'convert_to_pdf',
        title: this.document.name,
        images: this.pages.map((p) => {
          return {
            id: p.id,
            rotate: (p.rotate || 0) + (p.implicitRotate || 0)
          }
        })
      }
      postData(
        this.$root.url.convertAttachments,
        data,
        this.$root.csrfToken
      ).then((attachment) => {
        this.$emit('imagesconverted', {
          attachment,
          imageDoc: this.document
        })
      })
    }
  }
}
</script>

<style lang="scss" scoped>
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
