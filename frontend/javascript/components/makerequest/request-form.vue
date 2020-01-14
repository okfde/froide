<template>
  <div>
    <slot name="request-legend-title"></slot>

    <div v-if="multiRequest && canBatchRequest && publicBodies.length > 1" class="publicbody-summary-container">
      <div class="publicbody-summary">
        <p>
          {{ i18n._('toMultiPublicBodies', {count: publicBodies.length}) }}
          <span v-if="!hidePublicbodyChooser">
            <a class="pb-change-link badge badge-pill badge-primary ml-3" :href="config.url.makeRequest" @click.prevent="$emit('setStepSelectPublicBody')">
              {{ i18n.change }}
            </a>
          </span>
        </p>
      </div>
    </div>
    <div v-if="multiRequest && !canBatchRequest" class="mb-5 mt-5">
      <p>{{ i18n._('toMultiPublicBodies', {count: publicBodies.length}) }}</p>
      <div class="publicbody-summary-list">
        <ul>
          <li v-for="pb in publicBodies" :key="pb.id">
            {{ pb.name }}
          </li>
        </ul>
      </div>
      <small>{{ i18n.batchRequestDraftOnly }}</small>
    </div>

    <div v-if="!multiRequest" class="publicbody-summary-container">
      <div class="row">
        <div class="col-lg-12 publicbody-summary">
          <p>
            {{ i18n._('toPublicBody', {name: publicBody.name}) }}
            <span v-if="!hidePublicbodyChooser">
              <a class="pb-change-link badge badge-pill badge-primary ml-3" :href="config.url.makeRequest" @click.prevent="$emit('setStepSelectPublicBody')">
                {{ i18n.change }}
              </a>
            </span>
          </p>
        </div>
      </div>
      <div class="row" v-if="hasLawNotes">
        <div class="col-lg-8">
          <div class="alert alert-warning" v-html="lawNotes">
          </div>
        </div>
      </div>
      <div class="row" v-if="hasPublicBodyNotes">
        <div class="col-lg-8">
          <div class="alert alert-warning" v-html="publicBodyNotes">
          </div>
        </div>
      </div>
    </div>

    <input v-for="pb in publicBodies" type="hidden" name="publicbody" :value="pb.id" :key="pb.id">
    <input type="hidden" name="law_type" :value="lawType">

    <div class="row">
      <div class="col-md-12">

        <div v-if="nonFieldErrors.length > 0" class="alert alert-danger">
          <p v-for="error in nonFieldErrors" :key="error">{{ error }}</p>
        </div>

        <div class="form-group">
          <label for="id_subject" :class="{ 'text-danger': errors.subject }">
            {{ i18n.subject }}
          </label>
          <div v-if="editingDisabled">
            <input type="hidden" name="subject" :value="subject"/>
            <strong>{{ subject }}</strong>
            <button @click.prevent="editingDisabled = false" class="btn btn-sm btn-white pull-right">
              <small class="d-none d-md-block">{{ i18n.reviewEdit }}</small>
              <small class="d-md-none fa fa-edit">
                <span class="sr-only">{{ i18n.reviewEdit }}</span>
              </small>
            </button>
          </div>
          <input v-else v-model="subject" type="text" name="subject" class="form-control" id="id_subject" :class="{ 'is-invalid': errors.subject }" :placeholder="formFields.subject.placeholder" @keydown.enter.prevent/>
        </div>
      </div>
    </div>

    <div class="card mb-3">
      <div class="card-body">
        <div v-if="fullText && warnFullText" class="alert alert-warning">
          <p>
            {{ i18n.warnFullText }}
          </p>
        </div>
        <div class="row">
          <div v-if="!editingDisabled" class="col-md-4 order-md-2">
            <transition name="saved-full-text">
              <div v-if="savedFullTextBody">
                <h6>
                  {{ i18n.savedFullTextChanges }}
                </h6>
                <textarea class="saved-body" v-model="savedFullTextBody" readonly></textarea>
              </div>
            </transition>
            <slot name="request-hints"></slot>
            <button v-if="fullTextDisabled" class="btn btn-light btn-sm" @click.prevent="resetFullText" >
              {{ i18n.resetFullText }}
            </button>
          </div>
          <div class="col-md-8 order-1">
            <div v-if="!fullText" class="body-text">{{ letterStart }}</div>
            <div v-if="editingDisabled" class="body-text body-text-em">{{ body }}</div>
            <textarea v-show="!editingDisabled" v-model="body" name="body" id="id_body" class="form-control body-textarea" :class="{ 'is-invalid': errors.body, 'attention': !hasBody }" :rows="bodyRows" @keyup="bodyChanged" :placeholder="formFields.body.placeholder"></textarea>
            <label class="small pull-right text-muted" v-if="allowFullText && !editingDisabled">
              <input type="checkbox" id="full_text_checkbox" name="full_text_checkbox" v-model="fullText" :disabled="fullTextDisabled">
              <i v-if="warnFullText" class="fa fa-exclamation-triangle" aria-hidden="true"></i>
              {{ formFields.full_text.label }}
            </label>
            <input type="hidden" name="full_text" v-model="fullText">
            <div v-if="!fullText" class="body-text"><template v-if="!fullLetter"><a class="show-full-letter" href="#" @click.prevent="showFullLetter">[&hellip;]</a>
{{ letterEndShort }}</template><template v-else>
{{ letterEnd }}</template></div>
            <div v-if="letterSignature" class="body-text"><em>{{ letterSignature }}</em></div>
            <div v-if="!letterSignature && fullText" class="body-text">{{ letterSignatureName }}</div>
          </div>
        </div>
        <div class="row" v-if="!hasUser">
          <div class="col-md-8">
            <div class="form-group row">
              <div class="col-sm-6" :class="{ 'text-danger': usererrors.first_name }">
                <label class="control-label field-required" for="id_first_name" :class="{ 'text-danger': usererrors.first_name }">
                  {{ i18n.yourFirstName }}
                </label>
                <input v-model="first_name" type="text" name="first_name" class="form-control" :class="{ 'is-invalid': usererrors.first_name }" id="id_first_name" :placeholder="userformFields.first_name.placeholder" required/>
                <p v-for="e in usererrors.first_name" :key="e.message">{{ e.message }}</p>
              </div>

              <div class="col-sm-6" :class="{ 'text-danger': usererrors.last_name }">
                <label class="control-label field-required" for="id_last_name" :class="{ 'text-danger': usererrors.last_name }">
                  {{ i18n.yourLastName }}
                </label>
                <input v-model="last_name" type="text" name="last_name" class="form-control" :class="{ 'is-invalid': usererrors.last_name }" id="id_last_name" :placeholder="userformFields.last_name.placeholder" required/>
                <p v-for="e in usererrors.last_name" :key="e.message">{{ e.message }}</p>
              </div>
            </div>
          </div>
          <div class="col-md-4 mt-md-4" v-if="usePseudonym">
            <small v-if="userformFields.last_name.help_text" v-html="userformFields.last_name.help_text"></small>
          </div>
        </div>

        <div class="row mt-2" v-if="config.settings.user_can_hide_web && !hasUser">
          <div class="col-md-8">
            <div class="checkbox">
              <label>
                <input id="id_private" v-model="userPrivate" type="checkbox" name="private" />
                {{ userformFields.private.label }}
              </label>
              <br/>
              <p class="help-block" v-html="userformFields.private.help_text">
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script>

import LetterMixin from './lib/letter-mixin'
import I18nMixin from '../../lib/i18n-mixin'

const MAX_BODY_ROWS = 10
const MIN_BODY_ROWS = 3

export default {
  name: 'request-form',
  props: {
    config: {
      type: Object
    },
    publicbodies: {
      type: Array,
      default: null
    },
    user: {
      type: Object,
      default: null
    },
    defaultLaw: {
      type: Object,
      default: null
    },
    requestForm: {
      type: Object
    },
    userForm: {
      type: Object
    },
    lawType: {
      type: String,
      default: ''
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
    multiRequest: {
      type: Boolean,
      default: false
    },
    usePseudonym: {
      type: Boolean,
      default: true
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
    initialFirstName: {
      type: String,
      default: ''
    },
    initialLastName: {
      type: String,
      default: ''
    }
  },
  mixins: [I18nMixin, LetterMixin],
  data () {
    return {
      bodyRows: MIN_BODY_ROWS,
      bodyBeforeChange: '',
      savedFullTextBody: '',
      fullTextDisabled: false,
      editingDisabled: this.hideEditing,
      fullLetter: false,
      subjectValue: this.initialSubject || '',
      bodyValue: this.initialBody || '',
      fullTextValue: this.initialFullText,
      firstNameValue: this.initialFirstName || (this.user && this.user.first_name) || '',
      lastNameValue: this.initialLastName || (this.user && this.user.last_name) || '',
      privateValue: this.initialPrivate || (this.user && this.user.private) || false,
    }
  },
  computed: {
    nonFieldErrors () {
      return this.form.nonFieldErrors
    },
    form () {
      return this.requestForm
    },
    formFields () {
      return this.form.fields
    },
    errors () {
      return this.form.errors
    },
    userformFields () {
      return this.userForm.fields
    },
    usererrors () {
      return this.userForm.errors
    },
    hasLawNotes () {
      if (this.defaultLaw) {
        return !!this.defaultLaw.request_note_html
      }
      // FIXME: find all notes of all public body default laws?
      return false
    },
    hasPublicBodyNotes () {
      if (this.publicBody) {
        return !!this.publicBody.request_note_html
      }
      // FIXME: find all notes of all public body default laws?
      return false
    },
    lawNotes () {
      if (this.hasLawNotes) {
        return this.defaultLaw.request_note_html
      }
      return ''
    },
    publicBodyNotes () {
      if (this.hasPublicBodyNotes) {
        return this.publicBody.request_note_html
      }
      return ''
    },
    canBatchRequest () {
      return this.config.settings.user_can_create_batch
    },
    hasUser () {
      return this.user && this.user.id
    },
    subject: {
      get () {
        return this.subjectValue
      },
      set (value) {
        this.subjectValue = value
        this.$emit('update:initialSubject', value)
      }
    },
    hasBody () {
      return this.body && this.body.length > 0
    },
    body: {
      get () {
        return this.bodyValue
      },
      set (value) {
        this.bodyValue = value
        this.$emit('update:initialBody', value)
      }
    },
    allowFullText () {
      return this.hasUser && !this.hideFullText
    },
    warnFullText () {
      return this.allowFullText && this.multipleLaws
    },
    multipleLaws () {
      return this.defaultLaw === null
    },
    fullText: {
      get () {
        return this.fullTextValue
      },
      set (value) {
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
        let newLineCount = (this.body.match(/\n/g) || []).length
        this.bodyRows = Math.max(MIN_BODY_ROWS, Math.min(newLineCount + 1, MAX_BODY_ROWS))
      }
    },
    first_name: {
      get () {
        return this.firstNameValue
      },
      set (value) {
        this.firstNameValue = value
        this.$emit('update:initialFirstName', value)
      }
    },
    last_name: {
      get () {
        return this.lastNameValue
      },
      set (value) {
        this.lastNameValue = value
        this.$emit('update:initialLastName', value)
      }
    },
    userPrivate: {
      get () {
        return this.privateValue
      },
      set (value) {
        this.privateValue = value
        this.$emit('update:initialPrivate', value)
      }
    },
    hasPublicBodies () {
      return this.publicBodies.length > 0
    },
    publicBody () {
      return this.publicbodies[0]
    },
    publicBodies () {
      // FIXME
      return this.publicbodies
    }
  },
  methods: {
    resetFullText () {
      this.savedFullTextBody = this.body
      this.fullTextDisabled = false
      this.fullText = false
    },
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
    showFullLetter () {
      this.fullLetter = true
    }
  }
}
</script>


<style lang="scss" scoped>

@import "../../../styles/variables";

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

.publicbody-summary-list {
  max-height: 5rem;
  border: 1px solid #aaa;
  overflow: auto;
}

.pb-change-link {
  font-weight: normal;
  font-size: $font-size-sm;
}

.body-text {
  hyphens: none;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: #999;
}

.body-text-em {
  color: #555;
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
