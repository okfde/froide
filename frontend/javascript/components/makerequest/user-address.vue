<template>
  <div class="row">
    <label
      for="id_address"
      class="col-sm-4 col-md-3 col-form-label"
      :class="{
        'text-danger': (errors.address && !addressChanged) || addressValid === false,
        'field-required': requiresPostalAddress
      }">
      {{ i18n.yourAddress }}
    </label>
    <div class="col-sm-8 col-md-5">
      <div>
        <textarea
          v-model="address"
          ref="address"
          name="address"
          class="form-control"
          :class="{ 'is-invalid': (errors.address && !addressChanged ) || addressValid === false}"
          :placeholder="formFields.address.placeholder"
          :required="requiresPostalAddress"
          @change="addressUpdated(true)"
          @keyup="addressUpdated()"
          />
        <p class="help-block">
          <span v-html="addressHelpText" />
        </p>
        <div
          v-if="!clearFormErrors && errors.address"
          class="alert mb-2"
          :class="{ 'alert-danger': !addressChanged, 'alert-warning': addressChanged }"
          >
          <ul class="list-unstyled my-0">
            <li v-for="e in errors.address" :key="e.message">
              {{ e.message }}
            </li>
          </ul>
        </div>
        <div
          v-else-if="addressValidationErrors.length > 0"
          class="alert mb-2"
          :class="{ 'alert-danger': !addressChanged, 'alert-warning': addressChanged }"
          >
          <ul class="list-unstyled my-0">
            <li v-for="error in addressValidationErrors" :key="error" style="white-space: pre-line">
              {{ error }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>

import { mapGetters, mapMutations } from 'vuex'

import {
  UPDATE_ADDRESS,
  UPDATE_ADDRESS_VALIDITY,
  UPDATE_ADDRESS_CHANGED
} from '../../store/mutation_types'

let addressRegex

export default {
  name: 'UserAddress',
  props: {
    i18n: {
      type: Object,
      required: true
    },
    config: {
      type: Object
    },
    form: {
      type: Object
    },
    addressHelpText: {
      type: String,
      default: null
    },
    addressRequired: {
      type: Boolean,
      default: false
    },
  },
  data() {
    return {
      validateLive: false,
      clearFormErrors: false,
      addressValidationErrors: []
    }
  },
  created() {
    if (!this.address && this.user) {
      this.address = this.user.address
    }
    addressRegex = new RegExp(this.config.settings.address_regex)
  },
  methods: {
    addressUpdated(enableValidateLive) {
      if (!this.validateLive && !enableValidateLive) return
      this.validateLive = true
      this.updateAddressChanged(true)
      this.validate()
    },
    validate() {
      this.addressValidationErrors = []
      if (!this.$refs.address.reportValidity()) {
        this.updateAddressValidity(false)
        return
      }
      let valid = true
      if (this.address && addressRegex && !addressRegex.test(this.address)) {
        valid = false
        this.addressValidationErrors.push(this.i18n.pleaseFollowAddressFormat)
      }
      if (valid) {
        this.clearFormErrors = true
      }
      this.updateAddressValidity(valid)
    },
    ...mapMutations({
      updateAddress: UPDATE_ADDRESS,
      updateAddressChanged: UPDATE_ADDRESS_CHANGED,
      updateAddressValidity: UPDATE_ADDRESS_VALIDITY,
    })
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
    addressHelpTextValue() {
      if (this.addressHelpText !== null) {
        return this.addressHelpText
      }
      return this.formFields.address.help_text
    },
    address: {
      get() {
        return this.$store.state.user.address
      },
      set(value) {
        this.updateAddress(value)
      }
    },
    requiresPostalAddress() {
      if (this.addressRequired) {
        return true
      }
      if (this.defaultLaw) {
        return !this.defaultLaw.email_only
      }
      return true
    },
    isAllowedAddress() {
      if (!this.address || !this.config.settings.address_regex) {
        return true
      }
      return new RegExp(this.config.settings.address_regex).test(this.address)
    },
    ...mapGetters([
      'addressValid',
      'addressChanged',
    ])
  }
}
</script>