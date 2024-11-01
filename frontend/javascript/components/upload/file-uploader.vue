<template>
  <div>
    <div ref="uppy"></div>
    <template v-if="formFields">
      <input
        v-for="upload in uploads"
        :key="upload"
        type="hidden"
        :name="name"
        :value="upload"
      />
      <input
        v-if="!canSubmit"
        type="hidden"
        name="upload-pending"
        value=""
        required
      />
    </template>
  </div>
</template>

<script>
import Uppy from '@uppy/core'
import Tus from '@uppy/tus'
import Dashboard from '@uppy/dashboard'

import '@uppy/core/dist/style.css'
import '@uppy/dashboard/dist/style.css'

import I18nMixin from '../../lib/i18n-mixin'

export default {
  name: 'FileUploader',
  mixins: [I18nMixin],
  props: {
    config: {
      type: Object,
      required: true
    },
    name: {
      type: String,
      default: 'upload'
    },
    formFields: {
      type: Boolean,
      default: true,
      required: false
    },
    required: {
      type: Boolean,
      default: false,
      required: false
    },
    allowedFileTypes: {
      type: Array,
      required: false,
      default: null
    },
    autoProceed: {
      type: Boolean,
      default: false,
      required: false
    },
    allowRemove: {
      type: Boolean,
      default: true,
      required: false
    }
  },
  data() {
    return {
      files: {},
      uploading: false
    }
  },
  computed: {
    csrf() {
      return document.querySelector('[name=csrfmiddlewaretoken]').value
    },
    canSubmit() {
      return (!this.required || this.hasFiles) && this.uploadComplete
    },
    showSubmit() {
      return this.uploading || this.canSubmit
    },
    hasFiles() {
      return this.uploads.length > 0
    },
    uploadComplete() {
      for (const key in this.files) {
        if (this.files[key] === false) {
          return false
        }
      }
      return true
    },
    uploads() {
      const uploads = []
      for (const key in this.files) {
        if (this.files[key] !== false) {
          uploads.push(this.files[key])
        }
      }
      return uploads
    }
  },
  mounted() {
    const uppyLocale = {
      strings: this.config.i18n.uppy,
      pluralize: (n) => {
        if (n === 1) {
          return 0
        }
        return 1
      }
    }

    this.uppy = new Uppy({
      autoProceed: this.autoProceed,
      locale: uppyLocale,
      restrictions: {
        allowedFileTypes: this.allowedFileTypes
      }
    })
    this.uppy.use(Dashboard, {
      theme: document.documentElement.getAttribute('data-bs-theme') || 'light',
      inline: true,
      target: this.$refs.uppy,
      height: 250,
      showLinkToFileUploadResult: false,
      proudlyDisplayPoweredByUppy: false,
      showRemoveButtonAfterComplete: this.allowRemove,
      doneButtonHandler: null
    })
    this.uppy.use(Tus, {
      endpoint: this.config.url.tusEndpoint,
      chunkSize: this.config.settings.tusChunkSize,
      headers: {
        'X-CSRFToken': this.csrf
      }
    })
    this.uppy.on('file-added', (file) => {
      this.files[file.id] = false
      this.$emit('ready', this.canSubmit)
    })
    this.uppy.on('file-removed', (file) => {
      delete this.files[file.id]
      this.$emit('ready', this.canSubmit)
    })
    this.uppy.on('upload', () => {
      this.uploading = true
      this.$emit('uploading', true)
    })
    this.uppy.on('upload-success', (file, response) => {
      this.files[file.id] = response.uploadURL
      this.$emit('ready', this.canSubmit)
      this.$emit('upload-success', { uppy: this.uppy, file, response })
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
