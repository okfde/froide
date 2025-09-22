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
        into the future - "steps previously unlocked"
      reflect "done" pbly = this seems to be just a > step check
    -->
    <SimpleStepper
      class="bg-body-tertiary"
      :step="progressStepCurrent"
      :steps="steps"
      clickable
      @step-click="stepClick"
      >
      §step <strong>{{ this.progressStepCurrent }}/{{ this.steps.length }}</strong>:
      {{ this.steps[this.step] }}
    </SimpleStepper>

    <div>STEP: {{ this.step }}</div>

    <div :class="{ container: !multiRequest, 'container-multi': multiRequest }">
      <div
        v-show="step === STEPS.PREVIEW_SUBMIT"
        >
        <DjangoSlot
          name="messages"
          />
      </div>

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
                        <a
                          :href="config.url.helpRequestWhat"
                          @click.prevent="$refs.onlineHelp.show(config.url.helpRequestWhat)"
                          >§Was kann ich anfragen?</a><br/>
                        <a
                          :href="config.url.helpRequestWhatNot"
                          @click.prevent="$refs.onlineHelp.show(config.url.helpRequestWhatNot)"
                          >§Was kann ich NICHT anfragen?</a><br/>
                      </div>
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
            <div class="my-3">
              <a class="btn btn-link text-decoration-none ps-0"
                :href="'#step-' + STEPS.INTRO"
                @click="setStep(STEPS.INTRO)"
                >← <u>{{ i18n.back }}</u></a>
            </div>
            <div class="mb-4">
              <label for="similarSubject" class="form-label">
                §Im FragDenStaat-Archiv suchen:
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
                    §Suchen
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
                §Weiter
              </button>
            </div>
          </div>

          <fieldset
            v-if="stepSelectPublicBody"
            id="step-publicbody"
            class="mt-5">
            <div class="my-3 row">
              <div class="col">
                <a class="btn btn-link text-decoration-none ps-0"
                  :href="'#step-' + STEPS.FIND_SIMILAR"
                  @click="setStep(STEPS.FIND_SIMILAR)"
                  >← <u>{{ i18n.back }}</u></a>
              </div>
              <div class="col ms-auto text-end">
                <button
                  type="button"
                  class="btn btn-primary"
                  :disabled="!stepCanContinue(pbScope)"
                  @click="setStep((multiRequest && tmpMulti) ? STEPS.REVIEW_PUBLICBODY : STEPS.CREATE_ACCOUNT)"
                  >§Weiter</button>
              </div>
            </div>
            <!-- PublicBodyChoosers advance step by mutations like SET_STEP_REQUEST (mapped to setStepRequest) -->
            <div v-if="multiRequest && tmpMulti">
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
            >
            <div class="my-3">
              <a class="btn btn-link text-decoration-none ps-0"
                :href="'#step-' + STEPS.SELECT_PUBLICBODY"
                @click="setStep(STEPS.SELECT_PUBLICBODY)"
                >← <u>{{ i18n.back }}</u></a>
            </div>
            <PbMultiReview name="publicbody" :i18n="i18n" :scope="pbScope" />
          </fieldset>

          <!-- need v-show over v-if so <input>s are in DOM while submitting -->
          <div
            v-show="step === STEPS.CREATE_ACCOUNT">

            <div class="my-3">
              <a class="btn btn-link text-decoration-none ps-0"
                :href="'#step-' + ((multiRequest && tmpMulti) ? STEPS.REVIEW_PUBLICBODY : STEPS.SELECT_PUBLICBODY)"
                @click="setStep((multiRequest && tmpMulti) ? STEPS.REVIEW_PUBLICBODY : STEPS.SELECT_PUBLICBODY)"
                >← <u>{{ i18n.back }}</u></a>
            </div>

            <div v-if="!user.id">
              <p>
                §Sie haben schon einen Account?<br/>
                <DjangoSlot name="loginlink"></DjangoSlot>
              </p>
              <p><small>§Dieses Formular merkt sich Ihre angaben.</small></p>
            </div>

            <UserRegistration
              :form="userForm"
              :user-form="userForm"
              :config="config"
              :user="user.id ? user : null"
              :default-law="defaultLaw"
              v-model:initial-first-name="firstName"
              v-model:initial-last-name="lastName"
              v-model:initial-email="email"
              />

            <div>TODO: passwort (optional)</div>

            <UserAddress
              v-model:initial-address="address"
              :i18n="i18n"
              :form="userForm"
              :config="config"
              :address-help-text="userForm.fields.address.help_text"
              />

            <UserPublic
              v-if="!user.id"
              :user-form="userForm"
              :config="config"
              v-model:initial-private="userPrivate"
              @online-help="$refs.onlineHelp.show($event)"
              />
            <UserTerms
              v-if="!user.id"
              :form="userForm"
              v-model:initial-terms="terms"
              />
            <div>
              TODO: validation of vorname/name<br/>
              <button
                type="button"
                class="btn btn-primary"
                :disabled="!stepCanContinue(pbScope)"
                @click="setStep(STEPS.WRITE_REQUEST)"
                >
                Weiter
              </button>
            </div>

          </div>

          <fieldset v-show="stepWriteRequest" id="step-request" class="mt-3">
            <div class="my-3">
              <a class="btn btn-link text-decoration-none ps-0"
                :href="'#step-' + STEPS.CREATE_ACCOUNT"
                @click="setStep(STEPS.CREATE_ACCOUNT)"
                >← <u>{{ i18n.back }}</u></a>
            </div>
            TODO: rename/emphasize ellipsis button
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
              :submitting="submitting"
              @x-set-step-select-public-body="setStepSelectPublicBody"
              @set-step-select-public-body="setStep(STEPS.SELECT_PUBLICBODY)">
              <template #request-hints>
                <DjangoSlot name="request-hints" />
              </template>
              <template #request-legend-title>
                <DjangoSlot name="request-legend-title" />
              </template>
            </RequestForm>
            <div>
              TODO: validation<br/>
              <button
                type="button"
                class="btn btn-primary"
                :disabled="!stepCanContinue(pbScope)"
                @click="setStep(STEPS.REQUEST_PUBLIC)"
                >
                §Weiter
              </button>
            </div>
            <SimilarRequests
              v-if="showSimilar"
              :publicbodies="publicBodies"
              :subject="subject"
              :config="config" />
          </fieldset>

          <div v-show="step == STEPS.REQUEST_PUBLIC">
            <div class="my-3">
              <a class="btn btn-link text-decoration-none ps-0"
                :href="'#step-' + STEPS.CREATE_ACCOUNT"
                @click="setStep(STEPS.CREATE_ACCOUNT)"
                >← <u>{{ i18n.back }}</u></a>
            </div>
            TODO: add texts around
            <RequestPublic
              :form="requestForm"
              :hide-public="hidePublic"
              v-model:initial-public="requestPublic"
              />
            <div>
              <button
                type="button"
                class="btn btn-primary"
                @click="setStep(STEPS.PREVIEW_SUBMIT)"
                >
                §Weiter
              </button>
            </div>
          </div>

          <div v-if="step === STEPS.PREVIEW_SUBMIT">
            <div class="my-3">
              <a class="btn btn-link text-decoration-none ps-0"
                :href="'#step-' + STEPS.REQUEST_PUBLIC"
                @click="setStep(STEPS.REQUEST_PUBLIC)"
                >← <u>{{ i18n.back }}</u></a>
            </div>
            <ReviewRequest
              :i18n="i18n"
              :config="config"
              :pb-scope="pbScope"
              :publicbodies="publicBodies"
              :user="user"
              :user-form="userForm"
              :request-form="requestForm"
              :default-law="defaultLaw"
              :subject="subject"
              :body="body"
              :multi-request="multiRequest"
              :full-text="fullText"
              :hide-publicbody-chooser="hidePublicbodyChooser"
              :show-draft="showDraft"
              @submit="submitting = true"
              @online-help="$refs.onlineHelp.show($event)"
              />
          </div>
        </div>
      </div>
    </div>
    <button type="submit" @click="submitting = true">submit</button>
    <button type="button" @click="$refs.onlineHelp.show('foo')">test oh</button>
    <OnlineHelp ref="onlineHelp" :i18n="i18n"></OnlineHelp>
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
import UserPublic from './user-public.vue'
import UserAddress from './user-address.vue'
import DjangoSlot from '../../lib/django-slot.vue'
import SimpleStepper from '../postupload/simple-stepper.vue'
import OnlineHelp from '../online-help.vue'

import { mapGetters, mapMutations, mapActions } from 'vuex'

import {
  SET_STEP,
  SET_STEP_NO_HISTORY,
  // SET_STEP_SELECT_PUBLICBODY,
  // SET_STEP_REQUEST,
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
  UPDATE_REQUEST_PUBLIC,
  UPDATE_LAW_TYPE,
  UPDATE_TERMS,
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
    UserPublic,
    UserAddress,
    DjangoSlot,
    SimpleStepper,
    OnlineHelp,
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
      tmpMulti: document.location.search.indexOf('multi') > -1,
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
    // TODO what is this
    conditionalProofForm() {
      if (this.proofForm && this.proofForm.fields.proof) {
        return this.proofForm
      } else {
        return null
      }
    },
    steps() {
      return [
        '§introduction',
        '§similarRequests',
        this.i18n.choosePublicBody,
        // ...(this.hasReviewPbStep ? [this.i18n.checkSelection] : []),
        this.userInfo ? '§Adresse' : '§account',
        '§writeRequest',
        '§submit'
      ]
    },
    progressStepCurrent() {
      // needs to be zero-indexed
      return ({
        [STEPS.INTRO]: 0,
        [STEPS.FIND_SIMILAR]: 1,
        [STEPS.SELECT_PUBLICBODY]: 2,
        [STEPS.REVIEW_PUBLICBODY]: 2,
        [STEPS.CREATE_ACCOUNT]: 3,
        [STEPS.WRITE_REQUEST]: 4,
        [STEPS.REQUEST_PUBLIC]: 4,
        [STEPS.PREVIEW_SUBMIT]: 5,
        [STEPS.OUTRO]: 5
      })[this.step]
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
    // subjectWasChanged() {
    //   return this.subject !== this.originalSubject
    // },
    hasBody() {
      return this.body && this.body.length > 0
    },
    // bodyWasChanged() {
    //   return this.body !== this.originalBody
    // },
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
    requestPublic: {
      get() {
        return this.$store.state.requestPublic
      },
      set(value) {
        this.updateRequestPublic(value)
      }
    },
    terms: {
      get() {
        return this.$store.state.user.terms
      },
      set(value) {
        this.updateTerms(value)
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
    // shouldCheckRequest() {
    //   return (
    //     this.body === '' ||
    //     this.bodyWasChanged ||
    //     this.subject === '' ||
    //     this.subjectWasChanged
    //   )
    // },
    ...mapGetters([
      'user',
      'getPublicBodyByScope',
      'getPublicBodiesByScope',
      'stepWriteRequest',
      'stepReviewPublicBodies',
      'stepSelectPublicBody',
      'step',
      'lawType',
      'defaultLaw',
      'stepCanContinue',
    ])
  },
  watch: {
    step() {
      this.writeToStorage({ scope: this.pbScope })
      window.scrollTo(0, 0)
    }
  },
  created() {
    // window.__fds_debug_$store = this.$store
    this.pbScope = this.config.draftId
      ? 'make-request-draft-' + this.config.draftId
      : 'make-request'
    // from props
    this.setConfig(this.config)

    // init step value
    this.initStoreValues({
      scope: this.pbScope,
      preferStorage: true, // ...step always from storage, we omit formFields
      mutationMap: {
        step: SET_STEP,
      }
    })

    if (this.requestForm.fields.draft.initial && this.step === STEPS.INTRO) {
      console.log('request is draft, skipping intro etc.')
      this.setStep(STEPS.WRITE_REQUEST)
    }

    // init "regular form values" from storage if not POSTed
    // (not form-submitted, but refreshed, or returned from login)
    this.initStoreValues({
      scope: this.pbScope,
      preferStorage: !this.config.wasPost,
      formFields: this.formFields,
      formCoerce: {
        public: (djangoBoolStr) => djangoBoolStr === 'True'
      },
      mutationMap: {
        subject: UPDATE_SUBJECT,
        body: UPDATE_BODY,
        full_text: UPDATE_FULL_TEXT, // TODO
        // law_type: UPDATE_LAW_TYPE, // TODO
        public: UPDATE_REQUEST_PUBLIC,
      }
    })

    // PBs from prop, which is expanded in make_request context
    // (formFields would have IDs only)
    this.initStoreValues({
      scope: this.pbScope,
      scoped: true, // also, PBs are scoped
      preferStorage: !this.config.wasPost,
      mutationMap: {
        publicBodies: SET_PUBLICBODIES
      },
      propMap: {
        publicBodies: this.publicbodies
      }
    })

    // TODO I think this does nothing
    // this.updateLawType(
    //   this.formFields.law_type.value || this.formFields.law_type.initial
    // )

    this.cachePublicBodies(this.publicBodies)
    // "cache" laws for the PBs we just retrieved
    this.getLawsForPublicBodies(this.publicBodies)

    // prop set = is authenticated
    if (this.userInfo !== null) {
      this.initStoreValues({
        scope: this.pbScope,
        preferStorage: false,
        // no formFields, always from prop
        propMap: {
          user: this.userInfo 
        },
        mutationMap: {
          user: SET_USER,
        }
      })
    } else {
      // note that for logged-out users their "fields" are stored flatly, not in a .user object,
      // and hence need individual, per-field mutations.
      // see writeToStorage, reduced, where they are flattened/plucked
      this.initStoreValues({
        scope: this.pbScope,
        preferStorage: !this.config.wasPost,
        formFields: this.userformFields,
        formCoerce: {
          private: (djangoBoolStr) => djangoBoolStr === 'True'
        },
        mutationMap: {
          user_email: UPDATE_EMAIL,
          first_name: UPDATE_FIRST_NAME,
          last_name: UPDATE_LAST_NAME,
          private: UPDATE_PRIVATE,
          address: UPDATE_ADDRESS,
          terms: UPDATE_TERMS,
        }
      })
    }

    // note that an empty address will be pre-filled for logged-in users in UserAddress.data
    this.initStoreValues({
      scope: this.pbScope,
      preferStorage: !this.config.wasPost,
      formFields: this.userformFields,
      mutationMap: {
        address: UPDATE_ADDRESS
      }
    })

    // this.body are state getter/setters
    // original* were non-data attributes used for shouldCheckRequest
    // this.originalBody = this.body
    // this.originalSubject = this.subject
  },
  mounted() {
    document.forms.make_request.addEventListener('submit', () => {
      // invalidate storage, will load from form fields next time
      this.purgeStorage({ scope: this.pbScope, keepStep: true })
    })
    // TODO pbly delete
    // if (this.hasPublicBodies) {
    //   this.setStepRequest()
    // }
    // TODO maybe unnecessary when remembered
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
    window.addEventListener('popstate', (e) => {
      console.log('### popstate', e.state?.step)
      if (!e.state) return
      if (e.state.step) {
        this.setStepNoHistory(e.state.step)
      } else {
        console.log('### popstate, but no step')
      }
    })
  },
  methods: {
    initStoreValues2(fields, mapping) {
      for (const key in mapping) {
        const method = mapping[key]
        if (fields[key] === undefined) {
          continue
        }
        method(fields[key].value || fields[key].initial)
      }
    },
    stepClick(stepIndex) {
      this.setStep(([
        STEPS.INTRO,
        STEPS.FIND_SIMILAR,
        STEPS.SELECT_PUBLICBODY,
        STEPS.CREATE_ACCOUNT,
        STEPS.WRITE_REQUEST,
        STEPS.PREVIEW_SUBMIT
      ])[stepIndex])
    },
    ...mapMutations({
      setStep: SET_STEP,
      setStepNoHistory: SET_STEP_NO_HISTORY,
      // setStepSelectPublicBody: SET_STEP_SELECT_PUBLICBODY,
      // setStepRequest: SET_STEP_REQUEST,
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
      updatePrivate: UPDATE_PRIVATE,
      updateRequestPublic: UPDATE_REQUEST_PUBLIC,
      updateTerms: UPDATE_TERMS,
    }),
    ...mapActions([
      'getLawsForPublicBodies',
      'initStoreValues',
      'writeToStorage',
      'purgeStorage',
    ])
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
