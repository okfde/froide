<template>
  <div class="card mb-3">
    <div class="card-body">

      <div class="form-group row">
        <label for="id_user_email" class="col-sm-3 col-form-label" :class="{ 'text-danger': errors.user_email }">
          {{ i18n.yourEmail }}
        </label>
        <div class="col-sm-9">
          <p v-if="user.id" id="email_address" class="form-control">
            {{ user.email }}
          </p>
          <div v-else>
            <input v-model="email" type="email" name="user_email" class="form-control" :class="{ 'is-invalid': errors.user_email }" :placeholder="form.user_email.placeholder"/>
            <p v-for="e in errors.user_email" class="text-danger">{{ e.message }}</p>
            <p v-if="authRequired">
              <a id="simple-login-link" class="btn btn-success" :href="authRequiredUrl" @click.prevent="openLoginWindow">
                {{ i18n.loginWindowLink }}
              </a>
            </p>
          </div>
        </div>
      </div>

      <div class="form-group row">
        <label for="id_address" class="col-sm-3 col-form-label" :class="{ 'text-danger': errors.address }">
          {{ i18n.yourAddress }}
        </label>
        <div class="col-sm-9">
          <p v-if="user.id" id="email_address" class="form-control">
            {{ user.email }}
          </p>
          <div v-else>
            <textarea v-model="address" name="address" class="form-control" :class="{ 'is-invalid': errors.address }" :placeholder="form.address.placeholder"></textarea>
            <p v-for="e in errors.address">{{ e.message }}</p>
            <p class="help-block">{{ form.address.help_text }}</p>
          </div>
        </div>
      </div>

      <div v-if="config.settings.user_can_hide_web">
        <div class="row">
          <div class="col-md-8">
            <div class="checkbox">
              <label>
                <input id="id_private" v-model="private" type="checkbox" name="private" />
                {{ form.private.label }}
              </label>
              <br/>
              <p class="help-block" v-html="form.private.help_text">
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

export default {
  name: 'user-registration',
  props: [
    'config', 'formJson'
  ],
  mixins: [I18nMixin],
  created () {
    if (this.form.first_name.value !== null) {
      this.updateFirstName(this.form.first_name.value)
    }
    if (this.form.last_name.value !== null) {
      this.updateLastName(this.form.last_name.value)
    }
    if (this.form.user_email.value !== null) {
      this.updateEmail(this.form.user_email.value)
    }
    if (this.form.address.value !== null) {
      this.updateAddress(this.form.address.value)
    }
    if (this.form.private.value !== null) {
      this.updatePrivate(this.form.private.value)
    }
  },
  computed: {
    _form () {
      return JSON.parse(this.formJson)
    },
    form () {
      return this._form.fields
    },
    errors () {
      return this._form.errors
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
    private: {
      get () {
        return this.$store.state.user.private
      },
      set (value) {
        this.updatePrivate(value)
      }
    },
    ...mapGetters([
      'user'
    ])
  },
  methods: {
    openLoginWindow (e) {
      let url = e.target.href
      this.popup = window.open(url, 'popup', 'height=500,width=800,resizable=yes,scrollbars=yes')
      this.popup.focus()
      window.loggedInCallback = this.loggedInCallback
    },
    loggedInCallback (params) {
      this.updateFirstName(params.first_name)
      this.updateLastName(params.last_name)
      this.updateAddress(params.address)
      this.updateEmail(params.email)
      this.updatePrivate(params.private)
      this.updateUserId(params.id)

      let csrfTag = params.csrf_token
      let csrfValue = csrfTag.match(/value=.(\w+)/)[1]
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
