<template>
  <div>
    <div class="row mb-3">
      <!-- FIXME? the linter complained about vue/no-duplicate-attributes re class + :class,
       which should have allowCoexistClass:true by default.
       Adding that explicitly to eslint.config didn't help,
       eslint-disable for this file didn't either. -->
      <label
        class="form-label field-required"
        for="id_first_name"
        :class="[
          { 'text-danger': userformErrors.first_name },
          'col-sm-4', 'col-md-3', 'col-form-label'
        ]"
        >{{ i18n.yourFirstName }}
      </label>
      <div class="col-sm-8 col-md-5">
        <input
          id="id_first_name"
          v-model="first_name"
          ref="first_name"
          type="text"
          name="first_name"
          class="form-control"
          :class="{ 'is-invalid': userformErrors.first_name && !updateFirstNameChanged }"
          :placeholder="userformFields.first_name.placeholder"
          required
          :maxlength="userformFields.first_name.max_length"
          @change="updateFirstNameChanged(true)"
          />
        <p
          v-for="e in userformErrors.first_name"
          :key="e.message"
          class="text-danger"
          >{{ e.message }}
        </p>
      </div>
    </div>
    <div class="row mb-3">
      <label
        class="form-label field-required"
        for="id_last_name"
        :class="[
          { 'text-danger': userformErrors.last_name },
          'col-sm-4', 'col-md-3', 'col-form-label'
        ]"
        >{{ i18n.yourLastName }}
      </label>
      <div class="col-sm-8 col-md-5">
        <input
          id="id_last_name"
          v-model="last_name"
          ref="last_name"
          type="text"
          name="last_name"
          class="form-control"
          :class="{ 'is-invalid': userformErrors.last_name && !lastNameChanged }"
          :placeholder="userformFields.last_name.placeholder"
          required
          :maxlength="userformFields.last_name.max_length"
          @change="updateLastNameChanged(true)"
          />
        <div v-if="usePseudonym">
          <small
            v-if="userformFields.last_name.help_text"
            v-html="userformFields.last_name.help_text" />
        </div>
        <p v-for="e in userformErrors.last_name" :key="e.message">
          {{ e.message }}
        </p>
      </div>
    </div>
    <div class="mb-3 row">
      <label
        for="id_user_email"
        class="col-sm-4 col-md-3 col-form-label"
        :class="{
          'text-danger': userformErrors.user_email,
          'field-required': !user
        }">
        {{ i18n.yourEmail }}
      </label>
      <div class="col-sm-8 col-md-5">
        <input
          v-model="email"
          ref="email"
          type="email"
          name="user_email"
          class="form-control"
          :class="{ 'is-invalid': userformErrors.user_email && !emailChanged }"
          :placeholder="userformFields.user_email.placeholder"
          required
          :maxlength="userformFields.user_email.max_length"
          @change="updateEmailChanged(true)"
          />
        <p
          v-for="e in userformErrors.user_email"
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

  </div>
</template>

<script>
import I18nMixin from '../../lib/i18n-mixin'

import { mapGetters, mapMutations } from 'vuex'

import {
  UPDATE_FIRST_NAME_VALIDITY,
  UPDATE_FIRST_NAME_CHANGED,
  UPDATE_LAST_NAME_VALIDITY,
  UPDATE_LAST_NAME_CHANGED,
  UPDATE_EMAIL_VALIDITY,
  UPDATE_EMAIL_CHANGED,
} from '../../store/mutation_types'

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
    usePseudonym: {
      type: Boolean,
      default: false
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
    userformFields() {
      return this.userForm.fields
    },
    userformErrors() {
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
    ...mapGetters([
      'firstNameChanged',
      'lastNameChanged',
      'emailChanged',
    ]),
  },
  methods: {
    validateAll() {
      // validate in "reverse document order" since the last (negative) report triggers popup and lingers
      // note that we're impurely committing side-effectful reportValidity (instead of checkValidity)
      this.updateEmailValidity(
        this.$refs.email.reportValidity()
      )
      this.updateLastNameValidity(
        this.$refs.last_name.reportValidity()
      )
      this.updateFirstNameValidity(
        this.$refs.first_name.reportValidity()
      )
    },
    ...mapMutations({
      updateFirstNameValidity: UPDATE_FIRST_NAME_VALIDITY,
      updateFirstNameChanged: UPDATE_FIRST_NAME_CHANGED,
      updateLastNameValidity: UPDATE_LAST_NAME_VALIDITY,
      updateLastNameChanged: UPDATE_LAST_NAME_CHANGED,
      updateEmailValidity: UPDATE_EMAIL_VALIDITY,
      updateEmailChanged: UPDATE_EMAIL_CHANGED,
    })
  }
}
</script>
