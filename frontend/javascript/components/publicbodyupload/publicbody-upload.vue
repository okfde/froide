<template>
  <div class="publicbody-upload mb-3 mt-3">
    <file-uploader
      :config="config" class="mb-3 mt-3"
      @ready="canSubmit = $event"
      @uploading="uploading = $event"
    />
    <div class="text-right mt-3">
      <button type="submit" class="btn btn-lg btn-primary" :disabled="!canSubmit">
        <span v-if="uploading" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
        {{ i18n.createResponse }}
      </button>
    </div>
  </div>
</template>

<script>

import Vue from 'vue'

import FileUploader from '../upload/file-uploader.vue'

import I18nMixin from '../../lib/i18n-mixin'

export default {
  name: 'publicbody-upload',
  mixins: [I18nMixin],
  props: ['config'],
  components: {
    FileUploader
  },
  data () {
    return {
      canSubmit: false,
      uploading: false
    }
  },
  
}
</script>
