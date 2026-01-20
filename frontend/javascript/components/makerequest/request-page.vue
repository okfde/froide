<template>
  <div class="make-request-container">
    <SimpleStepper
      class="bg-body-tertiary"
      :step="stepperStepCurrent"
      :steps="stepperSteps.map((step) => step.label)"
      clickable
      keep-visited-clickable
      @step-click="stepperClick"
    >
      {{ i18n.step }}
      <!-- avoid 0 -->
      <strong
        >{{ this.stepperStepCurrent + 1 }}/{{
          this.stepperSteps.length
        }}</strong
      >:
      {{ this.stepperSteps[this.stepperStepCurrent]?.label }}
    </SimpleStepper>

    <div class="container">
      <div class="row">
        <div class="col">
          <!-- v-show="step === STEPS.PREVIEW_SUBMIT"
       ...would be less naggy here, but also more confusing in certain cases,
       e.g. submit from froide-campaign with target _blank -->
          <div class="my-2">
            <DjangoSlot name="messages" />
          </div>

          <div class="row justify-content-lg-center">
            <div class="col-lg-12">
              <div v-if="stepBack" class="my-3 d-flex justify-content-between">
                <a
                  class="btn btn-link text-decoration-none ps-0"
                  :href="'#step-' + stepBack"
                  @click="setStep(stepBack)"
                  >← <u>{{ i18n.back }}</u></a
                >
                <button
                  v-if="topNextLabel"
                  type="button"
                  class="btn btn-primary"
                  :disabled="!stepCanContinue(pbScope)"
                  @click="setStep(stepNext)"
                >
                  {{ topNextLabel }}
                </button>
              </div>

              <!-- keep visible for all steps -->
              <div
                v-if="requestForm.nonFieldErrors.length > 0"
                class="alert alert-danger"
              >
                <p
                  v-for="error in requestForm.nonFieldErrors"
                  :key="error"
                  v-html="error"
                />
              </div>
              <div v-if="fetchError" class="alert alert-danger">
                <strong>{{ i18n.error }}</strong>
                {{ fetchError }}
              </div>

              <h1
                v-if="hidePublicbodyChooser && hasPublicBodies"
                class="my-3 fs-5"
              >
                {{ i18n.requestTo }}
                {{ publicBodies.map((pb) => pb.name).join(', ') }}
              </h1>

              <!-- STEP: INTRO / CAMPAIGNS -->

              <div v-if="step === STEPS.INTRO" class="mt-5" id="step_intro">
                <h1>{{ i18n.makeRequest }}</h1>
                <p>{{ i18n.whatDoYouWantToDo }}</p>
                <IntroCampaigns :config="config" @step-next="setStep(stepNext)">
                  <template #campaign_main>
                    <DjangoSlot name="campaign_main" />
                  </template>
                  <template #campaigns>
                    <DjangoSlot name="campaigns" />
                  </template>
                </IntroCampaigns>
                <DjangoSlot
                  name="campaign_other"
                  has-onlinehelp-links
                  @onlinehelp-click="onlineHelpShow($event)"
                />
              </div>

              <!-- STEP: INTRO / HOWTO -->

              <div
                v-if="step === STEPS.INTRO_HOWTO"
                class="mt-5"
                id="step_intro_howto"
              >
                <DjangoSlot
                  name="intro_howto"
                  has-onlinehelp-links
                  @onlinehelp-click="onlineHelpShow($event)"
                />
                <div>
                  <button
                    type="button"
                    class="btn btn-primary"
                    @click="setStep(stepNext)"
                  >
                    {{ i18n.stepNext }}
                  </button>
                </div>
                <IntroSkipPreference :config="config" />
              </div>

              <!-- STEP: FIND SIMILAR REQUESTS -->

              <div
                v-show="step === STEPS.FIND_SIMILAR"
                class="mt-3"
                id="step_find_similar"
              >
                <h2>{{ i18n.findSimilarRequests }}</h2>
                <div class="row">
                  <div class="col-lg-9">
                    <DjangoSlot name="find-similar-requests-preamble" />
                  </div>
                </div>
                <SimilarRequestSearch :config="config" />
                <div>
                  <button
                    type="button"
                    class="btn btn-primary"
                    @click="setStep(stepNext)"
                  >
                    {{ i18n.stepSkip }}
                  </button>
                </div>
                <IntroSkipPreference :config="config" />
              </div>

              <!-- STEP: SELECT PUBLIC BODY -->

              <div
                v-if="step === STEPS.SELECT_PUBLICBODY"
                id="step_select_publicbody"
              >
                <p v-if="publicBodies.length > 0">
                  {{ i18n.currentlyChosen }}
                  {{ publicBodies.map((pb) => pb.name).join(', ') }}
                </p>

                <div v-if="multiRequest">
                  <!-- PublicBodyChoosers advance step by mutations like SET_STEP_REQUEST (mapped to setStepRequest) -->
                  <PublicbodyMultiChooser
                    name="publicbody"
                    :defaultsearch="publicBodySearch"
                    :scope="pbScope"
                    :config="config"
                  >
                    <template #publicbody-missing>
                      <DjangoSlot name="publicbody-missing" />
                    </template>
                  </PublicbodyMultiChooser>
                </div>
                <div v-else>
                  <div class="row">
                    <div class="col-lg-9">
                      <DjangoSlot name="publicbody-legend-title" />
                      <DjangoSlot name="publicbody-help-text" />
                      <PublicbodyBetaChooser
                        name="publicbody"
                        :defaultsearch="publicBodySearch"
                        :scope="pbScope"
                        :form="publicbodyForm"
                        :config="config"
                        @step-next="setStep(stepNext)"
                      >
                        <template #search-hint>
                          <DjangoSlot
                            name="publicbody-search-hint"
                            has-onlinehelp-links
                            @onlinehelp-click="onlineHelpShow($event)"
                          />
                        </template>
                      </PublicbodyBetaChooser>
                      <DjangoSlot name="publicbody-missing" />
                    </div>
                  </div>
                </div>
              </div>

              <!-- STEP: REVIEW PUBLIC BODIES -->

              <div
                v-if="step === STEPS.REVIEW_PUBLICBODY"
                id="step_review_publicbody"
              >
                <PbMultiReview
                  name="publicbody"
                  :i18n="i18n"
                  :scope="pbScope"
                  @step-next="setStep(stepNext)"
                />
              </div>

              <!-- STEPS: LOGIN or CREATE ? -->

              <div v-show="step === STEPS.LOGIN_CREATE" id="step_login_create">
                <h2>{{ i18n.account }}</h2>
                <div class="row">
                  <div class="col-md-6 mb-4">
                    <p class="mb-auto">
                      {{ i18n.createAccountPreamble }}
                    </p>
                    <div class="mt-3">
                      <button
                        type="button"
                        class="btn btn-primary"
                        @click="setStep(stepNext)"
                      >
                        {{ i18n.createAccount }}
                      </button>
                    </div>
                  </div>
                  <div class="col-md-6 mb-4">
                    <p class="mb-auto">
                      {{ i18n.doYouAlreadyHaveAccount }}<br />
                      <small>{{ i18n.thisFormRemembers }}</small>
                    </p>
                    <div class="mt-3">
                      <a :href="config.url.login" class="btn btn-primary">{{
                        i18n.login
                      }}</a>
                    </div>
                  </div>
                </div>
              </div>

              <!-- STEP: CREATE ACCOUNT -->

              <!-- need v-show over v-if so <input>s are in DOM while submitting -->
              <div
                v-show="step === STEPS.CREATE_ACCOUNT"
                id="step_create_account"
              >
                <h2>{{ i18n.createAccount }}</h2>
                <UserCreateAccount
                  v-if="!user.id"
                  :config="config"
                  :user="user"
                  :request-form="requestForm"
                  :user-form="userForm"
                  :default-law="defaultLaw"
                  show-next-button
                  show-user-claims-vip
                  @step-next="setStep(stepNext)"
                  @onlinehelp-click="onlineHelpShow($event)"
                >
                  <template #userPublicPreamble>
                    <DjangoSlot name="user-public-preamble"></DjangoSlot>
                  </template>
                </UserCreateAccount>
              </div>

              <!-- STEP: WRITE REQUEST -->

              <div
                v-show="step === STEPS.WRITE_REQUEST"
                id="step_write_request"
                class="mt-3"
              >
                <RequestForm
                  :config="config"
                  :publicbodies="publicBodies"
                  :user="user"
                  :request-form="requestForm"
                  :user-form="userForm"
                  :proof-form="proofForm"
                  :hide-publicbody-chooser="hidePublicbodyChooser"
                  :hide-full-text="hideFullText"
                  :hide-editing="hideEditing"
                  show-next-button
                  :multi-request="multiRequest"
                  :confirm-required="confirmRequired"
                  :default-law="defaultLaw"
                  :law-type="lawType"
                  v-model:initial-subject="subject"
                  v-model:initial-body="body"
                  v-model:initial-full-text="fullText"
                  :submitting="submitting"
                  @step-next="setStep(stepNext)"
                  @step-back="setStep(stepBack)"
                >
                  <template #request-hints>
                    <DjangoSlot
                      name="request-hints"
                      has-onlinehelp-links
                      @onlinehelp-click="onlineHelpShow($event)"
                    />
                  </template>
                  <template #request-legend-title>
                    <DjangoSlot name="request-legend-title" />
                  </template>
                  <template #request-user-confirm>
                    <DjangoSlot name="request-user-confirm" />
                  </template>
                </RequestForm>
                <SimilarRequests
                  v-if="showSimilar"
                  :publicbodies="publicBodies"
                  :subject="subject"
                  :config="config"
                />
              </div>

              <!-- STEP: VISIBILITY -->

              <div
                v-show="step == STEPS.REQUEST_PUBLIC"
                id="step_request_public"
              >
                <h2>{{ i18n.requestVisibility }}</h2>
                <DjangoSlot name="request-public-preamble" />
                <RequestPublic
                  :form="requestForm"
                  :hide-public="hidePublic"
                  v-model:initial-public="requestPublic"
                />
                <DjangoSlot name="request-public-postamble" />
                <div class="my-4">
                  <button
                    type="button"
                    class="btn btn-primary"
                    @click="setStep(stepNext)"
                  >
                    {{ i18n.stepNext }}
                  </button>
                </div>
              </div>

              <!-- STEP: PREVIEW -->

              <div
                v-if="step === STEPS.PREVIEW_SUBMIT"
                id="step_preview_submit"
              >
                <h2>{{ i18n.previewAndSubmit }}</h2>
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
                  :hide-public="hidePublic"
                  :hide-publicbody-chooser="hidePublicbodyChooser"
                  :show-draft="showDraft"
                  @submit="submit"
                  @onlinehelp-click="onlineHelpShow($event)"
                />
              </div>

              <!-- No STEP: OUTRO here, because it is handled by the form success page -->
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- /.container -->
    <OnlineHelp ref="onlineHelp" :i18n="i18n"></OnlineHelp>
  </div>
</template>

<script>
import SimilarRequests from './similar-requests'
import SimilarRequestSearch from './similar-request-search'
// TODO: rename, un-beta, remove old?
import PublicbodyBetaChooser from '../publicbody/publicbody-beta-chooser.vue'
import PublicbodyMultiChooser from '../publicbody/publicbody-multichooser'
import ReviewRequest from './review-request'
import PbMultiReview from '../publicbody/pb-multi-review'
import RequestForm from './request-form'
import RequestPublic from './request-public'
import DjangoSlot from '../../lib/django-slot.vue'
import SimpleStepper from '../postupload/simple-stepper.vue'
import OnlineHelp from '../online-help.vue'

import { mapGetters, mapMutations, mapActions } from 'vuex'

import {
  SET_STEP,
  SET_STEP_NO_HISTORY,
  UPDATE_SUBJECT,
  UPDATE_BODY,
  UPDATE_FULL_TEXT,
  UPDATE_REQUEST_PUBLIC,
  UPDATE_TERMS,
  STEPS,
  CACHE_PUBLICBODIES,
  SET_PUBLICBODIES
} from '../../store/mutation_types'

import LetterMixin from './lib/letter-mixin'
import StoreValueMixin from './lib/store-values-mixin'
import I18nMixin from '../../lib/i18n-mixin'
import UserCreateAccount from './user-create-account.vue'
import IntroCampaigns from './intro-campaigns.vue'
import IntroSkipPreference from './intro-skip-preference.vue'

export default {
  name: 'RequestPage',
  components: {
    IntroSkipPreference,
    IntroCampaigns,
    PublicbodyBetaChooser,
    PublicbodyMultiChooser,
    SimilarRequests,
    SimilarRequestSearch,
    ReviewRequest,
    PbMultiReview,
    RequestForm,
    RequestPublic,
    UserCreateAccount,
    DjangoSlot,
    SimpleStepper,
    OnlineHelp
  },
  mixins: [I18nMixin, LetterMixin, StoreValueMixin],
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
    requestFormInitial: {
      type: Object
    },
    userFormInitial: {
      type: Object
    },
    proofFormInitial: {
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
    confirmRequired: {
      type: Boolean,
      default: false
    }
  },
  inject: ['django-slots'],
  data() {
    return {
      pbScope: this.config.draftId
        ? 'make-request-draft-' + this.config.draftId
        : 'make-request',
      fullTextDisabled: false,
      editingDisabled: this.hideEditing,
      fullLetter: false,
      showReview: false,
      submitting: false,
      STEPS,
      similarSubject: '',
      fetchedForms: null,
      fetchError: null
    }
  },
  provide() {
    return {
      pbScope: this.pbScope
    }
  },
  computed: {
    requestForm() {
      return this.fetchedForms?.request_form || this.requestFormInitial
    },
    userForm() {
      return this.fetchedForms?.user_form || this.userFormInitial
    },
    proofForm() {
      if (
        !(
          this.proofFormInitial?.fields?.proof ||
          this.proofFormInitial?.fields?.proof_name
        )
      ) {
        return null
      }
      return this.fetchedForms?.proof_form || this.proofFormInitial
    },
    steps() {
      // TODO needs discussion:
      // hide vs. jump over INTRO+SIMILAR when hidePbChooser et al are set
      const steps = []
      if (this.hasCampaigns && !this.hidePublicbodyChooser) {
        steps.push(STEPS.INTRO)
      }
      // assume we don't need a generic intro for API-specified usage
      if (!(this.hidePublicbodyChooser || !this.hasIntroHowtoContent)) {
        steps.push(STEPS.INTRO_HOWTO)
      }
      if (this.showSimilar && !this.hidePublicbodyChooser) {
        steps.push(STEPS.FIND_SIMILAR)
      }
      if (!this.hidePublicbodyChooser) {
        steps.push(STEPS.SELECT_PUBLICBODY)
        if (this.multiRequest) {
          steps.push(STEPS.REVIEW_PUBLICBODY)
        }
      }
      // for /make-request/to/foo we want to land on WRITE_REQUEST...
      if (this.hasPublicBodiesByParam) {
        steps.push(STEPS.WRITE_REQUEST)
        if (!this.hidePublic) {
          steps.push(STEPS.REQUEST_PUBLIC)
        }
      }
      // ...and sign up afterwards...
      if (!this.userInfo) {
        steps.push(STEPS.LOGIN_CREATE)
        steps.push(STEPS.CREATE_ACCOUNT)
      }
      // ...but usually we sign up first and then write:
      if (!this.hasPublicBodiesByParam) {
        steps.push(STEPS.WRITE_REQUEST)
        if (!this.hidePublic) {
          steps.push(STEPS.REQUEST_PUBLIC)
        }
      }
      steps.push(STEPS.PREVIEW_SUBMIT)
      steps.push(STEPS.OUTRO)
      return steps
    },
    stepLabels() {
      return {
        [STEPS.INTRO]: this.i18n.introduction,
        [STEPS.INTRO_HOWTO]: this.i18n.introduction,
        [STEPS.FIND_SIMILAR]: this.i18n.similarRequests,
        [STEPS.SELECT_PUBLICBODY]: this.i18n.choosePublicBody,
        [STEPS.REVIEW_PUBLICBODY]: this.i18n.choosePublicBody,
        [STEPS.LOGIN_CREATE]: this.i18n.account,
        [STEPS.CREATE_ACCOUNT]: this.i18n.account,
        [STEPS.WRITE_REQUEST]: this.i18n.writeMessage,
        [STEPS.REQUEST_PUBLIC]: this.i18n.writeMessage,
        [STEPS.PREVIEW_SUBMIT]: this.i18n.submitRequest,
        [STEPS.OUTRO]: this.i18n.submitRequest
      }
    },
    stepperSteps() {
      const remap = {
        // "display INTRO_HOWTO as INTRO"
        [STEPS.INTRO]: STEPS.INTRO_HOWTO,
        [STEPS.SELECT_PUBLICBODY]: STEPS.REVIEW_PUBLICBODY,
        [STEPS.LOGIN_CREATE]: STEPS.CREATE_ACCOUNT,
        [STEPS.WRITE_REQUEST]: STEPS.REQUEST_PUBLIC,
        [STEPS.PREVIEW_SUBMIT]: STEPS.OUTRO
      }
      return this.steps
        .filter((stepId) => !Object.values(remap).includes(stepId))
        .map((stepId) => ({
          stepId,
          altStepId: remap[stepId],
          label: this.stepLabels[stepId]
        }))
    },
    stepperStepCurrent() {
      return this.stepperSteps.findIndex(
        (_) => _.stepId === this.step || _.altStepId === this.step
      )
    },
    stepIndex() {
      return this.steps.findIndex((_) => _ === this.step)
    },
    stepBack() {
      if (this.stepIndex <= 0) return false
      return this.steps[this.stepIndex - 1]
    },
    stepNext() {
      if (this.stepIndex === -1 || this.stepIndex > this.steps.length - 1)
        return false
      return this.steps[this.stepIndex + 1]
    },
    topNextLabel() {
      if (
        [
          STEPS.LOGIN_CREATE,
          STEPS.CREATE_ACCOUNT,
          STEPS.WRITE_REQUEST,
          STEPS.PREVIEW_SUBMIT,
          STEPS.OUTRO
        ].includes(this.step)
      ) {
        return false
      }
      if (this.step === STEPS.FIND_SIMILAR) {
        return this.i18n.stepSkip
      }
      return this.i18n.stepNext
    },
    preventUnload() {
      // notably, not STEPS.LOGIN_CREATE
      return [
        STEPS.SELECT_PUBLICBODY,
        STEPS.REVIEW_PUBLICBODY,
        STEPS.CREATE_ACCOUNT,
        STEPS.WRITE_REQUEST,
        STEPS.REQUEST_PUBLIC,
        STEPS.PREVIEW_SUBMIT
      ].includes(this.step)
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
    hasCampaigns() {
      return this['django-slots'].campaigns?.textContent.trim() !== ''
    },
    skipIntroHowtoPreference() {
      return this.config.settings.skip_intro_howto
    },
    hasIntroHowtoContent() {
      return this['django-slots'].intro_howto?.textContent.trim() !== ''
    },
    subject: {
      get() {
        return this.$store.state.subject
      },
      set(value) {
        this.updateSubject(value)
      }
    },
    hasBody() {
      return this.body && this.body.length > 0
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
    // e.g. /make-request/to/foo/
    // note the lowercase b
    hasPublicBodiesByParam() {
      return this.publicbodies.length > 0
    },
    publicBody() {
      return this.getPublicBodyByScope(this.pbScope)
    },
    publicBodies() {
      return this.getPublicBodiesByScope(this.pbScope)
    },
    ...mapGetters([
      'user',
      'getPublicBodyByScope',
      'getPublicBodiesByScope',
      'stepWriteRequest',
      'step',
      'lawType',
      'defaultLaw',
      'stepCanContinue'
    ])
  },
  watch: {
    step() {
      this.writeToStorage({ scope: this.pbScope })
      window.scrollTo(0, 0)
    }
  },
  created() {
    this.initAllStoreValues()

    // init step value, always from storage (formFields & propMap omitted)
    this.initStoreValues({
      scope: this.pbScope,
      mutationMap: {
        step: SET_STEP
      }
    })

    // PBs from prop, which is expanded in make_request context
    // (formFields would have IDs only)
    // prop has precedence over storage, so a reloaded /make-request/to/123/ URL
    //   will always default back to PB 123
    this.initStoreValues({
      scope: this.pbScope,
      scoped: true, // also, PBs are scoped
      ignoreStorage: this.config.wasPost,
      mutationMap: {
        publicBodies: SET_PUBLICBODIES
      },
      propMap: {
        // we want an empty array to fall through to storage
        publicBodies: this.publicbodies?.length > 0 ? this.publicbodies : null
      }
    })

    this.cachePublicBodies(this.publicBodies)
    // "cache" laws for the PBs we just retrieved
    this.getLawsForPublicBodies(this.publicBodies)

    // setFirstStep depends on state (publicbodies, subject...) so has to come after initStoreValues
    this.setFirstStep()
  },
  mounted() {
    document.forms.make_request.addEventListener('submit', () => {
      // invalidate storage, will load from form fields next time
      this.purgeStorage({ scope: this.pbScope, keepNonForm: true })
    })
    window.addEventListener('beforeunload', (e) => {
      if (this.submitting) {
        return
      }
      if (!this.preventUnload) {
        return
      }
      // If you prevent default behavior in Mozilla Firefox prompt will always be shown
      e.preventDefault()
      // Chrome requires returnValue to be set
      e.returnValue = this.i18n.sureCancel
      return e.returnValue
    })
    window.addEventListener('popstate', (e) => {
      if (!e.state) return
      if (e.state.step) {
        this.setStepNoHistory(e.state.step)
      } else {
        console.log('popstate, but no step')
      }
    })
  },
  methods: {
    submit() {
      this.fetchError = null
      this.submitting = true
      const form = document.forms.make_request
      const fd = new FormData(form)
      fetch(form.action, {
        method: 'POST',
        body: fd,
        headers: { 'x-requested-with': 'fetch' }
      })
        .then((resp) => {
          if (resp.ok) {
            if (resp.redirected && resp.url) {
              // success: purge & redirect
              this.purgeStorage({ scope: this.pbScope })
              document.location.href = resp.url
              return
            }
            console.error(resp)
            throw new Error('unexpected success response')
          }
          if (resp.status === 400) {
            // resp not ok, assume forms have errors...
            return resp.json()
          }
          console.error(resp)
          throw new Error(`${resp.status} ${resp.statusText}`)
        })
        .then((resp) => {
          // ...frontend will display/handle them
          this.fetchedForms = resp
        })
        .catch((e) => {
          console.error(e)
          this.fetchError = e.message || this.i18n.error
        })
        .finally(() => {
          this.submitting = false
        })
    },
    setFirstStep() {
      // this step may at this point be "remembered" from Storage
      // but this case is the "default"
      if (!this.step || this.step === this.steps[0]) {
        // if "editing draft" skip forward
        if (this.requestForm.fields.draft.initial) {
          console.log('request is draft, skipping intro etc.')
          this.setStep(STEPS.WRITE_REQUEST)
        } else if (this.hidePublicbodyChooser && !this.userInfo) {
          this.setStep(STEPS.LOGIN_CREATE)
        } else if (this.hasPublicBodies) {
          // skip directly to wrting
          // might theoretically also apply to "if state.subject || state.body"
          // but that combination seems unrealistic
          this.setStep(STEPS.WRITE_REQUEST)
        } else if (this.skipIntroHowtoPreference) {
          this.setStep(STEPS.SELECT_PUBLICBODY)
        }
      } else if (
        [STEPS.LOGIN_CREATE, STEPS.CREATE_ACCOUNT].includes(this.step) &&
        this.userInfo
      ) {
        // returning from login
        this.setStep(STEPS.WRITE_REQUEST)
      }
      // fall back to first viable (non-excluded) step
      if (!this.steps.includes(this.step)) {
        this.setStep(this.steps[0])
      }
    },
    stepperClick(stepperIndex) {
      this.setStep(this.stepperSteps[stepperIndex].stepId)
    },
    onlineHelpShow(urlOrContent) {
      this.$refs.onlineHelp.show(urlOrContent)
    },
    ...mapMutations({
      setStep: SET_STEP,
      setStepNoHistory: SET_STEP_NO_HISTORY,
      updateSubject: UPDATE_SUBJECT,
      updateBody: UPDATE_BODY,
      updateFullText: UPDATE_FULL_TEXT,
      cachePublicBodies: CACHE_PUBLICBODIES,
      updateRequestPublic: UPDATE_REQUEST_PUBLIC,
      updateTerms: UPDATE_TERMS
    }),
    ...mapActions([
      'getLawsForPublicBodies',
      'initStoreValues',
      'writeToStorage',
      'purgeStorage'
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

:deep(.campaign-logo) {
  max-height: 6em;
}
</style>
