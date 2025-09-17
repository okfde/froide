<template>
  <div>
    <div class="card mb-3">
      <div class="card-body">
        <div v-if="!user" class="row">
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

        <!--
          TODO: does not work a.t.m. without changes
            1. change MakeRequestView.get_user_form
              form_klass = NewUserForm → NewUserWithPasswordForm
            2. account.forms.NewUserWithPasswordForm.clean
              super().clean() returns None
              should compare self.data["passwordN"] ?
                and return self.cleaned_data ?
            3. on form errors, password fields remain empty, have to be re-filled
            4. /account/confirmed/ has a set password prompt

        <template v-if="formFields.password">
          <div class="mb-3 row">
            <label
              for="id_password"
              class="col-sm-3 col-form-label"
              >
              {{ i18n.password }}
            </label>
            <div
              class="col-sm-9"
              >
              <input
                name="password"
                type="password"
                class="form-control"
                />
            </div>
          </div>
          <div class="mb-3 row">
            <label
              for="id_password2"
              class="col-sm-3 col-form-label"
              >
              {{ i18n.passwordRepeated }}
            </label>
            <div
              class="col-sm-9"
              >
              <input
                name="password2"
                type="password"
                class="form-control"
                />
            </div>
          </div>
        </template>
      -->

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
  },
  data() {
    return {
      emailValue: this.initialEmail,
      firstNameValue:
        this.initialFirstName || (this.user && this.user.first_name) || '',
      lastNameValue:
        this.initialLastName || (this.user && this.user.last_name) || '',
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
    email: {
      get() {
        return this.emailValue
      },
      set(value) {
        this.emailValue = value
        this.$emit('update:initialEmail', value)
      }
    },
  }
}
</script>
