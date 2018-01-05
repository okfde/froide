<template>
  <div>
    <div class="process-breadcrumbs-container">
      <div class="container">
        <div class="row">
          <ol class="process-breadcrumbs col-md-8">
            <li :class="{ 'active': stepSelectPublicBody, 'done': stepReviewReady}">
              <a href="#step-publicbody" @click="setStepPublicBody" v-if="!hidePublicbodyChooser">
                <i class="fa fa-check-circle" aria-hidden="true"></i>
                Behörde wählen
              </a>
              <span v-else>
                <i class="fa fa-check-circle" aria-hidden="true"></i>
                Behörde wählen
              </span>
            </li>
            <li :class="{ 'active': stepReviewReady}">
              <a href="#step-request"  @click="setStepRequest" v-if="stepReviewReady">
                <i class="fa" :class="{ 'fa-check-circle': stepReviewReady, 'fa-check-circle-o': !stepReviewReady }" aria-hidden="true"></i>
                Anfrage stellen
              </a>
              <span v-else>
                <i class="fa" :class="{ 'fa-check-circle': stepReviewReady, 'fa-check-circle-o': !stepReviewReady }" aria-hidden="true"></i>
                Anfrage stellen
              </span>
            </li>
            <li>
              <a href="#step-review" data-toggle="modal" v-if="stepReviewReady">
                <i class="fa fa-check-circle-o" aria-hidden="true"></i>
                Prüfen
              </a>
              <span v-else>
                <i class="fa fa-check-circle-o" aria-hidden="true"></i>
                Prüfen
              </span>
            </li>
          </ol>
        </div>
      </div>
    </div>

    <div class="container">

      <slot name="messages"></slot>

      <div class="row justify-content-lg-center">
        <div class="col-lg-12">

          <fieldset v-if="stepSelectPublicBody" id="step-publicbody" class="mt-5">
            <div v-if="multiRequest">
              <publicbody-multi-chooser
                name="publicbody"
                :defaultsearch="publicBodySearch"
                :scope="pbScope"
                :config="config"></publicbody-multi-chooser>
            </div>
            <div v-else>
              <div class="row">
                <div class="col-lg-7">
                  <slot name="publicbody-legend-title"></slot>
                  <slot name="publicbody-help-text"></slot>
                </div>
              </div>
              <div class="row">
                <div class="col-lg-8">
                  <publicbody-chooser
                    name="publicbody"
                    :defaultsearch="publicBodySearch"
                    :scope="pbScope"
                    :config="config"
                    :list-view="publicBodyListView"></publicbody-chooser>
                </div>
                <div class="col-lg-4 small">
                  <slot name="publicbody-missing"></slot>
                </div>
              </div>
            </div>
          </fieldset>

          <fieldset v-if="stepReviewReady" id="step-request" class="mt-3">

            <slot name="request-legend-title"></slot>

            <div v-if="multiRequest" class="publicbody-summary-container">
              <div class="publicbody-summary">
                <p>
                  {{ i18n._('toMultiPublicBodies', {count: publicBodies.length}) }}

                  <span v-if="!hidePublicbodyChooser">
                    <a class="pb-change-link badge badge-pill badge-primary ml-3" href="#step-publicbody" @click="setStepPublicBody">
                      {{ i18n.change }}
                    </a>
                  </span>
                </p>
              </div>
            </div>
            <div v-else class="publicbody-summary-container">
              <div class="row">
                <div class="col-lg-8 publicbody-summary">
                  <p>
                    {{ i18n._('toPublicBody', {name: publicBody.name}) }}
                    <span v-if="!hidePublicbodyChooser">
                      <a class="pb-change-link badge badge-pill badge-primary ml-3" href="#step-publicbody" @click="setStepPublicBody">
                        {{ i18n.change }}
                      </a>
                    </span>
                  </p>
                </div>
              </div>
              <div class="row" v-if="hasNotes">
                <div class="col-lg-8">
                  <div class="alert alert-warning" v-html="requestNotes">
                  </div>
                </div>
              </div>
            </div>

            <input v-for="pb in publicBodies" type="hidden" name="publicbody" :value="pb.id">

            <div class="row">
              <div class="col-md-8">

                <div v-if="nonFieldErrors.length > 0" class="alert alert-danger">
                  <p v-for="error in nonFieldErrors">{{ error }}</p>
                </div>

                <div class="form-group">
                  <label for="id_subject" :class="{ 'text-danger': errors.subject }">
                    {{ i18n.subject }}
                  </label>
                  <input v-model="subject" type="text" name="subject" class="form-control" id="id_subject" :class="{ 'is-invalid': errors.subject }" :placeholder="form.subject.placeholder" @keydown.enter.prevent=""/>
                </div>
              </div>
            </div>

            <label for="id_subject" :class="{ 'text-danger': errors.subject }">
              {{ i18n.subject }}
            </label>

            <div class="card mb-3">
              <div class="card-body">
                <div class="row">
                  <div class="col-md-4 order-md-2">
                    <slot name="requesthints"></slot>
                  </div>
                  <div class="col-md-8 order-1">
                    <div v-if="!fullText" class="body-text">{{ letterStart }}</div>
                    <textarea v-model="body" name="body" id="id_body" class="form-control body-textarea" :class="{ 'is-invalid': errors.body, 'attention': !hasBody }" :rows="bodyRows" @keyup="bodyChanged" :placeholder="form.body.placeholder">
                    </textarea>
                    <label v-if="allowFullText" class="small pull-right text-muted">
                      <input type="checkbox" id="full_text_checkbox" name="full_text_checkbox" v-model="fullText" :disabled="fullTextDisabled">
                      {{ form.full_text.label }}
                      <input type="hidden" name="full_text" v-model="fullText">
                    </label>
                    <div v-if="!fullText" class="body-text">{{ letterEndShort }}</div>
                    <div v-if="letterSignature" class="body-text"><em>{{ letterSignature }}</em></div>
                    <div v-if="!letterSignature && fullText" class="body-text">{{ letterSignatureName }}</div>
                  </div>
                </div>
                <div class="row">
                  <div class="col-md-8">
                    <div class="form-group row" v-if="!user.id">
                      <div class="col" :class="{ 'text-danger': usererrors.first_name }">
                        <label class="control-label" for="id_first_name" :class="{ 'text-danger': usererrors.first_name }">
                          {{ i18n.yourFirstName }}
                        </label>
                        <input v-model="first_name" type="text" name="first_name" class="form-control" :class="{ 'is-invalid': usererrors.first_name }" id="id_first_name" :placeholder="userform.first_name.placeholder"/>
                        <p v-for="e in usererrors.first_name">{{ e.message }}</p>
                      </div>

                      <div class="col" :class="{ 'text-danger': usererrors.last_name }">
                        <label class="control-label" for="id_last_name" :class="{ 'text-danger': usererrors.last_name }">
                          {{ i18n.yourLastName }}
                        </label>
                        <input v-model="last_name" type="text" name="last_name" class="form-control" :class="{ 'is-invalid': usererrors.last_name }" id="id_last_name" :placeholder="userform.last_name.placeholder"/>
                        <p v-for="e in usererrors.last_name">{{ e.message }}</p>
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
              <div class="col-md-12">

                <slot name="public"></slot>

                <slot name="terms"></slot>
              </div>
            </div>

          </fieldset>

          <div class="row">
            <div class="col-md-12">
              <similar-requests v-if="showSimilar && stepReviewReady" :pbScope="pbScope" :config="config"></similar-requests>
            </div>
          </div>

          <review-request v-if="stepReviewReady" :pbScope="pbScope" :i18n="i18n"></review-request>

          <button v-if="stepReviewReady" type="button" id="review-button" class="btn btn-primary" data-toggle="modal" data-target="#step-review">
            <i class="fa fa-check" aria-hidden="true"></i>
            {{ i18n.reviewRequest }}
          </button>
          <button v-if="stepReviewReady && user.id && showDraft" type="submit" class="btn btn-secondary" name="save_draft" value="true">
            <i class="fa fa-save" aria-hidden="true"></i>
            {{ i18n.saveAsDraft }}
          </button>
        </div>

      </div>
    </div>
  </div>
</template>

<script>
import SimilarRequests from './similar-requests'
import PublicbodyChooser from './publicbody-chooser'
import PublicbodyMultiChooser from './publicbody-multichooser'
import UserRegistration from './user-registration'
import ReviewRequest from './review-request'

import {mapGetters, mapMutations, mapActions} from 'vuex'

import {
  STEPS, STEP_TO_URLS, SET_STEP_BY_URL, SET_STEP_PUBLICBODY, SET_STEP_REQUEST,
  SET_PUBLICBODY, SET_PUBLICBODIES, CACHE_PUBLICBODIES,
  UPDATE_FIRST_NAME, UPDATE_LAST_NAME,
  SET_USER, UPDATE_SUBJECT, UPDATE_BODY, UPDATE_FULL_TEXT
} from '../store/mutation_types'

import LetterMixin from '../lib/letter-mixin'
import I18nMixin from '../lib/i18n-mixin'

const MAX_BODY_ROWS = 10
const MIN_BODY_ROWS = 3

export default {
  name: 'request-form',
  props: [
    'config',
    'publicbodyDefaultSearch',
    'publicbodyFormJson', // if form should be present
    'publicbodiesJson', // if public bodies are fixed
    'userJson',
    'requestFormJson', 'userFormJson',
    'showSimilar',
    'showDraft',
    'hidePublicbodyChooser',
    'hideFullText',
    'multiRequest'
  ],
  mixins: [I18nMixin, LetterMixin],
  data () {
    return {
      bodyRows: MIN_BODY_ROWS,
      originalBody: '',
      fullTextDisabled: false
    }
  },
  created () {
    this.pbScope = 'make-request'
    this.updateSubject(this.form.subject.value || this.form.subject.initial || '')
    this.updateBody(this.form.body.value || this.form.body.initial || '')
    this.updateFullText(this.form.full_text.value || this.form.full_text.initial)
    if (this.userJson) {
      this.setUser(JSON.parse(this.userJson))
    }
    if (this.publicbodiesJson) {
      let pbs = JSON.parse(this.publicbodiesJson)
      this.setPublicBodies({
        publicBodies: pbs,
        scope: this.pbScope
      })
      this.cachePublicBodies(pbs)
    }
  },
  mounted () {
    let step = STEPS.SELECT_PUBLICBODY
    if (this.hasPublicBodies) {
      this.setStepRequest()
      step = STEPS.WRITE_REQUEST
    }
    let hash = STEP_TO_URLS[step]
    window.history.pushState({step: step}, '', hash)

    window.onpopstate = (event) => {
      let hash = document.location.hash
      this.setStepByURL({hash, scope: this.pbScope})
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
    hasNotes () {
      if (this.defaultLaw) {
        return !!this.defaultLaw.request_note_html
      }
      // FIXME: find all notes of all public body default laws?
      return false
    },
    requestNotes () {
      if (this.defaultLaw) {
        return this.defaultLaw.request_note_html
      }
      return ''
    },
    publicBodySearch () {
      if (this.publicBody) {
        return this.publicBody.name
      }
      return this.publicbodyDefaultSearch
    },
    publicBodyListView () {
      if (this.multiRequest) {
        return 'multi'
      }
      return 'actionList'
    },
    subject: {
      get () {
        return this.$store.state.subject
      },
      set (value) {
        this.updateSubject(value)
      }
    },
    hasBody () {
      return this.body && this.body.length > 0
    },
    body: {
      get () {
        return this.$store.state.body
      },
      set (value) {
        this.updateBody(value)
      }
    },
    allowFullText () {
      return this.user.id && !this.hideFullText && this.defaultLaw !== null
    },
    fullText: {
      get () {
        return this.$store.state.fullText
      },
      set (value) {
        this.updateFullText(value)
        if (value) {
          this.originalBody = this.body
          this.body = `${this.letterStart}\n${this.body}\n\n${this.letterEndNoName}`
        } else {
          if (!this.fullTextDisabled) {
            this.body = this.originalBody
          }
        }
        let newLineCount = (this.body.match(/\n/g) || []).length
        this.bodyRows = Math.max(MIN_BODY_ROWS, Math.min(newLineCount, MAX_BODY_ROWS))
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
    hasPublicBodies () {
      return this.publicBodies.length > 0
    },
    publicBody () {
      return this.getPublicBodyByScope(this.pbScope)
    },
    publicBodies () {
      return this.getPublicBodiesByScope(this.pbScope)
    },
    ...mapGetters([
      'user',
      'getPublicBodyByScope',
      'getPublicBodiesByScope',
      'defaultLaw',
      'stepReviewReady',
      'stepSelectPublicBody'
    ])
  },
  methods: {
    bodyChanged (e) {
      if (this.fullText) {
        this.fullTextDisabled = true
      }
      var ta = document.querySelector('[name=body]')
      while (ta.scrollHeight > ta.clientHeight && ta.rows < MAX_BODY_ROWS) {
        ta.style.overflow = 'hidden'
        ta.rows += 1
      }
      if (ta.scrollHeight > ta.clientHeight) {
        ta.style.overflow = 'auto'
      }
      this.bodyRows = ta.rows
    },
    ...mapMutations({
      setStepPublicBody: SET_STEP_PUBLICBODY,
      setStepRequest: SET_STEP_REQUEST,
      updateSubject: UPDATE_SUBJECT,
      updateBody: UPDATE_BODY,
      updateFullText: UPDATE_FULL_TEXT,
      setUser: SET_USER,
      updateFirstName: UPDATE_FIRST_NAME,
      updateLastName: UPDATE_LAST_NAME,
      setPublicBody: SET_PUBLICBODY,
      setPublicBodies: SET_PUBLICBODIES,
      cachePublicBodies: CACHE_PUBLICBODIES
    }),
    ...mapActions({
      setStepByURL: SET_STEP_BY_URL
    })
  },
  components: {
    PublicbodyChooser,
    PublicbodyMultiChooser,
    UserRegistration,
    SimilarRequests,
    ReviewRequest
  }
}
</script>

<style lang="scss" scoped>

@import "../../styles/variables";

.process-breadcrumbs-container {
  background-color: #f5f5f5;
  // position: sticky;
  // top: 0;
  // z-index: 500;
}

.process-breadcrumbs {
  margin-bottom: 0;
  list-style-type: none;
  display: flex;
  flex-wrap: wrap;

  li {
    flex: 1;
    min-width: 150px;
    padding: 15px 0;

    & > *, *:hover {
      color: $gray-500;
      text-decoration: none;
    }
    &.active > * {
      color: $black;
      font-weight: bold;
    }
    &.done > * {
      color: $success;
    }
  }
}

legend {
  padding: 2rem 0 2rem;
  font-size: 2rem;
}

.small a {
  color: $blue;
}

.request-hints {
  color: $gray-700;
  font-size: $font-size-sm;
  ul {
    padding-left: $spacer;
  }
}

.publicbody-summary-container {
  margin: 0 0 $spacer*2;
}

.publicbody-summary {
  font-size: $font-size-lg;
}

.pb-change-link {
  font-weight: normal;
  font-size: $font-size-sm;
}

.body-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  color: #999;
}

.body-textarea {
  width: 100%;
}

.body-textarea {
  padding-left: 0;
  margin-left: -5px;
  padding: 5px;
}
.body-textarea.attention {
  border-left: 3px solid #faa;
}


</style>
