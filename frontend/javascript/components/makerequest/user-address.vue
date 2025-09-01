<template>
        <div class="mb-3 row">
          <label
            for="id_address"
            class="col-sm-3 col-form-label"
            :class="{
              'text-danger': errors.address,
              'field-required': requiresPostalAddress
            }">
            {{ i18n.yourAddress }}
          </label>
          <div class="col-sm-9">
            <div>
              <textarea
                v-model="address"
                name="address"
                class="form-control"
                :class="{ 'is-invalid': errors.address }"
                :placeholder="formFields.address.placeholder"
                :required="requiresPostalAddress" />
              <div
                v-if="!isAllowedAddress"
                class="mt-3 alert alert-warning pre"
                v-html="i18n.pleaseFollowAddressFormat" />
              <p v-for="e in errors.address" :key="e.message">
                {{ e.message }}
              </p>
              <p class="help-block">
                <span v-html="addressHelpText" />
              </p>
            </div>
          </div>
        </div>
</template>

<script>
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
    initialAddress: {
      type: String,
      default: ''
    },
    addressHelpText: {
      type: String,
      default: null
    },
    addressRequired: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      addressValue:
        this.initialAddress || (this.user && this.user.address) || ''
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
    addressHelpTextValue() {
      if (this.addressHelpText !== null) {
        return this.addressHelpText
      }
      return this.formFields.address.help_text
    },
    address: {
      get() {
        return this.addressValue
      },
      set(value) {
        this.addressValue = value
        this.$emit('update:initialAddress', value)
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
    }
  }
}
</script>