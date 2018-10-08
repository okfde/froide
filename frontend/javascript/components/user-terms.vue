<template>
  <div class="row">
    <div class="col-md-12">
      <div class="card mb-3">
        <div class="card-body">
          <div class="form-group row">
            <div class="col-lg-9">
              <div class="form-check">
                <label class="form-check-label  field-required">
                  <input type="checkbox" v-model="termsValue" name="terms" class="form-check-input" required="" id="id_terms">
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