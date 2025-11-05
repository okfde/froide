<template>
  <div class="make-request-container">

    <SimpleStepper
      class="bg-body-tertiary"
      :step="stepperStepCurrent"
      :steps="stepperSteps.map(step => step.label)"
      clickable
      keep-visited-clickable
      @step-click="stepperClick"
      >
      {{ i18n.step }}
      <!-- avoid 0 -->
      <strong>{{ this.stepperStepCurrent + 1 }}/{{ this.stepperSteps.length }}</strong>:
      {{ this.stepperSteps[this.stepperStepCurrent].label }}
    </SimpleStepper>

    <div class="container"><div class="row"><div class="col x-col-lg-9">

      <div
        class="my-2"
        v-show="step === STEPS.PREVIEW_SUBMIT"
        >
        <DjangoSlot
          name="messages"
          />
      </div>

      <div class="row justify-content-lg-center">
        <div class="col-lg-12">
          <div
            v-if="stepBack"
            class="my-3 d-flex justify-content-between"
            >
            <a class="btn btn-link text-decoration-none ps-0"
              :href="'#step-' + stepBack"
              @click="setStep(stepBack)"
              >← <u>{{ i18n.back }}</u></a>
            <button
              v-show="true"
              type="button"
              class="btn btn-primary"
              :disabled="!stepCanContinue(pbScope)"
              @click="setStep(stepNext)"
              >
              {{ i18n.stepNext }}
            </button>
          </div>

          <!-- keep visible for all steps -->
          <div v-if="requestForm.nonFieldErrors.length > 0" class="alert alert-danger">
            <p v-for="error in requestForm.nonFieldErrors" :key="error" v-html="error" />
          </div>

          <h1
            v-if="hidePublicbodyChooser && hasPublicBodies"
            class="my-3 fs-5"
            >
            Anfrage an:<!-- TODO i18n -->
            {{ publicBodies.map(pb => pb.name).join(', ') }}
          </h1>

          <!-- STEP: INTRO / CAMPAIGNS -->

          <div v-if="step === STEPS.INTRO" class="mt-5">
            <h1>{{ i18n.makeRequest }}</h1>
            <p>{{ i18n.whatDoYouWantToDo }}</p>
            <IntroCampaigns
              :config="config"
              @onlinehelp-click="$refs.onlineHelp.show($event)"
              @step-next="setStep(stepNext)"
              >
              <DjangoSlot name="campaigns"></DjangoSlot>
            </IntroCampaigns>
          </div>

          <!-- STEP: INTRO / HOWTO -->

          <!-- TODO mt-5 might have no effect here -->
          <IntroHowto
            v-if="step === STEPS.INTRO_HOWTO"
            class="mt-5"
            :config="config"
            >
            <DjangoSlot name="intro_howto" />
          </IntroHowto>

          <!-- STEP: FIND SIMILAR REQUESTS -->

          <div v-if="step === STEPS.FIND_SIMILAR">

            <h2>Ähnliche Anfragen finden</h2><!-- TODO i18n -->

            <SimilarRequestSearch />

            <div>
              <button
                type="button"
                class="btn btn-primary"
                @click="setStep(stepNext)"
                >
                {{ i18n.stepNext }}
              </button>
            </div>

          </div>

          <!-- STEP: SELECT PUBLIC BODY -->

          <div v-if="step === STEPS.SELECT_PUBLICBODY">

            <p>
              Aktuell ausgewählt:<!-- TODO i18n -->
              {{ publicBodies.map(pb => pb.name).join(', ') }}
            </p>

            <div v-if="multiRequest && tmpMulti">
              <!-- PublicBodyChoosers advance step by mutations like SET_STEP_REQUEST (mapped to setStepRequest) -->
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
                      :config="config"
                      @step-next="setStep(stepNext)"
                      />
                  </template>
                  <template v-else>
                    <PublicbodyChooser
                      name="publicbody"
                      :defaultsearch="publicBodySearch"
                      :scope="pbScope"
                      :form="publicbodyForm"
                      :config="config"
                      :list-view="publicBodyListView"
                      />
                  </template>
                </div>
                <div class="col-lg-4 small">
                  <DjangoSlot name="publicbody-missing" />
                </div>
              </div>
            </div>
          </div>

          <!-- STEP: REVIEW PUBLIC BODIES -->

          <div v-if="step === STEPS.REVIEW_PUBLICBODY">
            <PbMultiReview
              name="publicbody"
              :i18n="i18n"
              :scope="pbScope"
              @step-next="setStep(stepNext)"
              />
          </div>

          <!-- STEP: CREATE ACCOUNT -->

          <!-- need v-show over v-if so <input>s are in DOM while submitting -->
          <div
            v-show="step === STEPS.CREATE_ACCOUNT">
            <UserCreateAccount
              v-if="!user.id"
              :config="config"
              :user="user"
              :request-form="requestForm"
              :user-form="userForm"
              :default-law="defaultLaw"
              @step-next="setStep(stepNext)"
              @onlinehelp-click="$refs.onlineHelp.show($event)"
              >
              <template #loginlink>
                <DjangoSlot name="loginlink"></DjangoSlot>
              </template>
            </UserCreateAccount>
          </div>

          <!-- STEP: WRITE REQUEST -->

          <div
            v-show="step === STEPS.WRITE_REQUEST"
            id="step-request"
            class="mt-3"
            >
            <!-- TODO: rename/emphasize ellipsis button -->
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
              @step-next="setStep(stepNext)"
              @step-back="setStep(stepBack)"
              >
              <template #request-hints>
                <!-- has-bs-directives for onlinehelp links -->
                <DjangoSlot
                  name="request-hints"
                  has-bs-directives
                  @onlinehelp-click="$refs.onlineHelp.show($event)"
                  />
              </template>
              <template #request-legend-title>
                <DjangoSlot name="request-legend-title" />
              </template>
            </RequestForm>
            <SimilarRequests
              v-if="showSimilar"
              :publicbodies="publicBodies"
              :subject="subject"
              :config="config" />
          </div>

          <!-- STEP: VISIBILITY -->

          <div v-show="step == STEPS.REQUEST_PUBLIC">
            <h2>Sichtbarkeit der Anfrage</h2><!-- TODO i18n -->
            <!-- TODO i18n -->
            <p>Ihre Anfrage ist für alle auf dieser Website sichtbar.
              Denn Sie tragen mit Ihrer Anfrage zu einem öffentlichen Archiv amtlicher Informationen bei und sorgen so mit einer wachsenden Community für Transparenz in Politik und Verwaltung.</p>
            <p>Auf Wunsch können Sie Ihre Anfrage aber erst später öffentlich machen, z.B. nach Veröffentlichung Ihrer investigativen Recherche.</p>
            <RequestPublic
              :form="requestForm"
              :hide-public="hidePublic"
              v-model:initial-public="requestPublic"
              />
            <p>Gut zu wissen: Ob Ihr Name im Klartext erscheinen soll, können Sie im nächsten Schritt auswählen –das ist unabhängig von Ihrer Entscheidung hier.</p>
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

          <div v-if="step === STEPS.PREVIEW_SUBMIT">
            <h2>Vorschau &amp; Abschicken</h2><!-- TODO i18n -->
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
              @submit="submitting = true"
              @onlinehelp-click="$refs.onlineHelp.show($event)"
              />
          </div>
        </div>
      </div>
    </div></div></div> <!-- /.container -->
    <OnlineHelp ref="onlineHelp" :i18n="i18n"></OnlineHelp>
  </div>
</template>

<script>
import SimilarRequests from './similar-requests'
import SimilarRequestSearch from './similar-request-search'
import PublicbodyChooser from '../publicbody/publicbody-chooser'
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
  UPDATE_SIMILAR_REQUEST_SEARCH,
  UPDATE_LAW_TYPE,
  UPDATE_TERMS,
  SET_CONFIG,
  STEPS,
  UPDATE_CONFIRM,
} from '../../store/mutation_types'

import LetterMixin from './lib/letter-mixin'
import I18nMixin from '../../lib/i18n-mixin'
import UserCreateAccount from './user-create-account.vue'
import IntroHowto from './intro-howto.vue'
import IntroCampaigns from './intro-campaigns.vue'

export default {
  name: 'RequestPage',
  components: {
    IntroHowto,
    IntroCampaigns,
    PublicbodyChooser,
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
        // TODO: when hidePbChoo maybe hide INTRO, and maybe swap ACCOUNT & WRITE_REQ?
        //   or when campaigns slot is empty -- depends what other intro contents there will be
        STEPS.INTRO,
        ...(this.config.settings.skip_intro_howto ? [] : [STEPS.INTRO_HOWTO]),
        ...(this.showSimilar ? [STEPS.FIND_SIMILAR] : []),
        ...(this.hidePublicbodyChooser ? [] : [STEPS.SELECT_PUBLICBODY]),
        ...(this.hidePublicbodyChooser ? [] : (this.multiRequest ? [STEPS.REVIEW_PUBLICBODY] : [])),
        ...(this.userInfo ? [] : [STEPS.CREATE_ACCOUNT]),
        STEPS.WRITE_REQUEST,
        ...(this.hidePublic ? [] : [STEPS.REQUEST_PUBLIC]),
        STEPS.PREVIEW_SUBMIT,
        STEPS.OUTRO
      ]
    },
    stepLabels() {
      return {
        [STEPS.INTRO]: this.i18n.introduction,
        [STEPS.INTRO_HOWTO]: this.i18n.introduction,
        [STEPS.FIND_SIMILAR]: this.i18n.similarRequests,
        [STEPS.SELECT_PUBLICBODY]: this.i18n.choosePublicBody,
        [STEPS.REVIEW_PUBLICBODY]: this.i18n.choosePublicBody,
        [STEPS.CREATE_ACCOUNT]: this.i18n.account,
        [STEPS.WRITE_REQUEST]: this.i18n.writeMessage,
        [STEPS.REQUEST_PUBLIC]: this.i18n.writeMessage,
        [STEPS.PREVIEW_SUBMIT]: this.i18n.submitRequest,
        [STEPS.OUTRO]: this.i18n.submitRequest,
      }
    },
    stepperSteps() {
      const remap = {
        // "display INTRO_HOWTO as INTRO"
        [STEPS.INTRO]: STEPS.INTRO_HOWTO,
        [STEPS.SELECT_PUBLICBODY]: STEPS.REVIEW_PUBLICBODY,
        [STEPS.WRITE_REQUEST]: STEPS.REQUEST_PUBLIC,
        [STEPS.PREVIEW_SUBMIT]: STEPS.OUTRO
      }
      return this.steps
        .filter(stepId => !(Object.values(remap).includes(stepId)))
        .map(stepId => ({
          stepId,
          altStepId: remap[stepId],
          label: this.stepLabels[stepId]
        }))
    },
    stepperStepCurrent() {
      return this.stepperSteps.findIndex(_ => _.stepId === this.step || _.altStepId === this.step)
    },
    stepIndex() {
      return this.steps.findIndex(_ => _ === this.step)
    },
    stepBack() {
      if (this.stepIndex <= 0) return false
      return this.steps[this.stepIndex - 1]
    },
    stepNext() {
      if (this.stepIndex === -1 || this.stepIndex > this.steps.length - 1) return false
      return this.steps[this.stepIndex + 1]
    },
    showTopNext() {
      return [STEPS.FIND_SIMILAR].includes(this.step)
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

    this.setFirstStep()

    // init "regular form values" from storage if not POSTed
    // (not form-submitted, but refreshed, or returned from login)
    // in the case of "preset by GET", e.g. ?subject=foo
    // we still preferStorage to allow changes (of the presets) to persist
    // -- within the session. In the (unlikely) case of "session reuse"
    // (e.g. abandon draft, open the page with different GETs in the same tab)
    // this could lead to the GET parameters be ignored. 
    // This could be prevented by tying the storage stronger to the request;
    // initStoreValues would need to do
    // persistKeyPrefix+(document.location.pathname+document.location.search)
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
          confirm: UPDATE_CONFIRM,
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

    this.initStoreValues({
      scope: this.pbScope,
      preferStorage: true,
      mutationMap: {
        similarRequestSearch: UPDATE_SIMILAR_REQUEST_SEARCH
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
      if (this.step !== STEPS.WRITE_REQUEST) {
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
    setFirstStep() {
      /* this step may at this point be "remembered" from Storage,
         but will default to STEPS.INTRO */
      // if "editing draft" skip forward 
      if (this.requestForm.fields.draft.initial && this.step === STEPS.INTRO) {
        console.log('request is draft, skipping intro etc.')
        this.setStep(STEPS.WRITE_REQUEST)
      } else if (this.hidePublicbodyChooser && this.step === STEPS.INTRO && !this.userInfo) {
        this.setStep(STEPS.CREATE_ACCOUNT)
      } else if (this.hasPublicBodies && this.step === STEPS.INTRO) {
        // skip intros
        this.setStep(STEPS.FIND_SIMILAR)
      } else if (this.step === STEPS.INTRO_HOWTO && this.config.settings.skip_intro_howto) {
        // skip intro
        this.setStep(this.stepNext)
      } else if (this.step === STEPS.CREATE_ACCOUNT && this.userInfo) {
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
    ...mapMutations({
      setStep: SET_STEP,
      setStepNoHistory: SET_STEP_NO_HISTORY,
      updateSubject: UPDATE_SUBJECT,
      updateBody: UPDATE_BODY,
      updateFullText: UPDATE_FULL_TEXT,
      setConfig: SET_CONFIG,
      setUser: SET_USER,
      updateLawType: UPDATE_LAW_TYPE,
      setPublicBody: SET_PUBLICBODY,
      setPublicBodies: SET_PUBLICBODIES,
      cachePublicBodies: CACHE_PUBLICBODIES,
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
