<template>
  <div>
    <div class="card mb-3">
      <div class="card-body">
        <div class="row">
          <div class="col-md-8">
            <div class="mb-3 row">
              <div
                class="col-sm-6"
                :class="{ 'text-danger': usererrors.first_name }">
                <label
                  class="form-label field-required"
                  for="id_first_name"
                  :class="{ 'text-danger': usererrors.first_name }">
                  {{ i18n.yourFirstName }}
                </label>
                <input
                  id="id_first_name"
                  v-model="first_name"
                  type="text"
                  name="first_name"
                  class="form-control"
                  :class="{ 'is-invalid': usererrors.first_name }"
                  :placeholder="userformFields.first_name.placeholder"
                  required />
                <p v-for="e in usererrors.first_name" :key="e.message">
                  {{ e.message }}
                </p>
              </div>

              <div
                class="col-sm-6"
                :class="{ 'text-danger': usererrors.last_name }">
                <label
                  class="form-label field-required"
                  for="id_last_name"
                  :class="{ 'text-danger': usererrors.last_name }">
                  {{ i18n.yourLastName }}
                </label>
                <input
                  id="id_last_name"
                  v-model="last_name"
                  type="text"
                  name="last_name"
                  class="form-control"
                  :class="{ 'is-invalid': usererrors.last_name }"
                  :placeholder="userformFields.last_name.placeholder"
                  required />
                <p v-for="e in usererrors.last_name" :key="e.message">
                  {{ e.message }}
                </p>
              </div>
            </div>
          </div>
          <div v-if="usePseudonym" class="col-md-4 mt-md-4">
            <small
              v-if="userformFields.last_name.help_text"
              v-html="userformFields.last_name.help_text" />
          </div>

        </div>
        <div v-if="!user" class="mb-3 row">
          <label
            for="id_user_email"
            class="col-sm-3 col-form-label"
            :class="{
              'text-danger': errors.user_email,
              'field-required': !user
            }">
            {{ i18n.yourEmail }}
          </label>
          <div class="col-sm-9">
            <input
              v-model="email"
              type="email"
              name="user_email"
              class="form-control"
              :class="{ 'is-invalid': errors.user_email }"
              :placeholder="formFields.user_email.placeholder"
              required />
            <p
              v-for="e in errors.user_email"
              :key="e.message"
              class="text-danger">
              {{ e.message }}
            </p>
          </div>
        </div>

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
        <template v-if="formFields.time">
          <input type="hidden" name="time" :value="formFields.time.initial" />
        </template>
        <template v-if="formFields.phone">
          <div class="mb-3 row d-none honigtopf">
            <label class="col-lg-3 col-form-label" for="id_phone">
              {{ formFields.phone.label }}
            </label>
            <div class="col-lg-9">
              <input
                id="id_phone"
                class="form-control"
                type="text"
                name="phone" />
            </div>
          </div>
        </template>
        <template v-if="formFields.test">
          <div class="mb-3 row">
            <label
              class="col-lg-3 col-form-label"
              :class="{
                'text-danger': errors.test,
                'field-required': formFields.test.required
              }"
              for="id_test">
              {{ formFields.test.label }}
            </label>
            <div class="col-lg-9">
              <input class="form-control" type="text" required name="test" />
              <p class="help-block">
                <span>{{ formFields.test.help_text }}</span>
              </p>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
import I18nMixin from '../../lib/i18n-mixin'

export default {
  name: 'UserRegistration',
  mixins: [I18nMixin],
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
    userForm: {
      type: Object
    },
    defaultLaw: {
      type: Object
    },
    initialFirstName: {
      type: String,
      default: ''
    },
    initialLastName: {
      type: String,
      default: ''
    },
    initialEmail: {
      type: String,
      default: ''
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
      emailValue: this.initialEmail,
      firstNameValue:
        this.initialFirstName || (this.user && this.user.first_name) || '',
      lastNameValue:
        this.initialLastName || (this.user && this.user.last_name) || '',
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
    userformFields() {
      return this.userForm.fields
    },
    usererrors() {
      return this.userForm.errors
    },
    first_name: {
      get() {
        return this.firstNameValue
      },
      set(value) {
        this.firstNameValue = value
        this.$emit('update:initialFirstName', value)
      }
    },
    last_name: {
      get() {
        return this.lastNameValue
      },
      set(value) {
        this.lastNameValue = value
        this.$emit('update:initialLastName', value)
      }
    },
    addressHelpTextValue() {
      if (this.addressHelpText !== null) {
        return this.addressHelpText
      }
      return this.formFields.address.help_text
    },
    email: {
      get() {
        return this.emailValue
      },
      set(value) {
        this.emailValue = value
        this.$emit('update:initialEmail', value)
      }
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
