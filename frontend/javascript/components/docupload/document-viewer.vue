<!-- the purpose of this component is to provide $root.config, specifically .i18n,
  to filingcabinet's document-viewer and its descendants -->
<template>
  <DocumentViewer
    :document-url="this.documentUrl"
    :document-preview="this.documentPreview"
    :page="this.page"
    :config="this.config"
    :defaults="this.defaults"
    ></DocumentViewer>
</template>

<script>

import DocumentViewer from '@okfde/filingcabinet/frontend/javascript/components/document-viewer.vue'

export default {
  components: {
    DocumentViewer
  },
  props: {
    documentUrl: {
      type: String,
      required: true
    },
    documentPreview: {
      type: Object,
      default: null
    },
    page: {
      type: Number,
      default: 1
    },
    config: {
      type: Object,
      default: () => ({})
    },
    defaults: {
      type: Object,
      default: () => ({})
    }
  },
  created() {
    this.$root.config = this.config
  }
}

</script>