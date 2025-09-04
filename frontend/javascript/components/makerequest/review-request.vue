<template>
  <div>
    <div class="row border-top">
      <div class="col-md-2">
        <h5 class="fs-6">{{ i18n.name }}</h5>
      </div>
      <div class="col-md-7">
        <span :class="{ 'text-danger': !user.first_name}">
          {{ user.first_name || i18n.yourFirstName }}
        </span>
        <span :class="{ 'text-danger': !user.last_name}">
          {{ user.last_name || i18n.yourLastName }}
        </span>
        <div
          v-if="hasFormErrorsUser"
          class="text-danger"
          >§ there were errors here</div>
      </div>
      <div class="col-md-2">
        <button type="button" class="btn"
          :class="{
            'btn-link': !needCorrectionUser,
            'btn-primary': needCorrectionUser
          }"
          @click="setStep(STEPS.CREATE_ACCOUNT)"
          >{{ needCorrectionUser ? '§korrigieren' : i18n.change }}</button>
      </div>
    </div>
    <div class="row border-top">
      <div class="col-md-2">
        <h5 class="fs-6">{{ i18n.subject }}</h5>
      </div>
      <div class="col-md-7">
        <span :class="{ 'text-danger': !subjectValid}">
          {{ subject || i18n.subject }}
        </span>
        <div
          v-if="hasFormErrorsSubject"
          class="text-danger"
          >§ there were errors here</div>
      </div>
      <div class="col-md-2">
        <button type="button" class="btn"
          :class="{
            'btn-link': !needCorrectionSubject,
            'btn-primary': needCorrectionSubject
          }"
          @click="setStep(STEPS.WRITE_REQUEST)"
          >{{ needCorrectionSubject ? '§korrigieren' : i18n.change }}</button>
      </div>
    </div>
          <dl class="message-meta row">
            <dt class="col-sm-3" :class="{ 'text-danger': !userValid }">
              {{ i18n.reviewFrom }}
            </dt>
            <dd class="col-sm-9" :class="{ 'text-danger': !userValid }">
              {{ user.first_name }} {{ user.last_name }}
            </dd>
            <dt class="col-sm-3">{{ i18n.reviewTo }}</dt>
            <dd class="col-sm-9" v-if="publicBodies.length > 1">
              {{ publicBodies.length }} {{ i18n.reviewPublicbodies }}
            </dd>
            <dd class="col-sm-9" v-else-if="publicBody">
              {{ publicBody.name }}
            </dd>
            <dd class="col-sm-9" v-else>-</dd>
            <dt class="col-sm-3" :class="{ 'text-danger': !subjectValid }">
              {{ i18n.subject }}
            </dt>
            <dd class="col-sm-9" :class="{ 'text-danger': !subjectValid }">
              {{ subject }}
            </dd>
          </dl>
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
  props: {
    i18n: {
      type: Object,
      required: true
    },
    publicbodies: {
      type: Array,
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
    fullText: {
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
    hasFormErrorsSubject() {
      // ignore form errors if value changed
      if (this.requestForm.fields.subject.value !== this.subject) return
      return ('subject' in this.requestForm.errors)
    },
    errors() {
      const errors = []
      if (!this.subjectValid) {
        errors.push(this.i18n.noSubject)
      }
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
      return this.publicbodies[0]
    },
    publicBodies() {
      return this.publicbodies
    },
    ...mapGetters([
      'user',
      'userValid',
      'subject',
      'subjectValid'
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
