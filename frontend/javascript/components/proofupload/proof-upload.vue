<template>
  <div class="mb-3 mt-3">
    <input
      class="form-control"
      type="file"
      :name="name"
      ref="image"
      @change="fileChanged"
      accept="image/*" />

    <div v-if="img" class="mt-3">
      <p>
        {{ i18n.redactionInstructions }}
      </p>
      <div class="d-flex justify-content-end">
        <button
          class="btn btn-outline-secondary"
          :disabled="!hasRedaction"
          :title="i18n.undo"
          @click.prevent="undoRedaction">
          <i class="fa fa-share fa-flip-horizontal" />
          {{ i18n.undo }}
        </button>
      </div>
      <div class="mt-2">
        <proof-redact
          :src="img.src"
          ref="redactor"
          @redacted="updateFile"
          @hasredaction="updateHasRedation" />
      </div>
    </div>
  </div>
</template>

<script>
import I18nMixin from '../../lib/i18n-mixin'

import ProofRedact from './proof-redact.vue'

function readImage(file) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader()
    fr.onload = () => {
      const img = new Image()
      img.onload = () => {
        resolve(img)
      }
      img.onerror = reject
      img.src = fr.result
    }
    fr.onerror = reject
    fr.readAsDataURL(file)
  })
}

export default {
  name: 'ProofUpload',
  components: {
    ProofRedact
  },
  mixins: [I18nMixin],
  props: {
    name: {
      type: String,
      required: true
    },
    config: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      img: null,
      hasRedaction: false,
      originalFile: null
    }
  },
  computed: {
    canUndo() {
      return this.$refs.redactor.canUndo
    }
  },
  methods: {
    fileChanged() {
      const imageInput = this.$refs.image
      if (!imageInput.files[0]) {
        this.img = null
        return
      }
      this.originalFile = imageInput.files[0]
      readImage(this.originalFile)
        .then((img) => {
          this.img = img
        })
        .catch((err) => {
          console.log(err)
        })
    },
    undoRedaction() {
      this.$refs.redactor.revert()
    },
    updateHasRedation(hasRedaction) {
      this.hasRedaction = hasRedaction
      if (!hasRedaction) {
        const dataTransfer = new DataTransfer()
        dataTransfer.items.add(this.originalFile)
        this.$refs.image.files = dataTransfer.files
      }
    },
    updateFile(blob) {
      const updatedFile = new File([blob], 'redacted.jpg', {
        type: 'image/jpeg',
        lastModified: new Date()
      })

      // Now let's create a DataTransfer to get a FileList
      const dataTransfer = new DataTransfer()
      dataTransfer.items.add(updatedFile)
      this.$refs.image.files = dataTransfer.files
    }
  }
}
</script>
