<template>
  <div class="card mb-3">
    <div class="card-body">

      <div class="form-group row">
        <label for="id_user_email" class="col-sm-3 col-form-label field-required" :class="{ 'text-danger': errors.user_email }">
          {{ i18n.yourEmail }}
        </label>
        <div class="col-sm-9">
          <p v-if="user.id" id="email_address" class="form-control">
            {{ user.email }}
          </p>
          <div v-else>
            <input v-model="email" type="email" name="user_email" class="form-control" :class="{ 'is-invalid': errors.user_email }" :placeholder="formFields.user_email.placeholder" required/>
            <p v-for="e in errors.user_email" :key="e.message" class="text-danger">{{ e.message }}</p>
            <p v-if="authRequired">
              <a id="simple-login-link" class="btn btn-success" :href="authRequiredUrl" @click.prevent="openLoginWindow">
                {{ i18n.loginWindowLink }}
              </a>
            </p>
          </div>
        </div>
      </div>

      <div class="form-group row" v-if="requiresPostalAddress">
        <label for="id_address" class="col-sm-3 col-form-label" :class="{ 'text-danger': errors.address }">
          {{ i18n.yourAddress }}
        </label>
        <div class="col-sm-9">
          <p v-if="user.id" id="email_address" class="form-control">
            {{ user.address }}
          </p>
          <div v-else>
            <textarea v-model="address" name="address" class="form-control" :class="{ 'is-invalid': errors.address }" :placeholder="formFields.address.placeholder"></textarea>
            <p v-for="e in errors.address" :key="e.message">{{ e.message }}</p>
            <p class="help-block">{{ formFields.address.help_text }}</p>
          </div>
        </div>
      </div>

      <div v-if="config.settings.user_can_hide_web">
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
</template>

<script>

import {mapGetters, mapMutations} from 'vuex'

import {
  UPDATE_FIRST_NAME, UPDATE_LAST_NAME, UPDATE_EMAIL, UPDATE_ADDRESS,
  UPDATE_PRIVATE, UPDATE_USER_ID
} from '../store/mutation_types'

import I18nMixin from '../lib/i18n-mixin'
import {FroideAPI} from '../lib/search'

export default {
  name: 'user-registration',
  props: [
    'config', 'form'
  ],
  mixins: [I18nMixin],
  created () {
    if (this.formFields.first_name.value !== null) {
      this.updateFirstName(this.formFields.first_name.value)
    }
    if (this.formFields.last_name.value !== null) {
      this.updateLastName(this.formFields.last_name.value)
    }
    if (this.formFields.user_email.value !== null) {
      this.updateEmail(this.formFields.user_email.value)
    }
    if (this.formFields.address.value !== null) {
      this.updateAddress(this.formFields.address.value)
    }
    if (this.formFields.private.value !== null) {
      this.updatePrivate(this.formFields.private.value)
    }
  },
  computed: {
    formFields () {
      return this.form.fields
    },
    errors () {
      return this.form.errors
    },
    authRequired () {
      if (this.errors && this.errors.user_email) {
        return this.errors.user_email.some(er => er.code === 'auth_required')
      }
      return false
    },
    authRequiredUrl () {
      return this.config.url.loginSimple + this.email
    },
    first_name: {
      get () {
        return this.$store.state.user.first_name
      },
      set (value) {
        this.updateFirstName(value)
      }
    },
    last_name: {
      get () {
        return this.$store.state.user.last_name
      },
      set (value) {
        this.updateLastName(value)
      }
    },
    email: {
      get () {
        return this.$store.state.user.email
      },
      set (value) {
        this.updateEmail(value)
      }
    },
    address: {
      get () {
        return this.$store.state.user.address
      },
      set (value) {
        this.updateAddress(value)
      }
    },
    userPrivate: {
      get () {
        return this.$store.state.user.private
      },
      set (value) {
        this.updatePrivate(value)
      }
    },
    requiresPostalAddress () {
      if (this.defaultLaw) {
        return !this.defaultLaw.email_only
      }
      return false
    },
    ...mapGetters([
      'user', 'defaultLaw'
    ])
  },
  methods: {
    openLoginWindow (e) {
      let url = e.target.href
      this.popup = window.open(url, 'popup', 'height=500,width=640,resizable=yes,scrollbars=yes')
      this.popup.focus()
      window.loggedInCallback = this.loggedInCallback
    },
    loggedInCallback (params) {
      let api = new FroideAPI(this.config)
      api.getUser().then((user) => {
        this.updateFirstName(user.first_name)
        this.updateLastName(user.last_name)
        this.updateAddress(user.address)
        this.updateEmail(user.email)
        this.updatePrivate(user.private)
        this.updateUserId(user.id)
      }).catch(((e) => {
        console.error('Could not get user data from API', e)
      }))

      let csrfValue = params.csrfToken
      if (csrfValue !== undefined) {
        let csrfInputs = document.querySelectorAll('input[name="csrfmiddlewaretoken"]')
        for (var i = 0; i < csrfInputs.length; i += 1) {
          csrfInputs[i].value = csrfValue
        }
      }
      if (this.popup) {
        this.popup.close()
      }
      window.loggedInCallback = undefined
    },
    ...mapMutations({
      updateFirstName: UPDATE_FIRST_NAME,
      updateLastName: UPDATE_LAST_NAME,
      updateAddress: UPDATE_ADDRESS,
      updateEmail: UPDATE_EMAIL,
      updatePrivate: UPDATE_PRIVATE,
      updateUserId: UPDATE_USER_ID
    })
  }
}
</script>
