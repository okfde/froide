<template>
  <div>
    <fieldset v-if="stepSelectPublicbody" class="active">
      <div class="row">
        <div class="col-lg-7">
          <slot name="publicbody-legend-title"></slot>
          <slot name="publicbody-help-text"></slot>
        </div>
      </div>
      <div class="row">
        <div class="col-lg-8">
          <publicbody-chooser name="publicbody"
            :defaultsearch="publicbodyDefaultSearch"
            :scope="pbScope"
            :form-json="publicbodyFormJson"
            :config="config">
          </publicbody-chooser>
        </div>
        <div class="col-lg-4 small">
          <slot name="publicbody-missing"></slot>
        </div>
      </div>
    </fieldset>

    <fieldset v-if="stepReviewReady" id="write-request">
      <div class="row">
        <div class="col-lg-8">
          <div>{{ publicbody.name }}</div>
        </div>
      </div>

      <div class="row " v-if="defaultLaw.request_note">
        <div class="col-lg-8">
          <div class="alert alert-warning" v-html="defaultLaw.request_note_html">
          </div>
        </div>
      </div>

      <div class="row">
        <div class="col-md-8">
          <slot name="request-legend-title"></slot>

          <div v-if="nonFieldErrors.length > 0" class="alert alert-danger">
            <p v-for="error in nonFieldErrors">{{ error }}</p>
          </div>

          <div class="form-group row">
            <label for="id_subject" class="col-sm-3 col-form-label" :class="{ 'text-danger': errors.subject }">
              {{ i18n.subject }}
            </label>
            <div class="col-sm-9">
              <input v-model="subject" type="text" name="subject" class="form-control" id="id_subject" :class="{ 'is-invalid': errors.subject }" :placeholder="form.subject.placeholder"/>
            </div>
          </div>
        </div>
      </div>

      <div class="card mb-3">
        <div class="card-body">
          <div class="row">
            <div class="col-md-8">
              <div class="body-text"><span v-if="defaultLaw">{{ defaultLaw.letter_start }}</span><span v-else>{{ i18n.greeting }}</span></div>
              <textarea v-model="body" name="body" class="form-control body-textarea" :class="{ 'is-invalid': errors.body }" rows="3" @keyup="bodyChanged">
              </textarea>
              <div class="body-text">{{ i18n.kindRegards }}
<em v-if="!user.id && !user.first_name && !user.last_name">{{ i18n.giveName }}</em>
<span v-else>{{ user.first_name }} {{ user.last_name }}</span>
              </div>
            </div>
            <div class="col-md-4 small">
              <slot name="requesthints"></slot>
            </div>
          </div>
          <div class="row">
            <div class="col-md-8">
              <div class="form-group row" v-if="!user.id">
                <div class="col" :class="{ 'text-danger': errors.first_name }">
                  <label class="control-label" for="id_first_name" :class="{ 'text-danger': errors.first_name }">
                    {{ i18n.yourFirstName }}
                  </label>
                  <input v-model="first_name" type="text" name="first_name" class="form-control" :class="{ 'is-invalid': errors.first_name }" id="id_first_name" :placeholder="userform.first_name.placeholder"/>
                  <p v-for="e in errors.first_name">{{ e.message }}</p>
                </div>
                <div class="col" :class="{ 'text-danger': errors.last_name }">
                  <label class="control-label" for="id_last_name" :class="{ 'text-danger': errors.last_name }">
                    {{ i18n.yourFirstName }}
                  </label>
                  <input v-model="last_name" type="text" name="last_name" class="form-control" :class="{ 'is-invalid': errors.last_name }" id="id_last_name" :placeholder="userform.last_name.placeholder"/>
                  <p v-for="e in errors.last_name">{{ e.message }}</p>
                </div>
              </div>
            </div>
            <div class="col-md-4 mt-4"  v-if="!user.id">
              <small v-if="userform.last_name.help_text" v-html="userform.last_name.help_text"></small>
            </div>
          </div>
        </div>
      </div>


      <user-registration v-if="!user.id" :form-json="userFormJson" :config="config"></user-registration>

      <div class="row">
        <div class="col-md-8">

          <slot name="public"></slot>

          <slot name="terms"></slot>
        </div>
      </div>

    </fieldset>

    <div class="row">
      <div class="col-md-8">
        <similar-requests v-if="showSimilar" :pbScope="pbScope" :config="config"></similar-requests>
      </div>
    </div>

    <review-request v-if="stepReviewReady" :pbScope="pbScope" :i18n="i18n"></review-request>

    <button v-if="stepReviewReady" type="button" id="review-button" class="btn btn-primary" data-toggle="modal" data-target="#step-review">
      <i class="fa fa-check" aria-hidden="true"></i>
      {{ i18n.reviewRequest }}
    </button>
    <button v-if="reviewReady && user.id" type="submit" class="btn btn-secondary" name="save_draft" value="true">
      <i class="fa fa-save" aria-hidden="true"></i>
      {{ i18n.saveAsDraft }}
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
  SET_PUBLICBODY, SET_PUBLICBODIES, CACHE_PUBLICBODIES,
  UPDATE_FIRST_NAME, UPDATE_LAST_NAME,
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
  data () {
    return {
      bodyRows: 3
    }
  },
  created () {
    this.pbScope = 'make-request'
    this.updateSubject(this.form.subject.value || this.form.subject.initial)
    this.updateBody(this.form.body.value || this.form.body.initial)
    if (this.userJson) {
      this.setUser(JSON.parse(this.userJson))
    }
    if (this.publicbodiesJson) {
      let pbs = JSON.parse(this.publicbodiesJson)
      this.setPublicbodies({
        publicbodies: pbs,
        scope: this.pbScope
      })
      this.cachePublicBodies(pbs)
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
    _userform () {
      return JSON.parse(this.userFormJson)
    },
    userform () {
      return this._userform.fields
    },
    usererrors () {
      return this._userform.errors
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
    publicbody () {
      return this.getPublicBodyByScope(this.pbScope)
    },
    ...mapGetters([
      'user',
      'getPublicBodyByScope',
      'defaultLaw',
      'stepReviewReady',
      'stepSelectPublicbody'
    ])
  },
  methods: {
    bodyChanged (e) {
      var ta = document.querySelector('[name=body]')
      var maxrows = 10
      while (ta.scrollHeight > ta.clientHeight && ta.rows < maxrows) {
        ta.style.overflow = 'hidden'
        ta.rows += 1
      }
      if (ta.scrollHeight > ta.clientHeight) {
        ta.style.overflow = 'auto'
      }
    },
    ...mapMutations({
      updateSubject: UPDATE_SUBJECT,
      updateBody: UPDATE_BODY,
      setUser: SET_USER,
      updateFirstName: UPDATE_FIRST_NAME,
      updateLastName: UPDATE_LAST_NAME,
      setPublicbody: SET_PUBLICBODY,
      setPublicbodies: SET_PUBLICBODIES,
      cachePublicBodies: CACHE_PUBLICBODIES
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

.body-textarea {
  background-color: #fff;
  outline: none;
  border-radius: 0px;
  padding-left: 0;
  border: 0px;
  border-left: 3px solid blue;
  margin-left: -5px;
  padding: 5px;
}


</style>
