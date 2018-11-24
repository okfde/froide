<template>
  <div class="row">
    <div class="col-md-12">
      <div class="card mb-3">
        <div class="card-body">
          <div class="form-group row">
            <div class="col-lg-9">
              <div class="form-check">
                <label class="form-check-label field-required"  :class="{ 'text-danger': errors.terms }">
                  <input type="checkbox" v-model="termsValue" name="terms" class="form-check-input" :class="{ 'is-invalid': errors.terms }" required="" id="id_terms">
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
  name: 'user-terms',
  props: {
    form: {
      type: Object
    }
  },
  data () {
    return {
      terms: this.form.fields.terms.value || this.form.fields.terms.initial
    }
  },
  computed: {
    formFields () {
      return this.form.fields
    },
    errors () {
      if (this.form) {
        return this.form.errors
      }
      return {}
    },
    termsValue: {
      get() {
        return this.terms
      },
      set (value) {
        this.terms = value
        this.$emit('update:initialTerms', value)
      }
    }
  }
}
</script>