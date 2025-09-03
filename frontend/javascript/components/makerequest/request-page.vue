<template>
  <div class="make-request-container">
    <RequestFormBreadcrumbs
      :i18n="i18n"
      :multi-request="multiRequest"
      :has-public-bodies="hasPublicBodies"
      :hide-publicbody-chooser="hidePublicbodyChooser" />
    
    <!-- TODO:
      steps need to be same width (for progress meter to match)
      steps need to be clickable
      reflect "done" pbly = this seems to be just a > step check
    -->
    <SimpleStepper
      class="bg-body-tertiary"
      :step="progressStepCurrent"
      :steps="steps"
      >
      §step <strong>{{ this.progressStepCurrent }}/{{ this.steps.length }}</strong>:
      {{ this.steps[this.step] }}
    </SimpleStepper>

    <div :class="{ container: !multiRequest, 'container-multi': multiRequest }">
      <DjangoSlot name="messages" />

      <div class="row justify-content-lg-center">
        <div class="col-lg-12">
          <div v-if="step === STEPS.INTRO">
            <h1>Anfrage stellen §</h1>
            <p>Was möchten Sie tun?</p>
            <div>
              campaigns
              <div class="row">
                <div class="col col-md-4 mb-4">
                  <div class="card h-100">
                    <div class="card-body d-flex flex-column">
                      <div>LOGO</div>
                      <h2 class="fs-4 my-auto">§ Eigene Anfrage schreiben</h2>
                      <div>
                        <button
                          type="button" class="btn btn-primary"
                          @click="setStep(STEPS.FIND_SIMILAR)"
                          >§Auswählen</button>
                      </div>
                    </div>
                  </div>
                </div>
                <DjangoSlot name="campaigns"></DjangoSlot>
              </div>
            </div>
          </div>
          <div v-if="step === STEPS.FIND_SIMILAR">
            <div class="mb-4">
              <label for="similarSubject" class="form-label">
                Im FragDenStaat-Archiv suchen:
              </label>
              <div class="row">
                <div class="col-sm-8">
                  <input
                    type="text"
                    class="form-control"
                    v-model="similarSubject"
                    />
                </div>
                <div class="col-sm-4">
                  <button type="button" class="btn btn-secondary w-100">
                    Suchen
                  </button>
                </div>
              </div>
            </div>
            <SimilarRequests
              :config="config"
              :publicbodies="publicBodies"
              :subject="similarSubject"
              ></SimilarRequests>
            <div>
              <button
                type="button"
                class="btn btn-primary"
                @click="setStep(STEPS.SELECT_PUBLICBODY)"
                >
                Weiter
              </button>
            </div>
          </div>
          <fieldset
            v-if="stepSelectPublicBody"
            id="step-publicbody"
            class="mt-5">
            <!-- PublicBodyChoosers advance step by mutations like SET_STEP_REQUEST (mapped to setStepRequest) -->
            <div v-if="false && multiRequest">
              <PublicbodyMultiChooser
                name="publicbody"
                :defaultsearch="publicBodySearch"
                :scope="pbScope"
                :config="config">
                <template #publicbody-missing>
                  <DjangoSlot name="publicbody-missing" />
                </template>
              </PublicbodyMultiChooser>
            </div>
            <div v-else>
              <div class="row">
                <div class="col-lg-7">
                  <DjangoSlot name="publicbody-legend-title" />
                  <DjangoSlot name="publicbody-help-text" />
                </div>
              </div>
              <div class="row">
                <div class="col-lg-8">
                  <template v-if="true || betaUi">
                    <PublicbodyBetaChooser
                      name="publicbody"
                      :defaultsearch="publicBodySearch"
                      :scope="pbScope"
                      :form="publicbodyForm"
                      :config="config" />
                  </template>
                  <template v-else>
                    <PublicbodyChooser
                      name="publicbody"
                      :defaultsearch="publicBodySearch"
                      :scope="pbScope"
                      :form="publicbodyForm"
                      :config="config"
                      :list-view="publicBodyListView" />
                  </template>
                </div>
                <div class="col-lg-4 small">
                  <DjangoSlot name="publicbody-missing" />
                </div>
              </div>
            </div>
          </fieldset>

          <fieldset
            v-if="stepReviewPublicBodies && !stepWriteRequest"
            id="step-review-publicbody"
            class="mt-5">
            <PbMultiReview name="publicbody" :i18n="i18n" :scope="pbScope" />
          </fieldset>

          <fieldset v-if="stepWriteRequest" id="step-request" class="mt-3">
            <RequestForm
              :config="config"
              :publicbodies="publicBodies"
              :user="user.id ? user : null"
              :request-form="requestForm"
              :user-form="userForm"
              :proof-form="conditionalProofForm"
              :hide-publicbody-chooser="hidePublicbodyChooser"
              :hide-full-text="hideFullText"
              :hide-editing="hideEditing"
              :multi-request="multiRequest"
              :default-law="defaultLaw"
              :law-type="lawType"
              v-model:initial-subject="subject"
              v-model:initial-body="body"
              v-model:initial-full-text="fullText"
              v-model:initial-private="userPrivate"
              :submitting="submitting"
              @set-step-select-public-body="setStepSelectPublicBody">
              <template #request-hints>
                <DjangoSlot name="request-hints" />
              </template>
              <template #request-legend-title>
                <DjangoSlot name="request-legend-title" />
              </template>
            </RequestForm>

            <UserRegistration
              :form="userForm"
              :user-form="userForm"
              :config="config"
              :user="user.id ? user : null"
              :default-law="defaultLaw"
              v-model:initial-first-name="firstName"
              v-model:initial-last-name="lastName"
              v-model:initial-email="email"
              v-model:initial-address="address"
              :address-help-text="userForm.fields.address.help_text" />

            <RequestPublic :form="requestForm" :hide-public="hidePublic" />

            <UserTerms v-if="!user.id" :form="userForm" />
          </fieldset>

          <SimilarRequests
            v-if="showSimilar && stepWriteRequest"
            :publicbodies="publicBodies"
            :subject="subject"
            :config="config" />

          <ReviewRequest
            :i18n="i18n"
            :publicbodies="publicBodies"
            :user="user"
            :default-law="defaultLaw"
            :subject="subject"
            :body="body"
            :full-text="fullText"
            ref="reviewrequest"
            @close="showReview = false"
            @submit="submitting = true" />

          <button
            v-if="stepWriteRequest && shouldCheckRequest"
            id="review-button"
            type="button"
            class="btn btn-primary btn-lg mt-3"
            @click="showReview = true">
            <i class="fa fa-check" aria-hidden="true" />
            {{ i18n.reviewRequest }}
          </button>
          <button
            v-else-if="stepWriteRequest"
            id="send-request-button"
            type="submit"
            class="btn btn-primary btn-lg mt-3"
            @click="submitting = true">
            <i class="fa fa-send" aria-hidden="true" />
            {{ i18n.submitRequest }}
          </button>
          <button
            v-if="stepWriteRequest && user.id && showDraft"
            type="submit"
            class="btn btn-secondary mt-3 ms-2"
            name="save_draft"
            value="true"
            @click="submitting = true">
            <i class="fa fa-save" aria-hidden="true" />
            {{ i18n.saveAsDraft }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import SimilarRequests from './similar-requests'
import PublicbodyChooser from '../publicbody/publicbody-chooser'
import PublicbodyBetaChooser from '../publicbody/publicbody-beta-chooser.vue'
import PublicbodyMultiChooser from '../publicbody/publicbody-multichooser'
import UserRegistration from './user-registration'
import ReviewRequest from './review-request'
import PbMultiReview from '../publicbody/pb-multi-review'
import RequestForm from './request-form'
import RequestFormBreadcrumbs from './request-form-breadcrumbs'
import RequestPublic from './request-public'
import UserTerms from './user-terms'
import DjangoSlot from '../../lib/django-slot.vue'
import SimpleStepper from '../postupload/simple-stepper.vue'

import { Modal } from 'bootstrap'

import { mapGetters, mapMutations, mapActions } from 'vuex'

import {
  SET_STEP,
  SET_STEP_SELECT_PUBLICBODY,
  SET_STEP_REQUEST,
  SET_PUBLICBODY,
  SET_PUBLICBODIES,
  CACHE_PUBLICBODIES,
  UPDATE_FIRST_NAME,
  UPDATE_LAST_NAME,
  SET_USER,
  UPDATE_SUBJECT,
  UPDATE_BODY,
  UPDATE_FULL_TEXT,
  UPDATE_ADDRESS,
  UPDATE_EMAIL,
  UPDATE_PRIVATE,
  UPDATE_LAW_TYPE,
  SET_CONFIG,
  STEPS
} from '../../store/mutation_types'

import LetterMixin from './lib/letter-mixin'
import I18nMixin from '../../lib/i18n-mixin'

export default {
  name: 'RequestPage',
  components: {
    PublicbodyChooser,
    PublicbodyBetaChooser,
    PublicbodyMultiChooser,
    UserRegistration,
    SimilarRequests,
    ReviewRequest,
    PbMultiReview,
    RequestForm,
    RequestFormBreadcrumbs,
    RequestPublic,
    UserTerms,
    DjangoSlot,
    SimpleStepper
  },
  mixins: [I18nMixin, LetterMixin],
  props: {
    slots: {
      type: Object,
      default: () => ({})
    },
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
      type: Object
    },
    proofForm: {
      type: Object,
      default: null
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
    },
    betaUi: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      fullTextDisabled: false,
      editingDisabled: this.hideEditing,
      fullLetter: false,
      showReview: false,
      submitting: false,
      STEPS,
      similarSubject: '',
    }
  },
  computed: {
    form() {
      return this.requestForm
    },
    formFields() {
      return this.form.fields
    },
    userformFields() {
      return this.userForm.fields
    },
    conditionalProofForm() {
      if (this.proofForm && this.proofForm.fields.proof) {
        return this.proofForm
      } else {
        return null
      }
    },
    hasReviewPbStep() {
      return false
    },
    steps() {
      return [
        '§introduction',
        '§similarRequests',
        this.i18n.choosePublicBody,
        ...(this.hasReviewPbStep ? [this.i18n.checkSelection] : []),
        '§writeRequest',
        '§account',
        '§submit'
      ]
    },
    progressStepCurrent() {
      // need 0-indexed, but if hasReview there's even one less, so -2
      return (!this.hasReviewPbStep && this.step >= STEPS.REVIEW_PUBLICBODY)
        ? this.step - 2
        : this.step - 1
    },
    publicBodySearch() {
      if (this.publicBody) {
        return this.publicBody.name
      }
      return this.publicbodyDefaultSearch
    },
    publicBodyListView() {
      if (this.multiRequest) {
        return 'multi'
      }
      return 'actionList'
    },
    subject: {
      get() {
        return this.$store.state.subject
      },
      set(value) {
        this.updateSubject(value)
      }
    },
    subjectWasChanged() {
      return this.subject !== this.originalSubject
    },
    hasBody() {
      return this.body && this.body.length > 0
    },
    bodyWasChanged() {
      return this.body !== this.originalBody
    },
    body: {
      get() {
        return this.$store.state.body
      },
      set(value) {
        this.updateBody(value)
      }
    },
    multipleLaws() {
      return this.defaultLaw === null
    },
    fullText: {
      get() {
        return this.$store.state.fullText
      },
      set(value) {
        this.updateFullText(value)
      }
    },
    email: {
      get() {
        return this.$store.state.user.email
      },
      set(value) {
        this.updateEmail(value)
      }
    },
    address: {
      get() {
        return this.$store.state.user.address
      },
      set(value) {
        this.updateAddress(value)
      }
    },
    firstName: {
      get() {
        return this.$store.state.user.first_name
      },
      set(value) {
        this.updateFirstName(value)
      }
    },
    lastName: {
      get() {
        return this.$store.state.user.last_name
      },
      set(value) {
        this.updateLastName(value)
      }
    },
    userPrivate: {
      get() {
        return this.$store.state.user.private
      },
      set(value) {
        this.updatePrivate(value)
      }
    },
    hasPublicBodies() {
      return this.publicBodies.length > 0
    },
    publicBody() {
      return this.getPublicBodyByScope(this.pbScope)
    },
    publicBodies() {
      return this.getPublicBodiesByScope(this.pbScope)
    },
    shouldCheckRequest() {
      return (
        this.body === '' ||
        this.bodyWasChanged ||
        this.subject === '' ||
        this.subjectWasChanged
      )
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
  watch: {
    step() {
      window.scrollTo(0, 0)
    },
    showReview(newShowReview) {
      if (newShowReview) {
        if (!this.reviewModal) {
          this.reviewModal = new Modal(this.$refs.reviewrequest.$el)
          this.$refs.reviewrequest.$el.addEventListener(
            'hidden.bs.modal',
            () => {
              this.showReview = false
            }
          )
        }
        this.reviewModal.show()
      } else {
        this.reviewModal.hide()
      }
    }
  },
  created() {
    this.pbScope = 'make-request'
    this.setConfig(this.config)

    this.initStoreValues(this.formFields, {
      subject: this.updateSubject,
      body: this.updateBody,
      full_text: this.updateFullText,
      law_type: this.updateLawType
    })

    this.updateLawType(
      this.formFields.law_type.value || this.formFields.law_type.initial
    )
    if (this.publicbodies !== null) {
      const pbs = this.publicbodies
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
        address: this.updateAddress
      })
    } else {
      this.initStoreValues(this.userformFields, {
        user_email: this.updateEmail,
        first_name: this.updateFirstName,
        last_name: this.updateLastName,
        address: this.updateAddress,
        private: this.updatePrivate
      })
    }
    this.originalBody = this.body
    this.originalSubject = this.subject
  },
  mounted() {
    if (this.hasPublicBodies) {
      this.setStepRequest()
    }
    window.addEventListener('beforeunload', (e) => {
      if (this.submitting) {
        return
      }
      if (!this.stepWriteRequest) {
        return
      }
      // If you prevent default behavior in Mozilla Firefox prompt will always be shown
      e.preventDefault()
      // Chrome requires returnValue to be set
      e.returnValue = this.i18n.sureCancel
      return e.returnValue
    })
  },
  methods: {
    initStoreValues(fields, mapping) {
      for (const key in mapping) {
        const method = mapping[key]
        if (fields[key] === undefined) {
          continue
        }
        method(fields[key].value || fields[key].initial)
      }
    },
    ...mapMutations({
      setStep: SET_STEP,
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
      updateAddress: UPDATE_ADDRESS,
      updateEmail: UPDATE_EMAIL,
      updatePrivate: UPDATE_PRIVATE
    }),
    ...mapActions(['getLawsForPublicBodies'])
  }
}
</script>

<style lang="scss" scoped>
@import '../../../styles/variables';

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
  margin: 0 0 $spacer * 2;
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

.saved-full-text-enter-active,
.saved-full-text-leave-active {
  transition: opacity 0.5s;
}
.saved-full-text-enter,
.saved-full-text-leave-to {
  opacity: 0;
}

.show-full-letter {
  color: #999;
  text-decoration: underline;
}
</style>
