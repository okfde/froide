<template>
  <div>
    <div class="card mb-3">
      <div class="card-body">
        <div class="form-group row">
          <label for="id_user_email" class="col-sm-3 col-form-label" :class="{ 'text-danger': errors.user_email, 'field-required': !user }">
            {{ i18n.yourEmail }}
          </label>
          <div class="col-sm-9">
            <p v-if="user" id="email_address" class="form-control-plaintext">
              {{ user.email }}
            </p>
            <div v-else>
              <input v-model="email" type="email" name="user_email" class="form-control" :class="{ 'is-invalid': errors.user_email }" :placeholder="formFields.user_email.placeholder" required/>
              <p v-for="e in errors.user_email" :key="e.message" class="text-danger">{{ e.message }}</p>
            </div>
          </div>
        </div>

        <div class="form-group row">
          <label for="id_address" class="col-sm-3 col-form-label" :class="{ 'text-danger': errors.address, 'field-required': requiresPostalAddress}">
            {{ i18n.yourAddress }}
          </label>
          <div class="col-sm-9">
            <div>
              <textarea v-model="address" name="address" class="form-control" :class="{ 'is-invalid': errors.address }" :placeholder="formFields.address.placeholder" :required="requiresPostalAddress"></textarea>
              <p v-for="e in errors.address" :key="e.message">{{ e.message }}</p>
              <p class="help-block">{{ addressHelpText }}</p>
            </div>
          </div>
        </div>

        <div v-if="config.settings.user_can_hide_web && !user">
          <div class="row">
            <div class="col-md-8">
              <div class="checkbox">
                <label>
                  <input id="id_private" v-model="userPrivate" type="checkbox" name="private" />
                  {{ formFields.private.label }}
                </label>
                <br/>
                <p class="help-block" v-html="formFields.private.help_text">
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>

import I18nMixin from '../../lib/i18n-mixin'

export default {
  name: 'user-registration',
  props: {
    config: {
      type: Object
    },
    form: {
      type: Object
    },
    user: {
      type: Object,
      default: null
    },
    defaultLaw: {
      type: Object
    },
    initialEmail: {
      type: String,
      default: '',
    },
    initialAddress: {
      type: String,
      default: '',
    },
    initialPrivate: {
      type: Boolean,
      default: false
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
  mixins: [I18nMixin],
  data () {
    return {
      emailValue: this.initialEmail,
      addressValue: this.initialAddress,
      privateValue: this.initialPrivate
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
    addressHelpTextValue () {
      if (this.addressHelpText !== null) {
        return this.addressHelpText
      }
      return formFields.address.help_text
    },
    email: {
      get () {
        return this.emailValue
      },
      set (value) {
        this.emailValue = value
        this.$emit('update:initialEmail', value)
      }
    },
    address: {
      get () {
        return this.addressValue
      },
      set (value) {
        this.addressValue = value
        this.$emit('update:initialAddress', value)
      }
    },
    userPrivate: {
      get () {
        return this.privateValue
      },
      set (value) {
        this.privateValue = value
        this.$emit('update:initialPrivate', value)
      }
    },
    requiresPostalAddress () {
      if (this.addressRequired) {
        return true
      }
      if (this.defaultLaw) {
        return !this.defaultLaw.email_only
      }
      return true
    }
  }
}
</script>
