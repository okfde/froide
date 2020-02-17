<template>
  <div class="publicbody-upload mb-3 mt-3">
    <div id="uppy"></div>
    <div class="text-right mt-3">
      <form action="" method="post">
        <input type="hidden" name="csrfmiddlewaretoken" :value="csrf"/>
        <input v-for="upload in uploads" type="hidden" name="upload" :value="upload" :key="upload"/>
        <button v-if="showSubmit" type="submit" class="btn btn-lg btn-primary" :disabled="!canSubmit">
          {{ i18n.createDocuments }}
        </button>
      </form>
    </div>
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
  name: 'document-uploader',
  mixins: [I18nMixin],
  props: ['config'],
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
      autoProceed: false,
      locale: uppyLocale,
      restrictions: {
        allowedFileTypes: [
          'application/pdf'
        ]
      }
    })
    this.uppy.use(Dashboard, {
      inline: true,
      target: '#uppy',
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
    })
    this.uppy.on('file-removed', (file) => {
      Vue.delete(this.files, file.id)
    })
    this.uppy.on('upload', (data) => {
      this.uploading = true
    })
    this.uppy.on('upload-success', (file, response) => {
      Vue.set(this.files, file.id, response.uploadURL)
    })
    this.uppy.on('complete', (result) => {
      console.log('successful files:', result.successful)
      console.log('failed files:', result.failed)
      this.uploading = false
    })
  }
}
</script>

<style lang="scss" scoped>
@import '~@uppy/core/dist/style.css';
@import '~@uppy/dashboard/dist/style.css';

</style>
