<template>
  <div>

    <fieldset class="active">
      <slot name="publicbody-legend-title"></slot>

      <publicbody-chooser name="public_body" :defaultsearch="publicbodyDefaultSearch"  :config="config"></publicbody-chooser>
    </fieldset>

    <fieldset v-if="publicbody" id="write-request">
      <slot name="request-legend-title"></slot>

      <div v-if="nonFieldErrors.length > 0" class="alert alert-danger">
        <p v-for="error in nonFieldErrors">{{ error }}</p>
      </div>

      <slot name="requesthints"></slot>

      <div class="form-group row">
        <label for="id_subject" class="col-sm-3 col-form-label" :class="{ 'text-danger': errors.subject }">
          {{ i18n.subject }}
        </label>
        <div class="col-sm-9">
          <input v-model="subject" type="text" name="subject" class="form-control" id="id_subject" :class="{ 'is-invalid': errors.subject }" :placeholder="form.subject.placeholder"/>
        </div>
      </div>


      <div class="row">
        <div class="col-sm-12">
          <div class="card">
            <div class="card-header body-text">Antrag nach dem IFG/UIG/VIG

  Sehr geehrte Damen und Herren,

  bitte senden Sie mir Folgendes zu:</div>
            <div class="card-body">
              <textarea v-model="body" name="body" class="form-control body-textarea" :class="{ 'is-invalid': errors.body }">
              </textarea>
            </div>
            <div class="card-footer body-text">Mit freundlichen Grüßen
<em v-if="!user.first_name && !user.last_name">Bitte Formular mit Namen ausfüllen</em>
<span v-else>{{ user.first_name }} {{ user.last_name }}</span>
            </div>
          </div>
        </div>

      </div>

      <user-registration :form-json="userFormJson" :config="config"></user-registration>

      <slot name="public"></slot>


    </fieldset>

    <similar-requests :config="config"></similar-requests>

    <button v-if="publicbody" type="submit" id="send-request-button" class="btn btn-primary">
      <span class="fa fa-check"></span>
      {{ i18n.submitRequest }}
    </button>
  </div>
</template>

<script>
import SimilarRequests from './similar-requests'
import PublicbodyChooser from './publicbody-chooser'
import UserRegistration from './user-registration'

import {mapGetters, mapMutations} from 'vuex'

import {SET_PUBLICBODY, SET_USER, UPDATE_SUBJECT, UPDATE_BODY
} from '../store/mutation_types'

export default {
  name: 'request-form',
  props: [
    'config',
    'publicbodyDefaultSearch', 'publicbodyJson',
    'userJson',
    'requestFormJson', 'userFormJson',
    'showSimilar'
  ],
  created () {
    this.updateSubject(this.form.subject.value || this.form.subject.initial)
    this.updateBody(this.form.body.value || this.form.body.initial)
    if (this.userJson) {
      this.setUser(JSON.parse(this.userJson))
    }
    if (this.publicbodyJson) {
      this.setPublicbody(JSON.parse(this.publicbodyJson))
    }
  },
  computed: {
    nonFieldErrors () {
      return this._form.nonFieldErrors
    },
    _form () {
      return JSON.parse(this.requestFormJson)
    },
    form () {
      return this._form.fields
    },
    errors () {
      return this._form.errors
    },
    i18n () {
      return this.config.i18n
    },
    subject: {
      get () {
        return this.$store.state.subject
      },
      set (value) {
        this.updateSubject(value)
      }
    },
    body: {
      get () {
        return this.$store.state.body
      },
      set (value) {
        this.updateBody(value)
      }
    },
    ...mapGetters(['user', 'publicbody'])
  },
  methods: {

    ...mapMutations({
      updateSubject: UPDATE_SUBJECT,
      updateBody: UPDATE_BODY,
      setUser: SET_USER,
      setPublicbody: SET_PUBLICBODY
    })
  },
  components: {PublicbodyChooser, UserRegistration, SimilarRequests}
}
</script>

<style>

.body-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  color: #999;
}

.body-textarea {
  width: 100%;
}


</style>
