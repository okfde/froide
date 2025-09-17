<template>
  <div class="row">
    <div class="col-md-12">
      <div class="card mb-3">
        <div class="card-body">
          <div class="mb-3 row">
            <div class="col-lg-9">
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
            </div>
          </div>
        </div>
      </div>
    </div>
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
