<template>
  <div class="make-request-container">
    <request-form-breadcrumbs
      :i18n="i18n"
      :multiRequest="multiRequest"
      :hasPublicBodies="hasPublicBodies"
      :hidePublicbodyChooser="hidePublicbodyChooser"></request-form-breadcrumbs>

    <div :class="{container: !multiRequest, 'container-multi': multiRequest}">

      <slot name="messages"></slot>

      <div class="row justify-content-lg-center">
        <div class="col-lg-12">

          <fieldset v-if="stepSelectPublicBody" id="step-publicbody" class="mt-5">
            <div v-if="multiRequest">
              <publicbody-multi-chooser
                name="publicbody"
                :defaultsearch="publicBodySearch"
                :scope="pbScope"
                :config="config">
                <template slot="publicbody-missing">
                  <slot name="publicbody-missing"></slot>
                </template>
              </publicbody-multi-chooser>
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

          <fieldset v-if="stepReviewPublicBodies && !stepWriteRequest" id="step-review-publicbody" class="mt-5">
            <pb-multi-review
              name="publicbody"
              :i18n="i18n"
              :scope="pbScope"
            >
            </pb-multi-review>
          </fieldset>

          <fieldset v-if="stepWriteRequest" id="step-request" class="mt-3">

            <request-form
              :config="config"
              :publicbodies="publicBodies"
              :user="user.id ? user : null"
              :request-form="requestForm"
              :user-form="userForm"
              :hide-publicbody-chooser="hidePublicbodyChooser"
              :hide-full-text="hideFullText"
              :hide-editing="hideEditing"
              :multi-request="multiRequest"
              :default-law="defaultLaw"
              :law-type="lawType"
              :initial-subject.sync="subject"
              :initial-body.sync="body"
              :initial-full-text.sync="fullText"
              :initial-first-name.sync="firstName"
              :initial-last-name.sync="lastName"
              @setStepSelectPublicBody="setStepSelectPublicBody"
            >
              <template slot="request-hints">
                <slot name="request-hints"></slot>
              </template>
              <template slot="request-legend-title">
                <slot name="request-legend-title"></slot>
              </template>
            </request-form>

            <user-registration
              :form="userForm"
              :config="config"
              :user="user.id ? user : null"
              :default-law="defaultLaw"
              :initial-email.sync="email"
              :initial-address.sync="address"
              :initial-private.sync="userPrivate"
            ></user-registration>

            <request-public
              :form="requestForm"
              :hide-public="hidePublic"
            ></request-public>

            <user-terms v-if="!user.id"
              :form="userForm"
            ></user-terms>

          </fieldset>

          <similar-requests v-if="showSimilar && stepWriteRequest"
            :publicbodies="publicBodies"
            :subject="subject"
            :config="config"
          ></similar-requests>

          <review-request
            v-if="stepWriteRequest"
            :i18n="i18n"
            :publicbodies="publicBodies"
            :user="user"
            :defaultLaw="defaultLaw"
            :subject="subject"
            :body="body"
            :fullText="fullText"
          ></review-request>

          <button v-if="stepWriteRequest && shouldCheckRequest" type="button" id="review-button" class="btn btn-primary" data-toggle="modal" data-target="#step-review">
            <i class="fa fa-check" aria-hidden="true"></i>
            {{ i18n.reviewRequest }}
          </button>
          <button v-else-if="stepWriteRequest" type="submit" id="send-request-button" class="btn btn-primary">
            <i class="fa fa-send" aria-hidden="true"></i>
            {{ i18n.submitRequest }}
          </button>
          <button v-if="stepWriteRequest && user.id && showDraft" type="submit" class="btn btn-secondary" name="save_draft" value="true">
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
import PublicbodyChooser from './publicbody/publicbody-chooser'
import PublicbodyMultiChooser from './publicbody/publicbody-multichooser'
import UserRegistration from './user-registration'
import ReviewRequest from './review-request'
import PbMultiReview from './publicbody/pb-multi-review'
import RequestForm from './request-form'
import RequestFormBreadcrumbs from './request-form-breadcrumbs'
import RequestPublic from './request-public'
import UserTerms from './user-terms'


import {mapGetters, mapMutations, mapActions} from 'vuex'

import {
  STEPS, STEP_TO_URLS, SET_STEP_BY_URL,
  SET_STEP_SELECT_PUBLICBODY, SET_STEP_REVIEW_PUBLICBODY, SET_STEP_REQUEST,
  SET_PUBLICBODY, SET_PUBLICBODIES, CACHE_PUBLICBODIES,
  UPDATE_FIRST_NAME, UPDATE_LAST_NAME,
  SET_USER, UPDATE_SUBJECT, UPDATE_BODY, UPDATE_FULL_TEXT,
  UPDATE_ADDRESS, UPDATE_EMAIL, UPDATE_PRIVATE,
  UPDATE_LAW_TYPE, SET_CONFIG
} from '../store/mutation_types'

import LetterMixin from '../lib/letter-mixin'
import I18nMixin from '../lib/i18n-mixin'

export default {
  name: 'request-page',
  props: {
    config: {
      type: Object
    },
    publicbodyDefaultSearch: {
        type: String
    },
    publicbodyForm: {
      type: Object,
      default: null
    },
    publicbodies: {
      type: Array,
      default: null
    },
    userInfo: {
      type: Object,
      default: null
    },
    requestForm: {
      type: Object
    },
    userForm: {
      type: Object,
    },
    showSimilar: {
      type: Boolean,
      default: false
    },
    showDraft: {
      type: Boolean,
      default: false
    },
    hidePublicbodyChooser: {
      type: Boolean,
      default: false
    },
    hideFullText: {
      type: Boolean,
      default: false
    },
    hideEditing: {
      type: Boolean,
      default: false
    },
    hidePublic: {
      type: Boolean,
      default: false
    },
    multiRequest: {
      type: Boolean,
      default: false
    }
  },
  components: {
    PublicbodyChooser,
    PublicbodyMultiChooser,
    UserRegistration,
    SimilarRequests,
    ReviewRequest,
    PbMultiReview,
    RequestForm,
    RequestFormBreadcrumbs,
    RequestPublic,
    UserTerms
  },
  mixins: [I18nMixin, LetterMixin],
  data () {
    return {
      fullTextDisabled: false,
      editingDisabled: this.hideEditing,
      fullLetter: false
    }
  },
  created () {
    this.pbScope = 'make-request'
    this.setConfig(this.config)

    this.initStoreValues(this.formFields, {
      subject: this.updateSubject,
      body: this.updateBody,
      full_text: this.updateFullText,
      law_type: this.updateLawType,
    })


    this.updateLawType(this.formFields.law_type.value || this.formFields.law_type.initial)
    if (this.publicbodies !== null) {
      let pbs = this.publicbodies
      this.setPublicBodies({
        publicBodies: pbs,
        scope: this.pbScope
      })
      this.cachePublicBodies(pbs)
      this.getLawsForPublicBodies(pbs)
    }
    if (this.userInfo !== null) {
      this.setUser(this.userInfo)
      this.initStoreValues(this.userformFields, {
        address: this.updateAddress,
      })
    } else {
      this.initStoreValues(this.userformFields, {
        user_email: this.updateEmail,
        first_name: this.updateFirstName,
        last_name: this.updateLastName,
        address: this.updateAddress,
        private: this.updatePrivate,
      })
    }
  },
  mounted () {
    let step = STEPS.SELECT_PUBLICBODY
    if (this.hasPublicBodies) {
      this.setStepRequest()
      step = STEPS.WRITE_REQUEST
    }
  },
  computed: {
    form () {
      return this.requestForm
    },
    formFields () {
      return this.form.fields
    },
    userformFields () {
      return this.userForm.fields
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
    subjectWasChanged () {
      return this.subject !== this.formFields.subject.initial
    },
    hasBody () {
      return this.body && this.body.length > 0
    },
    bodyWasChanged () {
      return this.body !== this.formFields.body.initial
    },
    body: {
      get () {
        return this.$store.state.body
      },
      set (value) {
        this.updateBody(value)
      }
    },
    multipleLaws () {
      return this.defaultLaw === null
    },
    fullText: {
      get () {
        return this.$store.state.fullText
      },
      set (value) {
        this.updateFullText(value)
      }
    },
    firstName: {
      get () {
        return this.$store.state.user.first_name
      },
      set (value) {
        this.updateFirstName(value)
      }
    },
    lastName: {
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
    hasPublicBodies () {
      return this.publicBodies.length > 0
    },
    publicBody () {
      return this.getPublicBodyByScope(this.pbScope)
    },
    publicBodies () {
      return this.getPublicBodiesByScope(this.pbScope)
    },
    shouldCheckRequest () {
      return (this.body === '' || this.bodyWasChanged) || (this.subject === '' || this.subjectWasChanged)
    },
    ...mapGetters([
      'user',
      'getPublicBodyByScope',
      'getPublicBodiesByScope',
      'stepWriteRequest',
      'stepReviewPublicBodies',
      'stepSelectPublicBody',
      'step',
      'lawType',
      'defaultLaw'
    ])
  },
  methods: {
    initStoreValues (fields, mapping) {
      for (let key in mapping) {
        let method = mapping[key]
        if (fields[key] === undefined) { continue }
        method(
          fields[key].value || fields[key].initial
        )
      }
    },
    ...mapMutations({
      setStepSelectPublicBody: SET_STEP_SELECT_PUBLICBODY,
      setStepRequest: SET_STEP_REQUEST,
      updateSubject: UPDATE_SUBJECT,
      updateBody: UPDATE_BODY,
      updateFullText: UPDATE_FULL_TEXT,
      setConfig: SET_CONFIG,
      setUser: SET_USER,
      updateFirstName: UPDATE_FIRST_NAME,
      updateLastName: UPDATE_LAST_NAME,
      updateLawType: UPDATE_LAW_TYPE,
      setPublicBody: SET_PUBLICBODY,
      setPublicBodies: SET_PUBLICBODIES,
      cachePublicBodies: CACHE_PUBLICBODIES,
      updateFirstName: UPDATE_FIRST_NAME,
      updateLastName: UPDATE_LAST_NAME,
      updateAddress: UPDATE_ADDRESS,
      updateEmail: UPDATE_EMAIL,
      updatePrivate: UPDATE_PRIVATE,
    }),
    ...mapActions([
      'getLawsForPublicBodies'
    ])
  },
  watch: {
    step (newStep, oldStep) {
      window.scrollTo(0, 0)
    }
  }
}
</script>

<style lang="scss" scoped>

@import "../../styles/variables";

.make-request-container {
  padding-bottom: 1rem;
}

.container-multi {
  /* Allow container to wider than normal to allow for more space */
  width: 100%;
  padding-right: 15px;
  padding-left: 15px;
  margin-right: auto;
  margin-left: auto;
  max-width: 1400px;
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

.saved-body {
  width: 100%;
  height: 5em;
}

.saved-full-text-enter-active, .saved-full-text-leave-active {
  transition: opacity .5s;
}
.saved-full-text-enter, .saved-full-text-leave-to {
  opacity: 0;
}

.show-full-letter {
  color: #999;
  text-decoration: underline;
}

</style>
