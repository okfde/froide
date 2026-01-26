<template>
  <div>
    <input
      v-for="pb in publicBodies"
      :key="pb.id"
      type="hidden"
      name="publicbody"
      :value="pb.id"
    />
    <input type="hidden" name="law_type" :value="lawType" />

    <div class="card mb-3">
      <div class="card-body">
        <div class="row mb-3" v-if="!hidePublicbodyChooser">
          <div class="col-sm-3 d-flex align-items-center">
            {{ i18n.recipientPb }}
          </div>
          <div class="col-sm-9 d-flex align-items-center">
            <strong v-if="publicBodies.length === 0" class="text-danger">{{
              i18n.none
            }}</strong>
            <strong v-else>{{
              publicBodies.map((pb) => pb.name).join(', ')
            }}</strong>
            <!-- setStep won't work in froide-campaign, but hidePublicbodyChooser always applies there;
              and Pb choosing is handled by <CampaignChoosePublicbody> -->
            <button
              type="button"
              class="btn btn-secondary btn-sm ms-auto text-nowrap"
              @click="setStepChangePublicbody"
            >
              {{ i18n.change }}
            </button>
          </div>
        </div>

        <div class="row mb-3">
          <div class="col-sm-3 d-flex align-items-center">
            <label
              class="form-check-label"
              for="id_subject"
              :class="{
                'text-danger': errors.subject && !subjectChanged
              }"
            >
              {{ i18n.subject }}:
            </label>
          </div>
          <div class="col-sm-9 d-flex flex-wrap align-items-center">
            <template
              v-if="
                editingDisabled &&
                !(errors.subject && errors.subject.length > 0)
              "
            >
              <!-- editingDisabled e.g. when ?hide_editing=1 -->
              <input type="hidden" name="subject" :value="subject" />
              <strong>{{ subject }}</strong>
              <button
                type="button"
                class="btn btn-secondary btn-sm ms-auto text-nowrap"
                @click="enableEditing"
              >
                {{ i18n.reviewEdit }}
              </button>
            </template>
            <template v-else>
              <div
                v-if="
                  !clearFormErrors &&
                  errors.subject &&
                  errors.subject.length > 0
                "
                class="alert my-2 w-100"
                :class="{
                  'alert-danger': !subjectChanged,
                  'alert-warning': subjectChanged
                }"
              >
                <ul class="list-unstyled my-0">
                  <li v-for="error in errors.subject" :key="error.message">
                    {{ error.message }}
                  </li>
                </ul>
              </div>
              <div
                v-else-if="subjectValidationErrors.length > 0"
                class="alert my-2 w-100"
                :class="{
                  'alert-danger': !subjectChanged,
                  'alert-warning': subjectChanged
                }"
              >
                <ul class="list-unstyled my-0">
                  <li v-for="error in subjectValidationErrors" :key="error">
                    {{ error }}
                  </li>
                </ul>
              </div>
              <input
                v-model="subject"
                ref="subject"
                id="id_subject"
                type="text"
                name="subject"
                class="form-control"
                :minlength="formFields.subject.min_length"
                :maxlength="formFields.subject.max_length"
                :class="{
                  'is-invalid':
                    (errors.subject || subjectValid === false) &&
                    !subjectChanged
                }"
                :placeholder="formFields.subject.placeholder"
                @change="updateSubjectChanged(true)"
                @keyup="resetSubjectCustomValidity"
                @keydown.enter.prevent
              />
            </template>
          </div>
        </div>

        <div v-if="fullText && warnFullText" class="alert alert-warning">
          <p>
            {{ i18n.warnFullText }}
          </p>
        </div>

        <div
          v-if="!clearFormErrors && errors.body && errors.body.length > 0"
          class="alert mb-2"
          :class="{
            'alert-danger': !bodyChanged,
            'alert-warning': bodyChanged
          }"
        >
          <ul class="list-unstyled my-0">
            <li v-for="error in errors.body" :key="error.message">
              {{ error.message }}
            </li>
          </ul>
          <div v-if="showPlaceholderReplacer">
            <button
              type="button"
              class="btn btn-secondary"
              @click="fixBodyPlaceholders"
            >
              {{ i18n.fixPlaceholder }}
            </button>
          </div>
        </div>
        <div
          v-else-if="bodyValidationErrors.length > 0"
          class="alert mt-2"
          :class="{
            'alert-danger': !bodyChanged,
            'alert-warning': bodyChanged
          }"
        >
          <ul class="list-unstyled my-0">
            <li v-for="error in bodyValidationErrors" :key="error">
              {{ error }}
            </li>
          </ul>
          <div v-if="showPlaceholderReplacer" class="mt-2">
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              @click="fixBodyPlaceholders"
            >
              {{ i18n.fixPlaceholder }}
            </button>
          </div>
        </div>

        <div class="row">
          <div
            :class="
              savedFullTextBody && savedFullTextBodySidebyside
                ? 'col-md-8 order-md-1'
                : 'col'
            "
          >
            <div class="mb-4">
              <label for="id_body"> {{ i18n.requestBody }}: </label>
            </div>
            <div v-if="!fullText" class="body-text" v-text="letterStart" />
            <div
              v-if="editingDisabled"
              class="body-text-em mb-3"
              v-text="body"
            />
            <textarea
              v-show="!editingDisabled"
              v-model="body"
              ref="body"
              id="id_body"
              name="body"
              required
              class="form-control body-textarea"
              :class="{
                'is-invalid':
                  (errors.body || bodyValid === false) && !bodyChanged,
                attention: !hasBody
              }"
              :rows="bodyRows"
              :placeholder="formFields.body.placeholder"
              :minlength="formFields.body.min_length"
              :maxlength="formFields.body.max_length"
              @keydown="updateBody"
              @keyup="resetBodyCustomValidity"
              @change="updateBodyChanged(true)"
            />

            <div class="bg-secondary-subtle px-2 py-1 mb-4 mt-1 border">
              <div class="d-flex justify-content-end gap-2">
                <div class="form-check">
                  <input
                    v-if="!fullText"
                    id="full_letter_checkbox"
                    type="checkbox"
                    class="form-check-input"
                    v-model="fullLetter"
                  />
                  <input
                    v-else
                    id="full_letter_checkbox"
                    type="checkbox"
                    class="form-check-input"
                    disabled
                    :checked="true"
                  />
                  <label class="form-check-label" for="full_letter_checkbox"
                    >Gesamten Nachrichtentext anzeigen</label
                  >
                </div>
                <input v-model="fullText" type="hidden" name="full_text" />
                <div
                  v-if="allowFullText && !editingDisabled"
                  class="form-check"
                >
                  <input
                    id="full_text_checkbox"
                    class="form-check-input"
                    v-model="fullText"
                    type="checkbox"
                    name="full_text_checkbox"
                    :disabled="fullTextDisabled"
                  />
                  <label for="full_text_checkbox" class="form-check-label">
                    <i
                      v-if="warnFullText"
                      class="fa fa-exclamation-triangle"
                      aria-hidden="true"
                    />
                    {{ formFields.full_text.label }}
                  </label>
                </div>
              </div>
              <div
                class="d-flex justify-content-end mt-2"
                v-if="fullTextDisabled"
              >
                <button
                  class="btn btn-outline-secondary btn-sm"
                  @click.prevent="resetFullText"
                >
                  {{ i18n.resetFullText }}
                </button>
              </div>
              <details
                v-if="savedFullTextBody && !savedFullTextBodySidebyside"
                class="text-end mt-2"
              >
                <summary>
                  {{ i18n.savedFullTextChanges }}
                </summary>
                <textarea
                  v-model="savedFullTextBody"
                  class="saved-body"
                  readonly
                />
              </details>
            </div>

            <div v-if="!fullText && !fullLetter" class="body-text">
              […]<br />{{ letterEndShort }}
            </div>

            <div v-if="!fullText && fullLetter" class="body-text">
              {{ letterEnd }}
            </div>

            <div v-if="letterSignature" class="body-text">
              <em>{{ letterSignature }}</em>
            </div>
            <div
              v-if="!letterSignature && fullText"
              class="body-text"
              v-text="letterSignatureName"
            />
            <div v-if="needles.length > 0" class="alert alert-warning mb-2">
              <ul class="list-unstyled my-0">
                <li v-for="needle in needles" :key="needle">
                  {{ needle }}
                </li>
              </ul>
            </div>
          </div>
          <div
            v-if="savedFullTextBody && savedFullTextBodySidebyside"
            class="col-md-4 order-md-2"
          >
            <h6>
              {{ i18n.savedFullTextChanges }}
            </h6>
            <textarea v-model="savedFullTextBody" class="saved-body" readonly />
          </div>
        </div>
      </div>
    </div>

    <div v-if="hasUser && proofForm" class="card mb-3">
      <div class="card-body">
        <template v-if="proofRequired">
          <h5>{{ i18n.includeProof }}</h5>
          <ProofForm
            :form="proofForm"
            :required="proofRequired"
            :config="config.proof_config"
          ></ProofForm>
        </template>
        <details v-else>
          <summary>{{ i18n.includeProof }}</summary>
          <ProofForm
            :form="proofForm"
            :required="proofRequired"
            :config="config.proof_config"
          ></ProofForm>
        </details>
      </div>
    </div>

    <div v-if="hasUser" class="card mb-3">
      <div class="card-body">
        <details
          :open="
            userForm?.errors?.address ||
            addressValid === false ||
            addressChanged === true ||
            user?.address === ''
          "
        >
          <summary>{{ i18n.updatePostalAddress }}</summary>
          <UserAddress
            :i18n="i18n"
            :form="userForm"
            :config="config"
            :address-help-text="userForm.fields.address.help_text"
            :default-law="defaultLaw"
            class="mt-3"
          />
        </details>
      </div>
    </div>

    <UserConfirm
      v-if="hasUserConfirmContent && confirmRequired"
      ref="userConfirm"
    >
      <slot name="request-user-confirm" />
    </UserConfirm>

    <div class="my-4" v-if="showNextButton">
      <button
        type="button"
        class="btn btn-primary"
        @click="validateAllNextStep"
      >
        {{ i18n.stepNext }}
      </button>
    </div>
  </div>
</template>

<script>
import LetterMixin from './lib/letter-mixin'
import I18nMixin from '../../lib/i18n-mixin'

import { mapGetters, mapMutations } from 'vuex'

import {
  UPDATE_BODY_VALIDITY,
  UPDATE_BODY_CHANGED,
  UPDATE_SUBJECT_VALIDITY,
  UPDATE_SUBJECT_CHANGED,
  SET_STEP,
  STEPS
} from '../../store/mutation_types'

import ProofForm from '../proofupload/proof-form.vue'
import UserAddress from './user-address.vue'
import UserConfirm from './user-confirm.vue'

function erx(text) {
  return text.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&')
}

const PLACEHOLDER_MARKER = '…'
const PLACEHOLDER_REPLACEMENT = '...'
const MAX_BODY_ROWS = 12
const MIN_BODY_ROWS = 3

// show savedFullTextBody next to the textarea (true), or below in <details> in the "tool bar" (false)
const savedFullTextBodySidebyside = false

export default {
  name: 'RequestForm',
  mixins: [I18nMixin, LetterMixin],
  components: {
    ProofForm,
    UserAddress,
    UserConfirm
  },
  emits: ['stepNext', 'enableEditing'],
  props: {
    config: {
      type: Object,
      default: null
    },
    publicbodies: {
      type: Array,
      default: null
    },
    user: {
      type: Object,
      default: null
    },
    requestForm: {
      required: true,
      type: Object
    },
    userForm: {
      required: true,
      type: Object
    },
    proofForm: {
      type: Object,
      default: null
    },
    lawType: {
      type: String,
      default: ''
    },
    defaultLaw: {
      type: Object,
      default: null
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
      default: true
    },
    hideEditing: {
      type: Boolean,
      default: false
    },
    showNextButton: {
      type: Boolean,
      default: false
    },
    initialSubject: {
      type: String,
      default: ''
    },
    initialBody: {
      type: String,
      default: ''
    },
    initialFullText: {
      type: Boolean,
      default: false
    },
    proofRequired: {
      type: Boolean,
      default: false
    },
    confirmRequired: {
      type: Boolean,
      default: false
    },
    submitting: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      bodyRows: MIN_BODY_ROWS,
      bodyBeforeChange: '',
      bodyValidationErrors: [],
      subjectValidationErrors: [],
      savedFullTextBody: '',
      savedFullTextBodySidebyside,
      fullTextDisabled: false,
      editingDisabled: this.hideEditing,
      fullLetter: false,
      subjectValue: this.initialSubject || '',
      bodyValue: this.initialBody || '',
      fullTextValue: this.initialFullText,
      clearFormErrors: false,
      showPlaceholderReplacer: false
    }
  },
  computed: {
    formFields() {
      return this.requestForm.fields
    },
    errors() {
      return this.requestForm.errors
    },
    userformFields() {
      return this.userForm.fields
    },
    nonMeaningfulSubjects() {
      return this.config.settings.non_meaningful_subject_regex.map(
        (x) => new RegExp(x, 'i')
      )
    },
    hasUser() {
      return this.user && this.user.id
    },
    subject: {
      get() {
        return this.subjectValue
      },
      set(value) {
        this.subjectValue = value
        this.$emit('update:initialSubject', value)
      }
    },
    hasBody() {
      return this.body && this.body.length > 0
    },
    body: {
      get() {
        return this.bodyValue
      },
      set(value) {
        this.bodyValue = value
        this.$emit('update:initialBody', value)
      }
    },
    allowFullText() {
      return this.hasUser && !this.hideFullText
    },
    warnFullText() {
      return this.allowFullText && this.multipleLaws
    },
    multipleLaws() {
      return this.defaultLaw === null
    },
    fullText: {
      get() {
        return this.fullTextValue
      },
      set(value) {
        this.fullTextValue = value
        this.$emit('update:initialFullText', value)
        if (value) {
          this.bodyBeforeChange = this.body
          this.body = `${this.letterStart}\n${this.body}\n\n${this.letterEndNoName}`
        } else {
          if (!this.fullTextDisabled) {
            this.body = this.bodyBeforeChange
          }
        }
        const newLineCount = (this.body.match(/\n/g) || []).length
        this.bodyRows = Math.max(
          MIN_BODY_ROWS,
          Math.min(newLineCount + 1, MAX_BODY_ROWS)
        )
      }
    },
    hasPublicBodies() {
      return this.publicBodies.length > 0
    },
    publicBody() {
      return this.publicbodies[0]
    },
    publicBodies() {
      // FIXME
      return this.publicbodies
    },
    needles() {
      let checks = []
      const positives = []
      if (!this.fullText) {
        checks = [
          ...checks,
          [
            new RegExp(erx(this.i18n.greeting), 'gi'),
            this.i18n.dontAddGreeting
          ],
          [
            new RegExp(erx(this.i18n.kindRegards), 'gi'),
            this.i18n.dontAddClosing
          ]
        ]
      }
      if (this.userRegex) {
        checks.push([this.userRegex, this.i18n.dontInsertName])
      }
      checks.forEach((params) => {
        if (params[0].test(this.body)) {
          positives.push(params[1])
        }
      })
      return positives
    },
    userRegex() {
      const regex = []
      if (!this.user) return null
      if (this.user.first_name && this.user.last_name) {
        regex.push(erx(`${this.user.first_name} ${this.user.last_name}`))
      }
      if (this.user.first_name) {
        regex.push(erx(this.user.first_name))
      }
      if (this.user.first_name) {
        regex.push(erx(this.user.first_name))
      }
      if (regex.length === 0) {
        return null
      }
      return new RegExp(`\\b${regex.join('\\b|\\b')}\\b`, 'gi')
    },
    hasUserConfirmContent() {
      if (!this.$parent['django-slots']) return false
      return (
        this.$parent['django-slots'][
          'request-user-confirm'
        ].textContent.trim() !== ''
      )
    },
    ...mapGetters([
      'subjectValid',
      'subjectChanged',
      'bodyValid',
      'bodyChanged',
      'confirmValid',
      'addressValid',
      'addressChanged'
    ])
  },
  mounted() {
    this.updateBody()
  },
  methods: {
    resetFullText() {
      this.savedFullTextBody = this.body
      this.fullTextDisabled = false
      this.fullText = false
    },
    updateBody() {
      if (this.fullText) {
        this.fullTextDisabled = true
      }
      const ta = this.$refs.body
      while (ta.scrollHeight > ta.clientHeight && ta.rows < MAX_BODY_ROWS) {
        ta.style.overflow = 'hidden'
        ta.rows += 1
      }
      if (ta.scrollHeight > ta.clientHeight) {
        ta.style.overflow = 'auto'
      }
      this.bodyRows = ta.rows
    },
    fixBodyPlaceholders() {
      this.body = this.body.replaceAll(
        PLACEHOLDER_MARKER,
        PLACEHOLDER_REPLACEMENT
      )
      this.validateBody()
    },
    enableEditing() {
      this.editingDisabled = false
      this.$emit('enableEditing')
    },
    showFullLetter() {
      this.fullLetter = true
    },
    validateSubject() {
      this.subjectValidationErrors = []
      let valid = true
      if (this.nonMeaningfulSubjects.some((re) => re.test(this.subject))) {
        this.subjectValidationErrors.push(this.i18n.subjectMeaningful)
        this.$refs.subject.setCustomValidity(this.i18n.subjectMeaningful)
        valid = false
      }
      // from model via form_utils
      const minLength = this.$refs.subject.minLength
      const checkValidity = this.$refs.subject.checkValidity()
      // unfortunately checkValidity is not enough, it won't kick in until a user interaction
      // there is a workaround with pattern=".{min,max}" but it still won't work for textarea,
      // so let's keep it consistent. cf. https://stackoverflow.com/a/10294291/629238 */
      if (!checkValidity || this.subject.length < minLength) {
        valid = false
        const minLengthMessage = this.i18n._('valueMinLength', {
          count: minLength
        })
        if (checkValidity) {
          // if browser wrong, force our message
          this.$refs.subject.setCustomValidity(minLengthMessage)
        } else {
          // let browser's native message take over
          this.resetSubjectCustomValidity()
        }
        if (this.subject.length < minLength) {
          this.subjectValidationErrors.push(minLengthMessage)
        }
      }
      if (!valid) {
        // note: reportValidity might only work from a click, but not keyboard event?
        this.$refs.subject.reportValidity()
      }
      this.updateSubjectValidity(valid)
    },
    resetSubjectCustomValidity() {
      this.$refs.subject.setCustomValidity('')
    },
    validateBody() {
      this.bodyValidationErrors = []
      let valid = true
      this.showPlaceholderReplacer = false
      if (this.body.includes(PLACEHOLDER_MARKER)) {
        const placeholderMessage = this.i18n._('containsPlaceholderMarker', {
          placeholder: PLACEHOLDER_MARKER
        })
        this.bodyValidationErrors.push(placeholderMessage)
        this.showPlaceholderReplacer = true
        this.$refs.body.setCustomValidity(placeholderMessage)
        valid = false
      }
      // see validateSubject above for comments, esp. re: textarea
      const minLength = this.$refs.body.minLength
      const checkValidity = this.$refs.body.checkValidity()
      if (!checkValidity || this.body.length < minLength) {
        valid = false
        const minLengthMessage = this.i18n._('valueMinLength', {
          count: minLength
        })
        if (checkValidity) {
          this.$refs.body.setCustomValidity(minLengthMessage)
        } else {
          this.resetBodyCustomValidity()
        }
        if (this.body.length < minLength) {
          this.bodyValidationErrors.push(minLengthMessage)
        }
      }
      if (!valid) {
        this.$refs.body.reportValidity()
      }
      this.updateBodyValidity(valid)
    },
    resetBodyCustomValidity() {
      this.$refs.body.setCustomValidity('')
    },
    validateConfirm() {
      this.$refs.userConfirm.validate()
    },
    validateAllNextStep() {
      this.clearFormErrors = true
      if (!this.editingDisabled) {
        // only one reportValidity will be visible, but the order/precedence seems a bit unpredictable
        this.validateBody()
        this.validateSubject()
      }
      const editingPassed =
        (this.bodyValid && this.subjectValid) || this.editingDisabled
      if (this.hasUserConfirmContent && this.confirmRequired)
        this.validateConfirm()
      const confirmPassed =
        this.confirmValid ||
        !this.confirmRequired ||
        !this.hasUserConfirmContent
      if (editingPassed && confirmPassed) {
        this.$emit('stepNext')
      }
    },
    setStepChangePublicbody() {
      this.setStep(STEPS.SELECT_PUBLICBODY)
    },
    ...mapMutations({
      setStep: SET_STEP,
      updateBodyValidity: UPDATE_BODY_VALIDITY,
      updateBodyChanged: UPDATE_BODY_CHANGED,
      updateSubjectValidity: UPDATE_SUBJECT_VALIDITY,
      updateSubjectChanged: UPDATE_SUBJECT_CHANGED
    })
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

.publicbody-summary-list {
  max-height: 5rem;
  border: 1px solid #aaa;
  overflow: auto;
}

.pb-change-link {
  font-weight: normal;
  font-size: $font-size-sm;
}

.body-text,
.body-text-em {
  hyphens: none;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: #666;
}

.body-text-em {
  color: #222;
}

.body-textarea {
  width: 100%;
}

.body-textarea {
  padding-left: 0;
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
