<template>
  <div>
    <div v-if="formFields.proof" class="mb-3 mt-3">
      <label
        class="fw-bold form-label"
        :class="{
          'field-required': proofRequired
        }"
        for="id_proof"
        >{{ formFields.proof.label }}</label
      >
      <select
        name="proof"
        class="form-select"
        id="id_proof"
        v-model="proof"
        :disabled="!!proofImage"
        :required="proofRequired"
      >
        <option
          v-for="option in formFields.proof.choices"
          :key="option.value"
          :value="option.value"
        >
          {{ option.label }}
        </option>
      </select>
      <div class="form-text">{{ formFields.proof.help_text }}</div>
    </div>

    <div v-if="formFields.proof" class="text-center fw-bold">
      {{ i18n.orUploadNewProof }}
    </div>

    <div class="mb-3 mt-3">
      <label
        class="fw-bold form-label"
        :class="{
          'field-required': proofImageRequired
        }"
        for="id_proof_name"
        >{{ formFields.proof_name.label }}</label
      >
      <input
        type="text"
        name="proof_name"
        class="form-control"
        maxlength="255"
        id="id_proof_name"
        :disabled="!!proof"
        :required="proofImageRequired"
      />

      <div class="form-text">{{ formFields.proof_name.help_text }}</div>
    </div>

    <div class="mb-3">
      <label
        class="fw-bold form-label"
        :class="{
          'field-required': proofImageRequired
        }"
        for="id_proof_image"
        >{{ formFields.proof_image.label }}</label
      >
      <ProofUpload
        name="proof_image"
        v-model="proofImage"
        :disabled="!!proof"
        :config="config"
        :required="proofImageRequired"
      />
    </div>

    <div class="mb-3">
      <div class="form-check">
        <input
          type="checkbox"
          name="proof_store"
          class="form-check-input"
          :disabled="!!proof"
          id="id_proof_store"
        />
        <label class="form-check-label fw-bold" for="id_proof_store">
          {{ formFields.proof_store.label }}
        </label>
      </div>
    </div>
  </div>
</template>

<script>
import I18nMixin from '../../lib/i18n-mixin'

import ProofUpload from './proof-upload.vue'

export default {
  name: 'ProofForm',
  components: {
    ProofUpload
  },
  mixins: [I18nMixin],
  props: {
    config: {
      type: Object
    },
    form: {
      type: Object,
      required: true
    },
    required: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      proof:
        this.form.fields.proof?.value ||
        this.form.fields.proof?.initial ||
        null,
      proofImage: null
    }
  },
  computed: {
    proofRequired() {
      return this.required && !this.proofImage
    },
    proofImageRequired() {
      return this.required && !this.proof
    },
    formFields() {
      return this.form.fields
    }
  },
  methods: {}
}
</script>
