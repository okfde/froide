<template>
  <div>
    <ReviewRequestLine
      :i18n="i18n"
      :title="i18n.publicBody || '§Behörde'"
      :invalid="needCorrectionPublicbody"
      :step="hidePublicbodyChooser ? '' : STEPS.SELECT_PUBLICBODY"
      >
      <template #contents>
        <ReviewPublicbody
          :config="config"
          :pb-scope="pbScope"
          :multi-request="multiRequest"
          />
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      :i18n="i18n"
      :title="i18n.subject"
      :invalid="needCorrectionSubject"
      :step="STEPS.WRITE_REQUEST"
      :contents="subject || i18n.subject"
      />
    
    <ReviewRequestLine
      :i18n="i18n"
      :title="'§Anfragentext'"
      :invalid="needCorrectionText"
      :step="STEPS.WRITE_REQUEST"
      >
      <template #contents>
        <div>
          <div v-if="fullText">
            <div class="body-text review-body-text">
              <span v-text="body" />
              <span v-text="letterSignatureName" />
            </div>
          </div>
          <div v-else>
            <div class="body-text review-body-text">
              <span>{{ letterStart }}</span>
              <span class="highlight"><br />{{ body }}</span>
              <span><br /><br />{{ letterEnd }}</span>
            </div>
          </div>
        </div>
        <ul class="review-hints">
          <li>{{ i18n.reviewSpelling }}</li>
          <li>{{ i18n.reviewPoliteness }}</li>
          <li v-for="error in errors" :key="error" class="error">
            {{ error }}
          </li>
        </ul>
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      :i18n="i18n"
      :title="i18n.visibility || '§Sichtbarkeit'"
      :step="STEPS.REQUEST_PUBLIC"
      >
      <template #contents>
        {{ requestPublic
          ? '§Anfrage sofort veröffentlichen'
          : '§Anfrage zunächst nicht veröffentlichen'
        }}
        <a
          :href="config.url.helpRequestPublic"
          @click.prevent="$emit('online-help', config.url.helpRequestPublic)"
          >{{ i18n.help || '§Hilfe' }}</a>
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      v-if="!user.id"
      :i18n="i18n"
      :title="i18n.privacy || '§Privatsphäre'"
      :step="STEPS.CREATE_ACCOUNT"
      >
      <template #contents>
        {{ user.private
          ? '§Eigenen Namen schwärzen'
          : '§Eigenen Namen im Klartext anzeigen'
        }}
        <a
          :href="config.url.helpRequestPrivacy"
          @click.prevent="$emit('online-help', config.url.helpRequestPrivacy)"
          >{{ i18n.help || '§Hilfe' }}</a>
      </template>
    </ReviewRequestLine>

    <ReviewRequestLine
      v-if="!user.id"
      :i18n="i18n"
      :title="i18n.name"
      :invalid="needCorrectionUser"
      :step="STEPS.CREATE_ACCOUNT"
      >
      <template #contents>
        <span :class="{ 'text-danger': !user.first_name}">
          {{ user.first_name || i18n.yourFirstName }}
        </span>
        <span :class="{ 'text-danger': !user.last_name}" style="margin-left: 1ch">
          {{ user.last_name || i18n.yourLastName }}
        </span>
        <div
          v-if="hasFormErrorsUser"
          class="text-danger"
          >§ there were errors here</div>
      </template>
    </ReviewRequestLine>


    <ReviewRequestLine
      v-if="!user.id"
      :i18n="i18n"
      :title="i18n.email || '§Email'"
      :invalid="needCorrectionEmail"
      :step="STEPS.CREATE_ACCOUNT"
      >
      <template #contents>
        <span :class="{ 'text-danger': needCorrectionEmail}">
          {{ user.email || i18n.email }}
        </span>
        (§wird Behörde nicht mitgeteilt)
      </template>
    </ReviewRequestLine>

    <button
      :x-disabled="!canSend"
      id="send-request-button"
      type="submit"
      class="btn btn-primary"
      @click="$emit('submit')">
      <i class="fa fa-send" aria-hidden="true" />
      {{ i18n.submitRequest }}
    </button>
  </div>
</template>

<script>
import LetterMixin from './lib/letter-mixin'

import ReviewRequestLine from './review-request-line.vue'
import ReviewPublicbody from './review-publicbody.vue'

import { mapMutations, mapGetters } from 'vuex'

import {
  SET_STEP,
  STEPS
} from '../../store/mutation_types'

function erx(text) {
  return text.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&')
}

export default {
  name: 'ReviewRequest',
  mixins: [LetterMixin],
  components: {
    ReviewRequestLine,
    ReviewPublicbody,
  },
  props: {
    i18n: {
      type: Object,
      required: true
    },
    config: {
      type: Object,
      required: true
    },
    pbScope: {
      type: String,
      required: true
    },
    user: {
      type: Object,
      required: true
    },
    userForm: {
      type: Object,
      required: true
    },
    requestForm: {
      type: Object,
      required: true
    },
    defaultLaw: {
      type: Object,
      default: null
    },
    subject: {
      type: String,
      required: true
    },
    body: {
      type: String,
      required: true
    },
    multiRequest: {
      type: Boolean,
      required: true
    },
    fullText: {
      type: Boolean,
      required: true
    },
    hidePublicbodyChooser: {
      type: Boolean,
      required: true
    }
  },
  data() {
    return {
      STEPS
    }
  },
  computed: {
    canSend() {
      return this.user.id || !this.hasErrors
    },
    hasErrors() {
      return this.errors.length > 0
    },
    needCorrectionUser() {
      return this.hasFormErrorsUser || !this.userValid
    },
    needCorrectionSubject() {
      return this.hasFormErrorsSubject || !this.subjectValid
    },
    hasFormErrorsUser() {
      return this.hasFormErrorsFirstName || this.hasFormErrorsLastName
    },
    hasFormErrorsFirstName() {
      if (this.userForm.fields.first_name !== this.user.first_name) return
      return ('first_name' in this.userForm.errors)
    },
    hasFormErrorsLastName() {
      if (this.userForm.fields.last_name !== this.user.last_name) return
      return ('last_name' in this.userForm.errors)
    },
    needCorrectionEmail() {
      return this.hasFormErrorsEmail || !this.emailValid
    },
    hasFormErrorsEmail() {
      if (this.userForm.fields.email != this.user.email) return
      return ('email' in this.userForm.errors)
    },
    hasFormErrorsSubject() {
      // ignore form errors if value changed
      if (this.requestForm.fields.subject.value !== this.subject) return
      return ('subject' in this.requestForm.errors)
    },
    needCorrectionText() {
      return this.errors.length > 0
    },
    errors() {
      const errors = []
      /* if (!this.subjectValid) {
        errors.push(this.i18n.noSubject)
      } */
      if (!this.body || this.body.length === 0) {
        errors.push(this.i18n.noBody)
      }
      let needles = []
      if (!this.fullText) {
        needles = [
          ...needles,
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
        needles.push([this.userRegex, this.i18n.dontInsertName])
      }

      needles.forEach((params) => {
        if (params[0].test(this.body)) {
          errors.push(params[1])
        }
      })
      return errors
    },
    userRegex() {
      const regex = []
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
    publicBody() {
      return this.getPublicBodyByScope(this.pbScope)
    },
    publicBodies() {
      return this.getPublicBodiesByScope(this.pbScope)
    },
    ...mapGetters([
      'user',
      'userValid',
      'subject',
      'subjectValid',
      'emailValid',
      'getPublicBodyByScope',
      'getPublicBodiesByScope',
      'requestPublic',
    ])
  },
  methods: {
    ...mapMutations({
      setStep: SET_STEP,
    })
  }
}
</script>

<style lang="scss" scoped>
@import '../../../styles/variables';

.review-body-text {
  color: var(--#{$prefix}body-color);
  background-color: var(--#{$prefix}body-bg);
  border: 1px dashed #777;
  padding: 0.25em;
  height: 14em;
  max-height: 14em;
  overflow: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}
.review-hints {
  margin-top: 1rem;
  .error {
    color: $red;
  }
}
</style>
