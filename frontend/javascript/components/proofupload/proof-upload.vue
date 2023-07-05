<template>
  <div class="mb-3">
    <input
      class="form-control"
      type="file"
      :name="name"
      ref="image"
      @change="fileChanged"
      accept="image/*" />

    <div v-if="img" class="mt-3">
      <div class="row">
        <div class="col d-flex align-items-center">
          {{ i18n.redactionInstructions }}
        </div>
        <div class="col-auto d-flex align-items-center">
          <button
            class="btn btn-sm btn-outline-secondary"
            :disabled="!hasRedaction"
            :title="i18n.undo"
            @click.prevent="undoRedaction">
            <i class="fa fa-share fa-flip-horizontal" />
            {{ i18n.undo }}
          </button>
        </div>
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
      hasRedaction: false
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
      readImage(imageInput.files[0])
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
    },
    updateFile(blob) {
      let filename
      if (this.hasRedaction) {
        filename = 'redacted_proof.jpg'
      } else {
        filename = 'resized_proof.jpg'
      }
      const updatedFile = new File([blob], filename, {
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
