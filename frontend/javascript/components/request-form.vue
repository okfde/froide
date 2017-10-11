<template>
  <div>

    <fieldset v-if="publicbodyFormJson" class="active">
      <slot name="publicbody-legend-title"></slot>

      <publicbody-chooser name="publicbody"
        :defaultsearch="publicbodyDefaultSearch"
        :form-json="publicbodyFormJson"
        :config="config"></publicbody-chooser>
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
          <div class="card mb-3">
            <div class="card-header body-text"><span v-if="defaultLaw">{{ defaultLaw.letter_start }}</span><span v-else>{{ i18n.greeting }}</span></div>
            <div class="card-body">
              <textarea v-model="body" name="body" class="form-control body-textarea" :class="{ 'is-invalid': errors.body }" :placeholder="form.body.placeholder">
              </textarea>
            </div>
            <div class="card-footer">
              <div class="body-text">{{ i18n.kindRegards }}
<em v-if="!user.first_name && !user.last_name">{{ i18n.giveName }}</em>
<span v-else>{{ user.first_name }} {{ user.last_name }}</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      <user-registration v-if="!user.id" :form-json="userFormJson" :config="config"></user-registration>

      <slot name="public"></slot>


    </fieldset>

    <similar-requests v-if="showSimilar" :config="config"></similar-requests>

    <review-request v-if="publicbody" :i18n="i18n"></review-request>

    <button v-if="publicbody" type="button" class="btn btn-primary" data-toggle="modal" data-target="#step-review">
      <i class="fa fa-check" aria-hidden="true"></i>
      {{ i18n.reviewRequest }}
    </button>

  </div>
</template>

<script>
import SimilarRequests from './similar-requests'
import PublicbodyChooser from './publicbody-chooser'
import UserRegistration from './user-registration'
import ReviewRequest from './review-request'

import {mapGetters, mapMutations} from 'vuex'

import {
  SET_PUBLICBODY, SET_PUBLICBODIES, SET_PUBLICBODIES_DETAIL,
  SET_USER, UPDATE_SUBJECT, UPDATE_BODY
} from '../store/mutation_types'

export default {
  name: 'request-form',
  props: [
    'config',
    'publicbodyDefaultSearch',
    'publicbodyFormJson', // if form should be present
    'publicbodiesJson', // if public bodies are fixed
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
    if (this.publicbodiesJson) {
      let pbs = JSON.parse(this.publicbodiesJson)
      this.setPublicbodies(pbs)
      this.setPublicbodiesDetail(pbs)
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
    ...mapGetters(['user', 'publicbody', 'publicbodyDetail', 'defaultLaw'])
  },
  methods: {

    ...mapMutations({
      updateSubject: UPDATE_SUBJECT,
      updateBody: UPDATE_BODY,
      setUser: SET_USER,
      setPublicbody: SET_PUBLICBODY,
      setPublicbodies: SET_PUBLICBODIES,
      setPublicbodiesDetail: SET_PUBLICBODIES_DETAIL
    })
  },
  components: {
    PublicbodyChooser,
    UserRegistration,
    SimilarRequests,
    ReviewRequest
  }
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
