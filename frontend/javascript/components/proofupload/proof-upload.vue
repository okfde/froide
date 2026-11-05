<template>
  <div class="mb-3">
    <p class="small">
      <i class="fa fa-exclamation-triangle"></i>
      {{
        gettext(
          'When you upload an identity document, please redact all information except your name, the city and the validity date. After selecting an image, you can apply redactions to it.'
        )
      }}
    </p>
    <div class="input-group mb-3">
      <input
        class="form-control"
        type="file"
        :name="name"
        ref="image"
        :required="required"
        :disabled="disabled"
        @change="fileChanged"
        accept="image/*"
      />
      <button
        class="btn btn-sm btn-outline-secondary"
        :disabled="!hasFile"
        :title="gettext('Reset')"
        @click.prevent="resetFile"
      >
        <i class="fa fa-times-circle" />
        {{ gettext('Reset') }}
      </button>
    </div>
    <div v-if="img" class="mt-3">
      <div class="row">
        <div class="col-12 col-md d-flex align-items-center">
          {{
            gettext(
              'Click or touch and drag over the image to redact parts of it.'
            )
          }}
        </div>
        <div class="col-auto d-flex align-items-center">
          <button
            class="btn btn-sm btn-outline-secondary"
            :disabled="!hasRedaction"
            :title="gettext('Undo')"
            @click.prevent="undoRedaction"
          >
            <i class="fa fa-share fa-flip-horizontal" />
            {{ gettext('Undo') }}
          </button>
        </div>
      </div>
      <div class="mt-2">
        <ProofRedact
          :src="img.src"
          ref="redactor"
          @redacted="updateFile"
          @hasredaction="updateHasRedation"
        />
      </div>
    </div>
  </div>
</template>

<script>
import { translateMixin } from 'vuepo/vue'

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
  mixins: [translateMixin],
  props: {
    name: {
      type: String,
      required: true
    },
    required: {
      type: Boolean,
      required: false,
      default: false
    },
    disabled: {
      type: Boolean,
      required: false,
      default: false
    }
  },
  emits: ['input'],
  data() {
    return {
      img: null,
      hasRedaction: false
    }
  },
  computed: {
    canUndo() {
      return this.$refs.redactor.canUndo
    },
    hasFile() {
      return this.img !== null
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
    resetFile() {
      this.$refs.image.value = ''
      this.img = null
      this.hasRedaction = false
      this.$emit('input', null)
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
      this.$emit('input', updatedFile)
    }
  }
}
</script>
