<template>
  <div class="publicbody-upload mb-3 mt-3">
    <div class="text-end mt-3">
      <button
        v-if="canSubmit"
        type="submit"
        class="btn btn-lg btn-primary"
        @click="submitting = true"
      >
        <span
          v-if="uploading"
          class="spinner-border spinner-border-sm"
          role="status"
          aria-hidden="true"
        />
        {{ gettext('Create response now') }}
      </button>
    </div>
    <FileUploader
      :config="config"
      class="mb-3 mt-3"
      :auto-proceed="true"
      :allow-remove="false"
      :required="true"
      @ready="canSubmit = $event"
      @uploading="uploading = $event"
    />
    <div class="text-end mt-3">
      <button
        type="submit"
        class="btn btn-lg btn-primary"
        :disabled="!canSubmit"
        @click="submitting = true"
      >
        <span
          v-if="uploading"
          class="spinner-border spinner-border-sm"
          role="status"
          aria-hidden="true"
        />
        {{ gettext('Create response now') }}
      </button>
    </div>
  </div>
</template>

<script>
import FileUploader from '../upload/file-uploader.vue'

import { translateMixin } from 'vuepo/vue'

export default {
  name: 'PublicbodyUpload',
  components: {
    FileUploader
  },
  mixins: [translateMixin],
  props: {
    config: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      canSubmit: false,
      uploading: false,
      submitting: false
    }
  },
  mounted() {
    window.addEventListener('beforeunload', (e) => {
      if (!this.canSubmit && !this.uploading) {
        return
      }
      if (this.submitting) {
        return
      }
      // If you prevent default behavior in Mozilla Firefox prompt will always be shown
      e.preventDefault()
      // Chrome requires returnValue to be set
      e.returnValue = this.gettext(
        'You have not completed this process. Are you sure you want to cancel?'
      ).value
      return e.returnValue
    })
  }
}
</script>
