<template>
  <div class="form-check">
    <input
      type="checkbox"
      v-model="terms"
      name="terms"
      class="form-check-input"
      :class="{ 'is-invalid': errors.terms }"
      required=""
      id="id_terms" />
    <label
      for="id_terms"
      class="form-check-label field-required"
      :class="{ 'text-danger': errors.terms }">
      <span v-html="form.fields.terms.label"></span>
    </label>
  </div>
</template>

<script>
export default {
  name: 'UserTerms',
  props: {
    form: {
      type: Object
    },
    initialTerms: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      termsValue: this.initialTerms
    }
  },
  computed: {
    formFields() {
      return this.form.fields
    },
    errors() {
      if (this.form) {
        return this.form.errors
      }
      return {}
    },
    terms: {
      get() {
        return this.termsValue
      },
      set(value) {
        this.termsValue = value
        this.$emit('update:initialTerms', value)
      }
    }
  }
}
</script>
