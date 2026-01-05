<template>
  <div class="form-check form-check-emphasized">
    <input
      type="checkbox"
      v-model="terms"
      ref="terms"
      name="terms"
      class="form-check-input"
      :class="{ 'is-invalid': errors.terms && !termsChanged }"
      required=""
      id="id_terms"
      @change="updateTermsChanged(true)"
      />
    <label
      for="id_terms"
      class="form-check-label field-required"
      :class="{ 'text-danger': errors.terms && !termsChanged }">
      <span v-html="form.fields.terms.label"></span>
    </label>
  </div>
</template>

<script>
import { mapGetters, mapMutations } from 'vuex'

import {
  UPDATE_TERMS,
  UPDATE_TERMS_VALIDITY,
  UPDATE_TERMS_CHANGED,
} from '../../store/mutation_types'

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
        return this.$store.state.user.terms
      },
      set(value) {
        this.updateTerms(value)
      }
    },
    ...mapGetters([
      'termsChanged',
    ]),
  },
  methods: {
    validate() {
      this.updateTermsValidity(
        this.$refs.terms.reportValidity()
      )
    },
    ...mapMutations({
      updateTerms: UPDATE_TERMS,
      updateTermsValidity: UPDATE_TERMS_VALIDITY,
      updateTermsChanged: UPDATE_TERMS_CHANGED
    })
  }
}
</script>
