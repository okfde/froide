<template>
  <div>
    <div ref="uppy"></div>
    <template v-if="formFields">
      <input v-for="upload in uploads" type="hidden" name="upload" :value="upload" :key="upload"/>
    </template>
  </div>
</template>

<script>

import Vue from 'vue'

import Uppy from '@uppy/core'
import Tus from '@uppy/tus'
import Dashboard from '@uppy/dashboard'

import I18nMixin from '../../lib/i18n-mixin'
import {postData} from '../../lib/api.js'


export default {
  name: 'uploader',
  mixins: [I18nMixin],
  props: {
    config: {
      type: Object,
      required: true
    },
    formFields: {
      type: Boolean,
      default: true,
      required: false
    },
    allowedFileTypes: {
      type: Array,
      required: false
    },
    autoProceed: {
      type: Boolean,
      default: false,
      required: false
    }
  },
  data () {
    return {
      files: {},
      uploading: false
    }
  },
  computed: {
    csrf () {
      return document.querySelector('[name=csrfmiddlewaretoken]').value
    },
    canSubmit () {
      return this.hasFiles && this.uploadComplete
    },
    showSubmit () {
      return this.uploading || this.canSubmit
    },
    hasFiles () {
      return this.uploads.length > 0
    },
    uploadComplete () {
      for (let key in this.files) {
        if (this.files[key] === false) {
          return false
        }
      }
      return true
    },
    uploads () {
      const uploads = []
      for (let key in this.files) {
        if (this.files[key] !== false) {
          uploads.push(this.files[key])
        }
      }
      return uploads
    }
  },
  mounted () {
    const uppyLocale = {
      strings: this.config.i18n.uppy,
      pluralize: (n) => {
        if (n === 1) {
          return 0
        }
        return 1
      }
    }

    this.uppy = Uppy({
      autoProceed: this.autoProceed,
      locale: uppyLocale,
      restrictions: {
        allowedFileTypes: this.allowedFileTypes
      }
    })
    this.uppy.use(Dashboard, {
      inline: true,
      target: this.$refs.uppy,
      height: 400,
      showLinkToFileUploadResult: false,
      proudlyDisplayPoweredByUppy: false
    })
    this.uppy.use(Tus, {
      endpoint: this.config.url.tusEndpoint,
      chunkSize: this.config.settings.tusChunkSize,
      headers: {
        'X-CSRFToken': this.csrf
      }
    })
    this.uppy.on('file-added', (file) => {
      Vue.set(this.files, file.id, false)
      this.$emit('ready', this.canSubmit)
    })
    this.uppy.on('file-removed', (file) => {
      Vue.delete(this.files, file.id)
      this.$emit('ready', this.canSubmit)
    })
    this.uppy.on('upload', (data) => {
      this.uploading = true
      this.$emit('uploading', true)
    })
    this.uppy.on('upload-success', (file, response) => {
      Vue.set(this.files, file.id, response.uploadURL)
      this.$emit('ready', this.canSubmit)
      this.$emit('upload-success', {uppy: this.uppy, file, response})
    })
    this.uppy.on('complete', (result) => {
      console.log('successful files:', result.successful)
      console.log('failed files:', result.failed)
      this.uploading = false
      this.$emit('uploading', false)
    })
  }
}
</script>

<style lang="scss" scoped>
@import '~@uppy/core/dist/style.css';
@import '~@uppy/dashboard/dist/style.css';

</style>
